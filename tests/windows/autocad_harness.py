"""COM-free read-only policy for the disposable AutoCAD smoke drawing."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from autocad_lease import assert_guard_run_current_user_system_acl
from drawing_copy_guard import DrawingCopyEvidence, DrawingCopyGuard


@dataclass(frozen=True)
class ReadOnlyDrawingFingerprint:
    file_sha256: str
    file_size: int
    file_mtime_ns: int
    dbmod: int
    entity_count: int
    entity_digest: str


@dataclass(frozen=True)
class _FileFingerprint:
    file_sha256: str
    file_size: int
    file_mtime_ns: int


class ReadOnlyAutoCADHarness:
    """Open one guarded copy read-only and reject every unsafe lifecycle change."""

    def __init__(
        self,
        *,
        lease: object,
        guard: DrawingCopyGuard,
        opener: Callable[[str, bool], object],
        acl_verifier: Callable[[Path], None] = assert_guard_run_current_user_system_acl,
    ) -> None:
        self._lease = lease
        self._guard = guard
        self._opener = opener
        self._acl_verifier = acl_verifier
        self._document: object | None = None
        self._file_fingerprint: _FileFingerprint | None = None
        self._fingerprint: ReadOnlyDrawingFingerprint | None = None
        self._close_attempted = False

    @property
    def fingerprint(self) -> ReadOnlyDrawingFingerprint:
        if self._fingerprint is None:
            raise RuntimeError("read-only drawing has not been opened")
        return self._fingerprint

    def open(self) -> object:
        """Assert controller and ACL safety before opening only the guard copy."""
        document: object | None = None
        try:
            self._assert_owned()
            self._verify_acl()
            self._file_fingerprint = _file_fingerprint(self._guard.copy_path)
            document = self._opener(str(self._guard.copy_path), True)
            self._validate_document(document)
            self._assert_file_unchanged()
            self._fingerprint = self._capture_drawing_fingerprint(document)
            self._document = document
            return document
        except BaseException as error:
            if document is not None:
                self._attempt_close_safely(document, error)
            self._preserve(error)
            raise

    def assert_unchanged(self) -> ReadOnlyDrawingFingerprint:
        """Revalidate controller/document identity and all fingerprint fields."""
        try:
            self._assert_owned()
            self._verify_acl()
            document = self._document_or_raise()
            self._validate_document(document)
            self._assert_file_unchanged()
            current = self._capture_drawing_fingerprint(document)
            if current != self.fingerprint:
                raise RuntimeError("read-only drawing fingerprint changed")
            return current
        except BaseException as error:
            self._preserve(error)
            raise

    def close(self) -> DrawingCopyEvidence:
        """Verify, close once without saving, recheck the copy, then clean up."""
        try:
            self._assert_owned()
            self._verify_acl()
            document = self._document_or_raise()
            self._validate_document(document)
            self.assert_unchanged()
            self._close_once(document)
            self._assert_file_unchanged()
            self._verify_acl()
            return self._guard.finalize(preserve=False, reason="read-only smoke completed")
        except BaseException as error:
            document = self._document
            if document is not None:
                self._attempt_close_safely(document, error)
            self._preserve(error)
            raise

    def _document_or_raise(self) -> object:
        if self._document is None:
            raise RuntimeError("read-only drawing has not been opened")
        return self._document

    def _assert_owned(self) -> None:
        assert_owned = getattr(self._lease, "assert_owned", None)
        if not callable(assert_owned):
            raise RuntimeError("AutoCAD verification lease has no ownership assertion")
        assert_owned()

    def _verify_acl(self) -> None:
        self._acl_verifier(self._guard.copy_path.parent)

    def _validate_document(self, document: object) -> None:
        self._guard.assert_active_full_name(str(document.FullName))  # type: ignore[attr-defined]
        if document.ReadOnly is not True:  # type: ignore[attr-defined]
            raise RuntimeError("AutoCAD document is not read-only")

    def _assert_file_unchanged(self) -> None:
        if self._file_fingerprint is None:
            raise RuntimeError("read-only drawing file fingerprint has not been captured")
        if _file_fingerprint(self._guard.copy_path) != self._file_fingerprint:
            raise RuntimeError("read-only drawing file fingerprint changed")

    def _attempt_close_safely(self, document: object, original_error: BaseException) -> None:
        if self._close_attempted:
            return
        try:
            self._assert_owned()
            self._verify_acl()
            self._validate_document(document)
            self._close_once(document)
        except BaseException as close_error:
            original_error.add_note(f"close without save also failed: {close_error}")

    def _close_once(self, document: object) -> None:
        if self._close_attempted:
            return
        close = getattr(document, "Close", None)
        if not callable(close):
            raise RuntimeError("AutoCAD document has no close operation")
        self._close_attempted = True
        self._guard.close_without_save(close)

    def _preserve(self, error: BaseException) -> None:
        try:
            self._guard.finalize(preserve=True, reason=f"read-only safety failure: {error}")
        except BaseException as finalize_error:
            error.add_note(f"guard preservation also failed: {finalize_error}")

    def _capture_drawing_fingerprint(self, document: object) -> ReadOnlyDrawingFingerprint:
        file_fingerprint = self._file_fingerprint
        if file_fingerprint is None:
            raise RuntimeError("read-only drawing file fingerprint has not been captured")
        entities = tuple(_entities(document))
        return ReadOnlyDrawingFingerprint(
            file_sha256=file_fingerprint.file_sha256,
            file_size=file_fingerprint.file_size,
            file_mtime_ns=file_fingerprint.file_mtime_ns,
            dbmod=_dbmod(document),
            entity_count=len(entities),
            entity_digest=_entity_digest(entities),
        )


def _file_fingerprint(path: Path) -> _FileFingerprint:
    file_stat = path.stat()
    return _FileFingerprint(_sha256(path), file_stat.st_size, file_stat.st_mtime_ns)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dbmod(document: object) -> int:
    try:
        value = document.GetVariable("DBMOD")  # type: ignore[attr-defined]
    except AttributeError:
        value = document.DBMOD  # type: ignore[attr-defined]
    if isinstance(value, bool) or not isinstance(value, int):
        raise RuntimeError("AutoCAD DBMOD is not an integer")
    return value


def _entities(document: object) -> Iterable[object]:
    try:
        model_space = document.ModelSpace  # type: ignore[attr-defined]
    except AttributeError:
        raise RuntimeError("AutoCAD document has no model space") from None
    if model_space is None:
        raise RuntimeError("AutoCAD document has no model space")
    return model_space


def _entity_digest(entities: Iterable[object]) -> str:
    ordered = [
        {
            "object_id": entity.ObjectID,  # type: ignore[attr-defined]
            "handle": entity.Handle,  # type: ignore[attr-defined]
            "object_name": entity.ObjectName,  # type: ignore[attr-defined]
            "layer": entity.Layer,  # type: ignore[attr-defined]
        }
        for entity in entities
    ]
    material = json.dumps(ordered, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
