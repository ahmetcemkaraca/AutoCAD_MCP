"""Revision-checked complete snapshots; storage remains the analysis service's responsibility."""

import hashlib
from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any, Literal, TypeAlias, cast

from autocad_mcp.adapter.context_protocol import (
    AdapterContextIssue,
    AdapterDocumentContext,
    AdapterDocumentIdentity,
    AdapterDocumentRevisionToken,
    AdapterEntityFacts,
    AdapterEntityPage,
    AdapterEntityReadRequest,
    ContextAdapterProvider,
    ContextInclude,
)
from autocad_mcp.adapter.protocol import AdapterError

from .adapter_reader import map_document_context, map_entity_context
from .fingerprint import build_drawing_fingerprint, entity_state_digest, snapshot_id
from .identity import build_document_identity
from .models import (
    ActiveDrawingContext,
    CapabilityIssue,
    DocumentIdentity,
    DrawingSnapshot,
    DrawingUnits,
    EntityContext,
    GeometryTolerance,
    RelationshipFact,
    SnapshotMaterialization,
    SnapshotRef,
)
from .pagination import Clock, entity_sort_key
from .relationships import RelationshipOptions, extract_relationships
from .serialization import record_to_json
from .validation import (
    MAX_COMPLETE_RELATIONSHIPS,
    MAX_PAGE_ENTITIES,
    MAX_SNAPSHOT_BYTES,
    MAX_SNAPSHOT_ENTITIES,
    ContextValidationError,
    convert_value,
    record_from_payload,
    require,
    validate_record,
)

_Code: TypeAlias = Literal[
    "REVISION_TOKEN_UNAVAILABLE",
    "SNAPSHOT_CHANGED_DURING_READ",
    "PARTIAL_READ",
    "UNSUPPORTED_CAPABILITY",
    "COMPLETE_SNAPSHOT_LIMIT",
]  # noqa: UP040
_FULL_INCLUDE = ContextInclude(True, True, True, True, True, True)
_ZERO_DIGEST = "sha256:" + "0" * 64


@dataclass(frozen=True, slots=True)
class CompleteSnapshotRequest:
    schema_version: Literal["1.0"]
    relationship_options: RelationshipOptions

    def __post_init__(self) -> None:
        validate_record(self)


class SnapshotBuildError(Exception):
    """Fixed redacted materialization failure; never carries a partial snapshot."""

    def __init__(self, code: _Code) -> None:
        self.code = code
        super().__init__(code.replace("_", " ").capitalize())


def _check(condition: bool, code: _Code) -> None:
    if not condition:
        raise SnapshotBuildError(code)


def _token(value: object) -> AdapterDocumentRevisionToken:
    _check(type(value) is AdapterDocumentRevisionToken, "REVISION_TOKEN_UNAVAILABLE")
    try:
        return replace(cast(AdapterDocumentRevisionToken, value))
    except (ContextValidationError, ValueError, TypeError):
        raise SnapshotBuildError("REVISION_TOKEN_UNAVAILABLE") from None


def _context(
    value: object,
) -> tuple[AdapterDocumentContext, DocumentIdentity, ActiveDrawingContext, DrawingUnits]:
    _check(type(value) is AdapterDocumentContext, "UNSUPPORTED_CAPABILITY")
    raw = cast(AdapterDocumentContext, value)
    _check(type(raw.identity) is AdapterDocumentIdentity, "UNSUPPORTED_CAPABILITY")
    raw = replace(raw, identity=replace(raw.identity))
    return (
        raw,
        build_document_identity(raw.identity),
        map_document_context(raw),
        record_from_payload(DrawingUnits, raw.units),
    )


def _issues(raw: tuple[AdapterContextIssue, ...]) -> tuple[CapabilityIssue, ...]:
    return tuple(
        CapabilityIssue(
            item.code, item.capability, item.entity_handle, item.member, item.message, False
        )
        for item in raw
    )


def _fallback(issue: AdapterContextIssue, identity: AdapterDocumentIdentity) -> bool:
    return (
        issue.code == "IDENTITY_PATH_FALLBACK"
        and issue.capability == "document_identity"
        and issue.entity_handle is None
        and issue.member is None
        and identity.is_saved
        and identity.database_fingerprint_guid is None
    )


class SnapshotBuilder:
    def __init__(
        self,
        provider: ContextAdapterProvider,
        *,
        clock: Clock,
        max_entities: int = 10000,
        max_relationships: int = 100000,
        max_snapshot_bytes: int = 32 * 1024 * 1024,
        adapter_page_size: int = 500,
    ) -> None:
        for value, ceiling in (
            (max_entities, MAX_SNAPSHOT_ENTITIES),
            (max_relationships, MAX_COMPLETE_RELATIONSHIPS),
            (max_snapshot_bytes, MAX_SNAPSHOT_BYTES),
            (adapter_page_size, MAX_PAGE_ENTITIES),
        ):
            require(type(value) is int and 1 <= value <= ceiling, "Invalid lowered snapshot bound")
        self._provider = provider
        self._clock = clock
        self._max_entities = max_entities
        self._max_relationships = max_relationships
        self._max_snapshot_bytes = max_snapshot_bytes
        self._page_size = adapter_page_size

    @staticmethod
    def _shape(
        document: DocumentIdentity,
        context: ActiveDrawingContext,
        units: DrawingUnits,
        tolerance: GeometryTolerance,
        issues: tuple[CapabilityIssue, ...],
        captured: datetime,
        token_digest: str,
        entity_count: int,
        relationship_count: int,
    ) -> dict[str, Any]:
        identifier = "ds1_" + "0" * 32
        return {
            "schema_version": "1.0",
            "snapshot_id": identifier,
            "reference": SnapshotRef(
                identifier, document.document_id, document.session_document_id, _ZERO_DIGEST
            ),
            "captured_at": captured,
            "document": document,
            "fingerprint": {
                "algorithm": "sha256-cad-facts-v1",
                "content_digest": _ZERO_DIGEST,
                "presentation_digest": _ZERO_DIGEST,
                "coverage": "enumerated-entity-facts-v1",
                "complete": True,
                "incomplete_reasons": [],
                "entity_count": entity_count,
            },
            "units": units,
            "tolerance": tolerance,
            "active_context": context,
            "entities": [],
            "capability_issues": issues,
            "materialization": {
                "builder_version": "snapshot-builder-v1",
                "complete": True,
                "entity_count": entity_count,
                "relationship_count": relationship_count,
                "revision_token_digest": token_digest,
            },
        }

    def _bytes(self, shape: dict[str, Any], entity_bytes: int) -> None:
        omitted = len(record_to_json(shape).encode("utf-8")) + entity_bytes
        field = len(record_to_json({"canonical_byte_count": omitted}).encode("utf-8")) - 2 + 1
        _check(omitted + field <= self._max_snapshot_bytes, "COMPLETE_SNAPSHOT_LIMIT")

    def build(self, request: CompleteSnapshotRequest) -> DrawingSnapshot:
        try:
            _check(type(request) is CompleteSnapshotRequest, "UNSUPPORTED_CAPABILITY")
            request = replace(request)
            return self._build(request)
        except (SnapshotBuildError, AdapterError):
            raise
        except ContextValidationError as error:
            mapping = {
                "REVISION_TOKEN_UNAVAILABLE": "REVISION_TOKEN_UNAVAILABLE",
                "STALE_CURSOR": "SNAPSHOT_CHANGED_DURING_READ",
                "SNAPSHOT_CHANGED_DURING_READ": "SNAPSHOT_CHANGED_DURING_READ",
                "PARTIAL_READ": "PARTIAL_READ",
                "PAYLOAD_LIMIT": "COMPLETE_SNAPSHOT_LIMIT",
                "COMPLETE_SNAPSHOT_LIMIT": "COMPLETE_SNAPSHOT_LIMIT",
            }
            raise SnapshotBuildError(
                cast(_Code, mapping.get(error.code, "UNSUPPORTED_CAPABILITY"))
            ) from None
        except (ValueError, TypeError, AttributeError, KeyError, OverflowError, RecursionError):
            raise SnapshotBuildError("UNSUPPORTED_CAPABILITY") from None

    def _build(self, request: CompleteSnapshotRequest) -> DrawingSnapshot:
        adapter = self._provider.get()
        before = _token(adapter.read_document_revision())
        raw, document, context, units = _context(adapter.read_document_context())
        _check(
            before.session_document_id == document.session_document_id,
            "SNAPSHOT_CHANGED_DURING_READ",
        )
        captured = cast(datetime, convert_value(self._clock.now(), datetime))
        diagnostic = "sha256:" + hashlib.sha256(record_to_json(before).encode("utf-8")).hexdigest()
        issues = list(raw.issues)
        entities: list[EntityContext] = []
        handles = set()
        cursors = set()
        cursor = None
        used = 0
        while True:
            page = adapter.read_entity_page(
                AdapterEntityReadRequest(
                    (), (), (), (), (), (), None, _FULL_INCLUDE, self._page_size, cursor
                )
            )
            _check(type(page) is AdapterEntityPage, "PARTIAL_READ")
            page = replace(page)
            _check(_token(page.revision_token) == before, "SNAPSHOT_CHANGED_DURING_READ")
            _check(not page.partial, "PARTIAL_READ")
            for issue in page.issues:
                _check(_fallback(issue, raw.identity), "PARTIAL_READ")
                if issue not in issues:
                    issues.append(issue)
            _check(page.next_cursor is None or bool(page.entities), "PARTIAL_READ")
            for record in page.entities:
                _check(type(record) is AdapterEntityFacts, "UNSUPPORTED_CAPABILITY")
                _check(len(entities) < self._max_entities, "COMPLETE_SNAPSHOT_LIMIT")
                entity = map_entity_context(replace(record))
                _check(entity.identity.handle not in handles, "PARTIAL_READ")
                size = len(record_to_json(entity).encode("utf-8")) + bool(entities)
                count = len(entities) + 1
                self._bytes(
                    self._shape(
                        document,
                        context,
                        units,
                        request.relationship_options.tolerance,
                        _issues(tuple(issues)),
                        captured,
                        diagnostic,
                        count,
                        0,
                    ),
                    used + size,
                )
                handles.add(entity.identity.handle)
                entities.append(entity)
                used += size
            if page.next_cursor is None:
                break
            _check(page.next_cursor not in cursors, "PARTIAL_READ")
            cursors.add(page.next_cursor)
            cursor = page.next_cursor
        raw_after, document_after, context_after, units_after = _context(
            adapter.read_document_context()
        )
        after = _token(adapter.read_document_revision())
        _check(
            before == after
            and document == document_after
            and context == context_after
            and units == units_after,
            "SNAPSHOT_CHANGED_DURING_READ",
        )
        return self._finish(
            tuple(sorted(entities, key=entity_sort_key)),
            request.relationship_options,
            document,
            context,
            units,
            _issues(tuple(issues)),
            captured,
            diagnostic,
        )

    def _finish(
        self,
        entities: tuple[EntityContext, ...],
        options: RelationshipOptions,
        document: DocumentIdentity,
        context: ActiveDrawingContext,
        units: DrawingUnits,
        issues: tuple[CapabilityIssue, ...],
        captured: datetime,
        diagnostic: str,
    ) -> DrawingSnapshot:
        relations = extract_relationships(entities, options)
        _check(len(relations) <= self._max_relationships, "COMPLETE_SNAPSHOT_LIMIT")
        grouped: dict[str, list[RelationshipFact]] = defaultdict(list)
        for relation in relations:
            grouped[relation.source_handle].append(relation)
        complete = []
        used = 0
        count = 0
        for entity in entities:
            updated = replace(entity, relationships=tuple(grouped.get(entity.identity.handle, ())))
            updated = replace(updated, state_digest=entity_state_digest(updated))
            count += len(updated.relationships)
            size = len(record_to_json(updated).encode("utf-8")) + bool(complete)
            self._bytes(
                self._shape(
                    document,
                    context,
                    units,
                    options.tolerance,
                    issues,
                    captured,
                    diagnostic,
                    len(entities),
                    count,
                ),
                used + size,
            )
            complete.append(updated)
            used += size
        # Empty drawings still include real complete metadata in byte admission.
        self._bytes(
            self._shape(
                document,
                context,
                units,
                options.tolerance,
                issues,
                captured,
                diagnostic,
                len(entities),
                len(relations),
            ),
            used,
        )
        full = tuple(complete)
        fingerprint = build_drawing_fingerprint(
            document, units, options.tolerance, context, full, issues
        )
        identifier = snapshot_id(document, fingerprint)
        reference = SnapshotRef(
            identifier,
            document.document_id,
            document.session_document_id,
            fingerprint.content_digest,
        )
        shape = self._shape(
            document,
            context,
            units,
            options.tolerance,
            issues,
            captured,
            diagnostic,
            len(full),
            len(relations),
        )
        shape.update(
            snapshot_id=identifier, reference=reference, fingerprint=fingerprint, entities=full
        )
        canonical_count = len(record_to_json(shape).encode("utf-8"))
        shape["materialization"]["canonical_byte_count"] = canonical_count
        _check(
            len(record_to_json(shape).encode("utf-8")) <= self._max_snapshot_bytes,
            "COMPLETE_SNAPSHOT_LIMIT",
        )
        return DrawingSnapshot(
            "1.0",
            identifier,
            reference,
            captured,
            document,
            fingerprint,
            units,
            options.tolerance,
            context,
            full,
            issues,
            SnapshotMaterialization(
                "snapshot-builder-v1", True, len(full), len(relations), canonical_count, diagnostic
            ),
        )
