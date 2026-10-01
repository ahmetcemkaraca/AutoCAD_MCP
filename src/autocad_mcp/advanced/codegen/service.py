"""Stateless recipe admission, rendering and independent validation; output only."""

import hashlib
import json
from typing import cast

from autocad_mcp.core.models import JsonValue

from .models import (
    HUMAN_REVIEW_WARNING,
    MAX_ARTIFACT_BYTES,
    CodeGenerationError,
    GeneratedCodeArtifact,
    decode_recipe,
)
from .render import render_recipe
from .validate import validate_source


def artifact_payload(artifact: GeneratedCodeArtifact) -> dict[str, JsonValue]:
    """Export the exact artifact wire fields as detached JSON data."""
    if type(artifact) is not GeneratedCodeArtifact:
        raise CodeGenerationError("INVALID_ARGUMENT")
    return {
        "target": artifact.target.value,
        "template_id": artifact.template_id,
        "template_version": artifact.template_version,
        "source": artifact.source,
        "digest": artifact.digest,
        "findings": cast(
            list[JsonValue],
            [
                {
                    "rule_id": f.rule_id,
                    "severity": f.severity,
                    "location": f.location,
                    "message": f.message,
                }
                for f in artifact.findings
            ],
        ),
        "executed": artifact.executed,
        "warning": artifact.warning,
    }


def generate_code(payload: object) -> GeneratedCodeArtifact:
    """Return a bounded reviewed artifact; no source execution or persistence path exists."""
    recipe = decode_recipe(payload)
    source = render_recipe(recipe)
    findings = validate_source(recipe, source)
    if any(finding.severity == "error" for finding in findings):
        raise CodeGenerationError("STATIC_VALIDATION_FAILED")
    metadata = {
        "target": recipe.target.value,
        "template_id": recipe.template_id,
        "template_version": recipe.template_version,
        "source": source,
    }
    encoded = json.dumps(
        metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    artifact = GeneratedCodeArtifact(
        recipe.target,
        recipe.template_id,
        recipe.template_version,
        source,
        "sha256:" + hashlib.sha256(encoded).hexdigest(),
        findings,
        False,
        HUMAN_REVIEW_WARNING,
    )
    complete = json.dumps(
        artifact_payload(artifact),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    if len(complete) > MAX_ARTIFACT_BYTES:
        raise CodeGenerationError("PAYLOAD_LIMIT")
    return artifact
