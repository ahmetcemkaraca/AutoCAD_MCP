"""Canonical full-set drawing facts and presentation identities, without session IDs."""

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import is_dataclass
from math import isfinite
from typing import Any
from unicodedata import normalize

from .models import (
    ActiveDrawingContext,
    CapabilityIssue,
    DocumentIdentity,
    DrawingFingerprint,
    DrawingSnapshot,
    DrawingUnits,
    EntityContext,
    GeometryTolerance,
)
from .serialization import record_to_payload
from .validation import (
    MAX_SNAPSHOT_ENTITIES,
    ContextValidationError,
    require,
    require_complete_entity,
)


def _canonical(value: object) -> str:
    if is_dataclass(value) and not isinstance(value, type):
        return _canonical(record_to_payload(value))
    if value is None:
        return "null"
    if type(value) is bool:
        return "true" if value else "false"
    if type(value) is int:
        return str(value)
    if type(value) is float:
        require(isfinite(value), "Canonical numbers must be finite")
        return "0" if value == 0 else format(value, ".17g")
    if isinstance(value, str):
        return json.dumps(normalize("NFC", value), ensure_ascii=False)
    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            require(isinstance(key, str), "Canonical object keys must be strings")
            normalized = normalize("NFC", key)
            require(normalized not in result, "Canonical object contains normalized key collisions")
            result[normalized] = item
        return (
            "{"
            + ",".join(_canonical(key) + ":" + _canonical(result[key]) for key in sorted(result))
            + "}"
        )
    if isinstance(value, tuple | list):
        return "[" + ",".join(_canonical(item) for item in value) + "]"
    raise ContextValidationError("Unsupported canonical value")


def canonical_bytes(value: object) -> bytes:
    """Encode compact NFC JSON using exact .17g numeric tokens, never numeric strings."""
    try:
        return _canonical(value).encode("utf-8")
    except (UnicodeEncodeError, RecursionError):
        raise ContextValidationError("Invalid canonical value") from None


def _digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def _issues(issues: Sequence[CapabilityIssue]) -> list[dict[str, Any]]:
    result = []
    for issue in issues:
        payload = record_to_payload(issue)
        del payload["message"]
        result.append(payload)
    return sorted(result, key=canonical_bytes)


def _entity_facts(entity: EntityContext) -> dict[str, Any]:
    require_complete_entity(entity)
    payload: dict[str, Any] = record_to_payload(entity)
    del payload["identity"]["object_id"]
    del payload["identity"]["object_id_scope"]
    del payload["state_digest"]
    del payload["relationships"]
    payload["fact_evidence"] = sorted(
        [
            {key: value for key, value in item.items() if key != "source"}
            for item in payload["fact_evidence"]
        ],
        key=canonical_bytes,
    )
    payload["capability_issues"] = _issues(entity.capability_issues)
    return payload


def entity_state_digest(entity: EntityContext) -> str:
    facts = _entity_facts(entity)
    del facts["fact_evidence"]
    del facts["capability_issues"]
    return _digest({"schema_major": 1, **facts})


def _content(
    document: DocumentIdentity,
    units: DrawingUnits,
    tolerance: GeometryTolerance,
    entities: Sequence[EntityContext],
    issues: Sequence[CapabilityIssue],
) -> dict[str, Any]:
    from .pagination import entity_sort_key

    require(
        len(entities) <= MAX_SNAPSHOT_ENTITIES,
        "Too many complete entities",
        code="COMPLETE_SNAPSHOT_LIMIT",
    )
    require(
        len({entity.identity.handle for entity in entities}) == len(entities),
        "Duplicate complete entity handle",
        code="SNAPSHOT_INCOMPLETE",
    )
    require(
        not any(issue.required or issue.code == "NOT_REQUESTED" for issue in issues)
        and not any(issue.required for entity in entities for issue in entity.capability_issues),
        "Required complete facts are unavailable",
        code="SNAPSHOT_INCOMPLETE",
    )
    relationships = [
        record_to_payload(relation) for entity in entities for relation in entity.relationships
    ]
    require(
        len(relationships) <= 100000,
        "Too many complete relationships",
        code="COMPLETE_SNAPSHOT_LIMIT",
    )
    relationships.sort(
        key=lambda item: (
            item["kind"],
            item["source_handle"],
            item["target_handle"],
            canonical_bytes(item),
        )
    )
    return {
        "schema_major": 1,
        "coverage": "enumerated-entity-facts-v1",
        "document_id": document.document_id,
        "units": record_to_payload(units),
        "tolerance": record_to_payload(tolerance),
        "entities": [_entity_facts(entity) for entity in sorted(entities, key=entity_sort_key)],
        "relationships": relationships,
        "capability_issues": _issues(issues),
    }


def _presentation(context: ActiveDrawingContext) -> dict[str, Any]:
    payload: dict[str, Any] = record_to_payload(context)
    del payload["space"]["viewport_object_id"]
    del payload["space"]["viewport_object_id_scope"]
    return payload


def build_drawing_fingerprint(
    document: DocumentIdentity,
    units: DrawingUnits,
    tolerance: GeometryTolerance,
    active_context: ActiveDrawingContext,
    entities: Sequence[EntityContext],
    issues: Sequence[CapabilityIssue],
) -> DrawingFingerprint:
    """Hash the caller's complete revision-checked set, before response filtering/pagination."""
    content = _digest(_content(document, units, tolerance, entities, issues))
    presentation = _digest(
        {
            "document_id": document.document_id,
            "content_digest": content,
            "active_context": _presentation(active_context),
        }
    )
    return DrawingFingerprint(
        "sha256-cad-facts-v1",
        content,
        presentation,
        "enumerated-entity-facts-v1",
        True,
        (),
        len(entities),
    )


def snapshot_id(document: DocumentIdentity, fingerprint: DrawingFingerprint) -> str:
    payload = {
        "schema_major": 1,
        "coverage": fingerprint.coverage,
        "document_id": document.document_id,
        "content_digest": fingerprint.content_digest,
        "presentation_digest": fingerprint.presentation_digest,
    }
    return "ds1_" + hashlib.sha256(canonical_bytes(payload)).hexdigest()[:32]


def snapshot_identity_bytes(snapshot: DrawingSnapshot) -> bytes:
    """Retain underlying facts/context so forged same-ID hashes cannot hide changed facts."""
    return canonical_bytes(
        {
            "content": _content(
                snapshot.document,
                snapshot.units,
                snapshot.tolerance,
                snapshot.entities,
                snapshot.capability_issues,
            ),
            "active_context": _presentation(snapshot.active_context),
        }
    )
