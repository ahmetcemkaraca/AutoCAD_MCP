"""Output-only service validates before rendering and before artifact release."""

import ast
import builtins
import hashlib
import io
import json
import os
import socket
import subprocess
from pathlib import Path

import pytest
from autocad_mcp.advanced.codegen import service
from autocad_mcp.advanced.codegen.models import (
    HUMAN_REVIEW_WARNING,
    CodeGenerationError,
    StaticFinding,
)

from .test_models import request
from .test_validate import PAIRS


@pytest.mark.parametrize("pair", PAIRS, ids=lambda p: f'{p["target"]}-{p["template_id"]}')
def test_exact_artifact_fields_digest_warning_and_determinism(pair: dict) -> None:
    artifact = service.generate_code(pair["example"])
    payload = service.artifact_payload(artifact)
    assert set(payload) == {
        "target",
        "template_id",
        "template_version",
        "source",
        "digest",
        "findings",
        "executed",
        "warning",
    }
    metadata = {
        key: payload[key] for key in ("target", "template_id", "template_version", "source")
    }
    encoded = json.dumps(
        metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    assert payload["digest"] == "sha256:" + hashlib.sha256(encoded).hexdigest()
    assert payload["executed"] is False and payload["warning"] == HUMAN_REVIEW_WARNING
    assert payload["findings"] == []
    assert service.generate_code(pair["example"]) == artifact
    assert (
        len(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())
        <= 65536
    )


def test_invalid_recipe_never_calls_renderer(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args):
        raise AssertionError("Renderer reached before admission")

    monkeypatch.setattr(service, "render_recipe", forbidden)
    with pytest.raises(CodeGenerationError) as error:
        service.generate_code({**request(), "source": "private injected text"})
    assert error.value.code == "INVALID_ARGUMENT" and str(error.value) == "INVALID_ARGUMENT"


def test_render_once_validate_once_and_any_error_prevents_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []
    original = service.render_recipe

    def render(recipe):
        calls.append("render")
        return original(recipe)

    def validate(recipe, source):
        calls.append("validate")
        return (
            StaticFinding("REVIEW", "warning", "1:1", "Review"),
            StaticFinding("DENIED", "error", "1:1", "Denied"),
        )

    monkeypatch.setattr(service, "render_recipe", render)
    monkeypatch.setattr(service, "validate_source", validate)
    with pytest.raises(CodeGenerationError) as error:
        service.generate_code(request())
    assert error.value.code == "STATIC_VALIDATION_FAILED"
    assert calls == ["render", "validate"]


def test_injected_rendered_source_is_rejected_by_real_validator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        service, "render_recipe", lambda recipe: 'import os\nos.system("synthetic")'
    )
    with pytest.raises(CodeGenerationError) as error:
        service.generate_code(request())
    assert error.value.code == "STATIC_VALIDATION_FAILED"


def test_actual_artifact_byte_ceiling_and_one_byte_overflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ordinary = service.generate_code(request())
    payload = service.artifact_payload(ordinary)
    baseline = len(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    )
    source = ordinary.source + " " * (65536 - baseline)
    assert len(source.encode()) < 65536
    monkeypatch.setattr(service, "render_recipe", lambda recipe: source)
    exact = service.artifact_payload(service.generate_code(request()))
    assert (
        len(json.dumps(exact, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())
        == 65536
    )
    source += " "
    with pytest.raises(CodeGenerationError) as error:
        service.generate_code(request())
    assert error.value.code == "PAYLOAD_LIMIT"


def test_generation_does_not_reach_file_process_network_or_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_compile = builtins.compile
    ast_compiles = []

    def forbidden(*args, **kwargs):
        raise AssertionError("Forbidden operation reached")

    def static_compile(*args, **kwargs):
        flags = kwargs.get("flags", args[3] if len(args) > 3 else 0)
        assert flags & ast.PyCF_ONLY_AST
        ast_compiles.append(True)
        return original_compile(*args, **kwargs)

    with monkeypatch.context() as guard:
        for owner, name in [
            (builtins, "eval"),
            (builtins, "exec"),
            (builtins, "open"),
            (io, "open"),
            (os, "open"),
            (os, "system"),
            (os, "getenv"),
            (Path, "open"),
            (subprocess, "Popen"),
            (subprocess, "run"),
            (socket, "socket"),
            (socket, "create_connection"),
        ]:
            guard.setattr(owner, name, forbidden)
        guard.setattr(builtins, "compile", static_compile)
        for pair in PAIRS:
            assert service.generate_code(pair["example"]).executed is False
    assert len(ast_compiles) == 3


def test_warning_findings_are_retained_and_counted_in_actual_utf8_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    warning = StaticFinding("REVIEW", "warning", "1:1", "Review outside the server")
    monkeypatch.setattr(service, "validate_source", lambda recipe, source: (warning,))
    artifact = service.generate_code(request())
    assert artifact.findings == (warning,)
    assert service.artifact_payload(artifact)["findings"] == [
        {
            "rule_id": "REVIEW",
            "severity": "warning",
            "location": "1:1",
            "message": "Review outside the server",
        }
    ]
    oversized = StaticFinding("REVIEW", "warning", "1:1", "🙂" * 16384)
    monkeypatch.setattr(service, "validate_source", lambda recipe, source: (oversized,))
    with pytest.raises(CodeGenerationError) as error:
        service.generate_code(request())
    assert error.value.code == "PAYLOAD_LIMIT"
