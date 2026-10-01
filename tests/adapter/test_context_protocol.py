"""Pure immutable raw context records; synthetic fixtures are never CAD observations."""

import json
from dataclasses import replace
from pathlib import Path

import pytest
from autocad_mcp.adapter.context_protocol import (
    AdapterContextIssue,
    AdapterDocumentContext,
    AdapterDocumentIdentity,
    AdapterDocumentRevisionToken,
    AdapterEntityFacts,
    AdapterEntityPage,
    AdapterEntityReadRequest,
    ContextInclude,
)
from autocad_mcp.context.validation import ContextValidationError

FIXTURE = Path(__file__).parents[1] / "fixtures/context/raw_entities_v1.json"
ALL = ContextInclude(True, True, True, True, True, True)


def fixture_records(session=0):
    data = json.loads(FIXTURE.read_text())
    document = data["document"]
    document["identity"]["session_document_id"] = data["sessions"][session]["session_document_id"]
    document["identity"] = AdapterDocumentIdentity(**document["identity"])
    document["issues"] = tuple(AdapterContextIssue(**item) for item in document["issues"])
    entities = []
    for entity in data["entities"]:
        entity["object_id"] = data["sessions"][session]["object_ids"][entity["handle"]]
        entity["issues"] = tuple(AdapterContextIssue(**item) for item in entity["issues"])
        entities.append(AdapterEntityFacts(**entity))
    return AdapterDocumentContext(**document), tuple(entities)


def request(**changes):
    data = {
        "spaces": (),
        "layout_names": (),
        "entity_types": (),
        "layer_names": (),
        "layer_globs": (),
        "handles": (),
        "intersects_wcs": None,
        "include": ALL,
        "page_size": 100,
        "cursor": None,
    }
    return AdapterEntityReadRequest(**(data | changes))


def test_raw_records_copy_and_deeply_freeze_json_and_normalize_handles():
    document, entities = fixture_records()
    source = {"kind": "point", "position": {"x": 1, "y": 2, "z": 3}}
    raw = replace(entities[0], handle="a1", geometry=source)
    source["position"]["x"] = 999
    assert raw.handle == "A1" and raw.geometry["position"]["x"] == 1
    with pytest.raises(TypeError):
        raw.geometry["position"]["x"] = 2
    poly = next(entity for entity in entities if entity.handle == "30")
    assert isinstance(poly.geometry["vertices"], tuple)
    with pytest.raises(AttributeError):
        poly.geometry["vertices"].append({})
    assert document.identity.full_path.startswith("C:")


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": "2.0"},
        {"handle": "G"},
        {"object_id": True},
        {"bounds": (1, 0, 0, 0, 0, 0)},
        {"space_kind": "paper", "layout_name": None},
        {"space_kind": "block_definition", "owner_block_handle": None, "layout_name": None},
        {"geometry": {"kind": "point", "position": object()}},
        {"style": {"visible": float("nan")}},
        {"style": {"color_index": 1e16}},
    ],
)
def test_invalid_raw_record_values_fail_redacted(change):
    _, entities = fixture_records()
    with pytest.raises(ContextValidationError):
        replace(entities[0], **change)


@pytest.mark.parametrize("size", [0, True, 501])
def test_page_request_bounds(size):
    with pytest.raises(ContextValidationError):
        request(page_size=size)


def test_token_and_cursor_exact_utf8_bounds_and_page_count():
    document, entities = fixture_records()
    token = AdapterDocumentRevisionToken(
        "1.0", document.identity.session_document_id, "synthetic", "é" * 256
    )
    with pytest.raises(ContextValidationError):
        replace(token, opaque_value="é" * 256 + "x")
    assert request(cursor="é" * 1024).cursor == "é" * 1024
    with pytest.raises(ContextValidationError):
        request(cursor="é" * 1024 + "x")
    assert (
        len(AdapterEntityPage("1.0", token, (entities[0],) * 500, None, False, ()).entities) == 500
    )
    with pytest.raises(ContextValidationError):
        AdapterEntityPage("1.0", token, (entities[0],) * 501, None, False, ())


def test_raw_freeze_stops_oversized_nested_json_before_copying_the_whole_graph():
    _, entities = fixture_records()

    class Sentinel:
        pass

    # Byte overflow must win before traversing a later non-JSON object.
    oversized = {"prefix": ["x" * 65536] * 5, "later": Sentinel()}
    with pytest.raises(ContextValidationError) as error:
        replace(entities[0], geometry=oversized)
    assert error.value.code == "PAYLOAD_LIMIT"


def test_public_exports_are_additive_and_imports_keep_windows_isolated():
    import subprocess
    import sys

    script = """
import sys
from autocad_mcp.adapter import (ContextAutoCADAdapter, ContextAdapterProvider,
    FakeContextAutoCADAdapter, StaticContextAdapterProvider, ContextInclude)
from autocad_mcp.adapter.protocol import AutoCADAdapter
import autocad_mcp.context.adapter_reader
assert {name for name in AutoCADAdapter.__dict__ if not name.startswith('_')} == {
    'status','reconnect','list_entities','get_entity_info'}
assert not {'pythoncom','win32com','win32com.client','pyautocad',
    'autocad_mcp.adapter.windows','autocad_mcp.adapter.windows_context',
    'autocad_mcp.adapter.windows_session'} & set(sys.modules)
"""
    result = subprocess.run(  # noqa: S603 - fixed interpreter and literal test probe
        [sys.executable, "-c", script], capture_output=True, text=True, check=False
    )  # noqa: S603 - fixed literal import probe
    assert result.returncode == 0, result.stderr


def test_raw_document_display_name_uses_domain_codepoint_limit_not_utf8_bytes():
    from autocad_mcp.context.identity import build_document_identity

    document, _ = fixture_records()
    for name in ("ç" * 200, "🙂" * 255):
        identity = replace(document.identity, display_name=name)
        assert build_document_identity(identity).display_name == name
    with pytest.raises(ContextValidationError):
        replace(document.identity, display_name="🙂" * 256)
