"""Revision-bound portable paging and filtering over synthetic raw facts."""

from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from autocad_mcp.adapter.fake import FakeAutoCADAdapter
from autocad_mcp.adapter.fake_context import FakeContextAutoCADAdapter, StaticContextAdapterProvider
from autocad_mcp.adapter.protocol import AdapterError, AdapterErrorCode
from autocad_mcp.context.validation import ContextValidationError

from tests.adapter.test_context_protocol import ALL, fixture_records, request

CLOCK = SimpleNamespace(now=lambda: datetime(2026, 10, 1, tzinfo=UTC))
SECRET = b"synthetic-context-cursor-secret-32"


def fake(session=0, **changes):
    document, entities = fixture_records(session)
    return FakeContextAutoCADAdapter(
        document=document, entities=entities, clock=CLOCK, cursor_secret=SECRET, **changes
    )


def test_additive_fake_provider_and_two_sessions_keep_content_identity():
    first, second = fake(), fake(1)
    assert isinstance(first, FakeAutoCADAdapter)
    assert StaticContextAdapterProvider(first).get() is first
    assert first.read_document_revision() == first.read_document_revision()
    assert first.read_document_context().identity.session_document_id != (
        second.read_document_context().identity.session_document_id
    )
    assert [x.handle for x in first.read_entity_page(request()).entities] == [
        x.handle for x in second.read_entity_page(request()).entities
    ]
    assert first.entity_facts_by_handles(("10",), ALL)[0].object_id != (
        second.entity_facts_by_handles(("10",), ALL)[0].object_id
    )
    before = first.read_document_revision()
    first.advance_revision()
    assert before != first.read_document_revision()


@pytest.mark.parametrize("count", [1, 500, 501, 10001])
def test_paging_is_bounded_ordered_and_nonrepeating_over_live_sets(count):
    document, entities = fixture_records()
    records = tuple(replace(entities[0], handle=f"{i+1:X}", object_id=i + 1) for i in range(count))
    adapter = FakeContextAutoCADAdapter(
        document=document, entities=records, clock=CLOCK, cursor_secret=SECRET
    )
    handles = []
    cursors = set()
    current = request(page_size=500)
    while True:
        page = adapter.read_entity_page(current)
        assert 0 < len(page.entities) <= 500
        handles.extend(item.handle for item in page.entities)
        if page.next_cursor is None:
            break
        assert page.next_cursor not in cursors and len(page.next_cursor.encode()) <= 2048
        cursors.add(page.next_cursor)
        current = replace(current, cursor=page.next_cursor)
    assert handles == [f"{i+1:X}" for i in range(count)]


@pytest.mark.parametrize(
    "fields,expected",
    [
        ({"spaces": ("paper",)}, ["50", "60"]),
        ({"layout_names": ("Sheet α",)}, ["50", "60"]),
        ({"entity_types": ("AcDbCircle",)}, ["20"]),
        ({"layer_names": ("Walls",)}, ["10"]),
        ({"layer_globs": ("wall[1]",)}, ["30"]),
        ({"layer_globs": ("W*",)}, ["10"]),
        ({"layer_globs": ("wal?s",)}, ["20"]),
        ({"handles": ("60", "10")}, ["10", "60"]),
        ({"intersects_wcs": (100, 100, 0, 101, 101, 0)}, []),
    ],
)
def test_filters_apply_before_slicing_and_globs_are_literal_except_star_question(fields, expected):
    assert [x.handle for x in fake().read_entity_page(request(**fields)).entities] == expected


def test_cursor_tampering_request_binding_stale_revision_and_missing_boundary():
    adapter = fake()
    initial = request(page_size=1)
    page = adapter.read_entity_page(initial)
    token = page.next_cursor
    for current in (
        replace(initial, cursor=token + "x"),
        replace(initial, cursor=token, page_size=2),
        replace(initial, cursor=token, layer_names=("Walls",)),
    ):
        with pytest.raises(ContextValidationError) as error:
            adapter.read_entity_page(current)
        assert error.value.code == "INVALID_CURSOR"
    adapter.advance_revision()
    with pytest.raises(ContextValidationError) as error:
        adapter.read_entity_page(replace(initial, cursor=token))
    assert error.value.code == "STALE_CURSOR"
    adapter = fake()
    page = adapter.read_entity_page(initial)
    document, entities = fixture_records()
    adapter.set_entities(tuple(x for x in entities if x.handle != "10"), advance_revision=False)
    with pytest.raises(ContextValidationError) as error:
        adapter.read_entity_page(replace(initial, cursor=page.next_cursor))
    assert error.value.code == "INVALID_CURSOR"


def test_failure_partial_injection_and_lookup_bounds():
    adapter = fake()
    error = AdapterError(AdapterErrorCode.COM_BUSY, "Full AutoCAD is busy")
    adapter.fail_next(error)
    with pytest.raises(AdapterError) as caught:
        adapter.read_document_context()
    assert caught.value is error
    adapter.inject_partial_once()
    assert adapter.read_entity_page(request()).partial
    assert not adapter.read_entity_page(request()).partial
    for handles in (("10", "10"), ("FF",), tuple(f"{x:X}" for x in range(257))):
        with pytest.raises(ContextValidationError):
            adapter.entity_facts_by_handles(handles, ALL)
    assert tuple(x.handle for x in adapter.entity_facts_by_handles(("60", "10"), ALL)) == (
        "60",
        "10",
    )


def test_mixed_owner_order_and_definition_wcs_projection():
    document, entities = fixture_records()
    source = entities[0]
    records = (
        replace(source, handle="F", space_kind="model"),
        replace(source, handle="1", space_kind="paper", layout_name="Z"),
        replace(source, handle="A", space_kind="paper", layout_name="A"),
        replace(
            source,
            handle="2",
            space_kind="block_definition",
            layout_name=None,
            owner_block_handle="B",
        ),
    )
    adapter = FakeContextAutoCADAdapter(
        document=document, entities=records, clock=CLOCK, cursor_secret=SECRET
    )
    first = adapter.read_entity_page(request(page_size=2))
    second = adapter.read_entity_page(request(page_size=2, cursor=first.next_cursor))
    assert [x.handle for x in first.entities + second.entities] == ["F", "A", "1", "2"]
    page = adapter.read_entity_page(request(intersects_wcs=(0, 0, 0, 20, 20, 0)))
    assert "2" not in [x.handle for x in page.entities] and page.issues
    with pytest.raises(ContextValidationError) as error:
        adapter.read_entity_page(
            request(spaces=("block_definition",), intersects_wcs=(0, 0, 0, 20, 20, 0))
        )
    assert error.value.code == "UNSUPPORTED_CAPABILITY"


def test_layer_names_and_globs_are_or_within_layer_and_and_across_other_filters():
    result = fake().read_entity_page(request(layer_names=("Walls",), layer_globs=("wal?s",)))
    assert [item.handle for item in result.entities] == ["10", "20"]
    result = fake().read_entity_page(
        request(layer_names=("Walls",), layer_globs=("wal?s",), entity_types=("AcDbCircle",))
    )
    assert [item.handle for item in result.entities] == ["20"]


def test_short_or_empty_secret_is_rejected_and_revision_unavailable_is_explicit():
    for secret in (b"", b"short"):
        document, entities = fixture_records()
        with pytest.raises(ContextValidationError):
            FakeContextAutoCADAdapter(document=document, entities=entities, cursor_secret=secret)
    adapter = fake()
    adapter.set_revision_token(None)
    with pytest.raises(ContextValidationError) as error:
        adapter.read_document_revision()
    assert error.value.code == "REVISION_TOKEN_UNAVAILABLE"


def test_max_handle_unicode_layout_cursor_nested_wire_and_session_change():
    document, entities = fixture_records()
    first = replace(entities[0], handle="E" * 128, space_kind="paper", layout_name="🙂" * 255)
    last = replace(first, handle="F" * 128)
    adapter = FakeContextAutoCADAdapter(
        document=document, entities=(last, first), clock=CLOCK, cursor_secret=SECRET
    )
    page = adapter.read_entity_page(request(page_size=1))
    assert page.entities == (first,) and len(page.next_cursor.encode()) <= 2048
    assert adapter.read_entity_page(request(page_size=1, cursor=page.next_cursor)).entities == (
        last,
    )
    next_document, _ = fixture_records(1)
    adapter.set_document(next_document)
    with pytest.raises(ContextValidationError) as error:
        adapter.read_entity_page(request(page_size=1, cursor=page.next_cursor))
    assert error.value.code == "STALE_CURSOR"


def test_glob_adversary_finishes_and_brackets_and_backslashes_are_literal():
    import subprocess
    import sys

    from autocad_mcp.context.filtering import layer_glob_matches as _glob

    assert _glob("[ab]", "[ab]") and not _glob("[ab]", "a")
    assert _glob("[?]", "[x]") and _glob(r"wall\*", r"wall\abc")
    script = (
        "from autocad_mcp.context.filtering import layer_glob_matches as _glob; "
        "from time import perf_counter; started=perf_counter(); "
        "assert not _glob('*a'*20+'b','a'*100); assert perf_counter()-started < 2"
    )
    # Bound matching itself; cold interpreter/MCP imports have a separate startup allowance.
    result = subprocess.run(  # noqa: S603 - fixed interpreter and literal test probe
        [sys.executable, "-c", script], capture_output=True, text=True, check=False, timeout=10
    )  # noqa: S603 - fixed literal adversarial probe
    assert result.returncode == 0, result.stderr
