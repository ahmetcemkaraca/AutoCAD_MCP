"""Pure persistent document identity; raw drawing paths never leave this helper."""

import hashlib
import ntpath
from typing import Protocol
from unicodedata import normalize
from uuid import UUID

from .models import DocumentIdentity, DocumentIdentityScope
from .validation import ContextValidationError, normalize_handle, require

__all__ = ["build_document_identity", "normalize_handle"]


class AdapterDocumentIdentityInput(Protocol):
    """Structural seam until the additive adapter identity is available."""

    @property
    def display_name(self) -> str: ...
    @property
    def full_path(self) -> str | None: ...
    @property
    def database_fingerprint_guid(self) -> str | None: ...
    @property
    def session_document_id(self) -> str: ...
    @property
    def is_saved(self) -> bool: ...
    @property
    def is_read_only(self) -> bool: ...


def _uuid(value: str) -> UUID:
    require(isinstance(value, str), "Expected a document UUID")
    try:
        return UUID(value)
    except ValueError:
        raise ContextValidationError("Invalid document UUID") from None


def _windows_path(value: str | None) -> str:
    require(
        isinstance(value, str) and bool(value) and "\0" not in value,
        "Saved document requires an absolute Windows path",
    )
    assert isinstance(value, str)
    path = normalize("NFC", value).replace("/", "\\")
    if path[:8].casefold() == "\\\\?\\unc\\":
        path = "\\\\" + path[8:]
    elif path.startswith("\\\\?\\"):
        path = path[4:]
    require(not path.startswith("\\\\.\\"), "Device paths are not drawing paths")
    drive, tail = ntpath.splitdrive(path)
    drive_absolute = (
        len(drive) == 2 and drive[0].isascii() and drive[0].isalpha() and drive[1] == ":"
    )
    unc_parts = drive.split("\\")
    unc_absolute = (
        drive.startswith("\\\\")
        and len(unc_parts) == 4
        and all(unc_parts[2:])
        and unc_parts[2] not in (".", "?")
    )
    require(
        (drive_absolute or unc_absolute) and tail.startswith("\\"),
        "Saved document requires an absolute Windows path",
    )
    result = normalize("NFC", ntpath.normpath(path).casefold())
    try:
        result.encode("utf-8")
    except UnicodeEncodeError:
        raise ContextValidationError("Invalid Windows path encoding") from None
    return result


def build_document_identity(raw: AdapterDocumentIdentityInput) -> DocumentIdentity:
    """Prefer a saved database GUID; otherwise use path hash or unsaved session UUID."""
    require(type(raw.is_saved) is bool and type(raw.is_read_only) is bool, "Invalid document flags")
    require(
        isinstance(raw.display_name, str) and 0 < len(raw.display_name) <= 255,
        "Invalid document display name",
    )
    require(
        isinstance(raw.session_document_id, str)
        and 0 < len(raw.session_document_id) <= 255
        and "\0" not in raw.session_document_id,
        "Invalid document session identity",
    )
    guid = None
    path_hash = None
    scope: DocumentIdentityScope
    if not raw.is_saved:
        document_id = "session_" + _uuid(raw.session_document_id).hex
        scope = "session"
    else:
        if raw.database_fingerprint_guid is not None:
            guid = str(_uuid(raw.database_fingerprint_guid))
            digest = hashlib.sha256(("drawing-v1\0" + guid).encode()).hexdigest()
        else:
            path_hash = hashlib.sha256(_windows_path(raw.full_path).encode()).hexdigest()
            digest = path_hash
        document_id = "dwg_" + digest[:32]
        scope = "drawing"
    return DocumentIdentity(
        document_id,
        scope,
        normalize("NFC", raw.display_name),
        guid,
        path_hash,
        raw.session_document_id,
        raw.is_saved,
        raw.is_read_only,
    )
