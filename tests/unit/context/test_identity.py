"""Persistent document identities normalize Windows facts without disclosing paths."""

import hashlib
from types import SimpleNamespace
from uuid import UUID

import pytest
from autocad_mcp.context.identity import build_document_identity, normalize_handle
from autocad_mcp.context.validation import ContextValidationError


def raw_identity(**changes):
    values = {
        "display_name": "fixture.dwg",
        "full_path": r"C:\Plans\fixture.dwg",
        "database_fingerprint_guid": None,
        "session_document_id": "11111111-1111-4111-8111-111111111111",
        "is_saved": True,
        "is_read_only": False,
    }
    values.update(changes)
    return SimpleNamespace(**values)


@pytest.mark.parametrize(
    "path",
    [
        r"c:\plans\café.dwg",
        "C:/PLANS/cafe\u0301.dwg",
        r"\\?\C:\plans\.\café.dwg",
        r"C:\other\..\plans\café.dwg",
    ],
)
def test_drive_path_equivalence_and_privacy(path):
    identity = build_document_identity(raw_identity(full_path=path))
    expected = hashlib.sha256("c:\\plans\\café.dwg".encode()).hexdigest()
    assert identity.path_hash == expected
    assert identity.document_id == "dwg_" + expected[:32]
    assert identity.scope == "drawing"
    assert path not in repr(identity)


def test_unc_extended_prefix_and_case_are_equivalent():
    first = build_document_identity(raw_identity(full_path=r"\\server\share\a.dwg"))
    second = build_document_identity(raw_identity(full_path=r"\\?\UNC\SERVER\SHARE\a.dwg"))
    assert first == second


@pytest.mark.parametrize(
    "path",
    [
        None,
        "",
        "relative.dwg",
        r"C:relative.dwg",
        r"\root.dwg",
        r"\\server",
        "C:/invalid\x00name.dwg",
        r"\\.\device",
    ],
)
def test_saved_path_failures_are_redacted(path):
    with pytest.raises(ContextValidationError) as error:
        build_document_identity(raw_identity(full_path=path))
    assert error.value.code == "INVALID_ARGUMENT"
    if path:
        assert path not in str(error.value)


def test_guid_precedence_normalization_and_saved_reopen_stability():
    guid = "ABCDEF00-1234-5678-9ABC-DEF012345678"
    first = build_document_identity(raw_identity(database_fingerprint_guid="{" + guid + "}"))
    second = build_document_identity(
        raw_identity(
            database_fingerprint_guid=guid.lower(),
            full_path=r"D:\moved.dwg",
            session_document_id="second-open-instance",
        )
    )
    expected = hashlib.sha256(("drawing-v1\0" + str(UUID(guid))).encode()).hexdigest()
    assert first.document_id == second.document_id == "dwg_" + expected[:32]
    assert first.session_document_id != second.session_document_id
    assert first.database_fingerprint_guid == str(UUID(guid))
    assert first.path_hash is None


def test_unsaved_identity_uses_adapter_uuid_even_with_guid():
    first = build_document_identity(
        raw_identity(is_saved=False, database_fingerprint_guid="bad-guid")
    )
    second = build_document_identity(
        raw_identity(is_saved=False, session_document_id="22222222-2222-4222-8222-222222222222")
    )
    assert first.document_id == "session_11111111111141118111111111111111"
    assert first.scope == "session" and first.path_hash is None
    assert first.document_id != second.document_id
    with pytest.raises(ContextValidationError):
        build_document_identity(raw_identity(is_saved=False, session_document_id="proxy-42"))


def test_invalid_guid_and_flags_are_rejected_without_input():
    for changes in (
        {"database_fingerprint_guid": "private-invalid-guid"},
        {"is_saved": 1},
        {"display_name": "x" * 256},
    ):
        with pytest.raises(ContextValidationError):
            build_document_identity(raw_identity(**changes))
    assert normalize_handle("a1") == "A1"
    with pytest.raises(ContextValidationError):
        normalize_handle("0xA1")
