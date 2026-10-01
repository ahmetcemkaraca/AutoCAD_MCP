"""Portable context fake with signed continuation; no simulated COM engine."""

import hashlib
import secrets
from dataclasses import asdict
from datetime import timedelta
from fnmatch import fnmatchcase
from types import SimpleNamespace
from typing import cast
from unicodedata import normalize

from autocad_mcp.adapter.context_protocol import (
    AdapterContextIssue,
    AdapterDocumentContext,
    AdapterDocumentRevisionToken,
    AdapterEntityFacts,
    AdapterEntityPage,
    AdapterEntityReadRequest,
    ContextAutoCADAdapter,
    ContextInclude,
    request_filters,
)
from autocad_mcp.adapter.fake import FakeAutoCADAdapter
from autocad_mcp.adapter.protocol import AdapterError, AdapterErrorCode, EntityDetails
from autocad_mcp.context.identity import build_document_identity, normalize_handle
from autocad_mcp.context.models import EntityContext, EntityQueryFilters
from autocad_mcp.context.pagination import (
    Clock,
    CursorCodec,
    PageCursor,
    SystemClock,
    entity_sort_key,
    filter_digest,
    normalize_filters,
)
from autocad_mcp.context.validation import require


def _key(raw: AdapterEntityFacts) -> tuple[int, str, int, str]:
    view = SimpleNamespace(
        space=SimpleNamespace(kind=raw.space_kind, layout_name=raw.layout_name),
        identity=SimpleNamespace(handle=raw.handle),
    )
    return entity_sort_key(cast(EntityContext, view))


def _glob(pattern: str, value: str) -> bool:
    # Escape set syntax; stdlib star translation avoids exponential backtracking.
    return fnmatchcase(value, pattern.replace("[", "[[]"))


def _matches(
    item: AdapterEntityFacts, request: AdapterEntityReadRequest, filters: EntityQueryFilters
) -> bool:
    def nfc(value: str) -> str:
        return normalize("NFC", value)

    for values, value in (
        (filters.spaces, item.space_kind),
        (filters.layout_names, item.layout_name or ""),
        (filters.entity_types, item.object_name),
        (filters.handles, item.handle),
    ):
        if values and nfc(value) not in values:
            return False
    layer = nfc(cast(str, item.layer.get("name", "")))
    if (filters.layer_names or filters.layer_globs) and not (
        layer in filters.layer_names
        or any(_glob(pattern, layer) for pattern in filters.layer_globs)
    ):
        return False
    if request.intersects_wcs is not None:
        if item.space_kind == "block_definition" or item.bounds is None:
            return False
        query = request.intersects_wcs
        if any(
            item.bounds[axis] > query[axis + 3] or item.bounds[axis + 3] < query[axis]
            for axis in range(3)
        ):
            return False
    return True


class FakeContextAutoCADAdapter(FakeAutoCADAdapter):
    """Store pure supplied values; hooks deliberately model interrupted/changing acquisition."""

    def __init__(
        self,
        *,
        document: AdapterDocumentContext,
        entities: tuple[AdapterEntityFacts, ...],
        revision_token: AdapterDocumentRevisionToken | None = None,
        clock: Clock | None = None,
        cursor_secret: bytes | None = None,
        connected: bool = True,
    ) -> None:
        self._document = document
        self._clock = clock or SystemClock()
        self._codec = CursorCodec(
            clock=self._clock,
            secret=secrets.token_bytes(32) if cursor_secret is None else cursor_secret,
        )
        self._generation = 1
        self._raw_entities: tuple[AdapterEntityFacts, ...] = ()
        self._partial: tuple[AdapterContextIssue, ...] | None = None
        self._revision: AdapterDocumentRevisionToken | None = revision_token or self._new_revision()
        super().__init__(
            connected=connected, document_name=document.identity.display_name, entities=()
        )
        self.set_entities(entities, advance_revision=False)

    def _new_revision(self) -> AdapterDocumentRevisionToken:
        return AdapterDocumentRevisionToken(
            "1.0",
            self._document.identity.session_document_id,
            "synthetic",
            f"synthetic-revision-{self._generation}",
        )

    def advance_revision(self) -> None:
        self._generation += 1
        self._revision = self._new_revision()

    def set_revision_token(self, token: AdapterDocumentRevisionToken | None) -> None:
        self._revision = token

    def set_document(self, document: AdapterDocumentContext) -> None:
        self._document = document
        self._document_name = document.identity.display_name
        self.advance_revision()

    def set_entities(
        self, entities: tuple[AdapterEntityFacts, ...], *, advance_revision: bool = True
    ) -> None:
        require(
            type(entities) is tuple and all(type(item) is AdapterEntityFacts for item in entities),
            "Invalid synthetic entity records",
        )
        require(
            len({item.handle for item in entities}) == len(entities),
            "Duplicate entity handle",
            code="SNAPSHOT_INCOMPLETE",
        )
        self._raw_entities = tuple(sorted(entities, key=_key))
        self._entities = tuple(
            EntityDetails(
                item.object_id, item.handle, item.object_name, cast(str, item.layer.get("name"))
            )
            for item in entities
            if item.object_id is not None
        )
        if advance_revision:
            self.advance_revision()

    def inject_partial_once(self, *, issues: tuple[AdapterContextIssue, ...] = ()) -> None:
        self._partial = issues

    def _operation(self, name: str, argument: object = None) -> None:
        self._calls += ((name, argument),)
        error = self._next_error
        self._next_error = None
        if error is not None:
            raise error
        if not self._connected:
            raise AdapterError(
                AdapterErrorCode.AUTOCAD_UNAVAILABLE, "Full AutoCAD is unavailable", retryable=True
            )
        if self._document_name is None:
            raise AdapterError(AdapterErrorCode.NO_ACTIVE_DOCUMENT, "No active document")

    def context_capabilities(self) -> tuple[str, ...]:
        self._operation("context_capabilities")
        return ("document_context", "document_revision", "entity_facts", "entity_paging")

    def read_document_context(self) -> AdapterDocumentContext:
        self._operation("read_document_context")
        return self._document

    def read_document_revision(self) -> AdapterDocumentRevisionToken:
        self._operation("read_document_revision")
        return self._token()

    def _token(self) -> AdapterDocumentRevisionToken:
        require(
            self._revision is not None,
            "Revision witness is unavailable",
            code="REVISION_TOKEN_UNAVAILABLE",
        )
        token = cast(AdapterDocumentRevisionToken, self._revision)
        require(
            token.session_document_id == self._document.identity.session_document_id,
            "Revision session changed",
            code="STALE_CURSOR",
        )
        return token

    def entity_facts_by_handles(
        self, handles: tuple[str, ...], include: ContextInclude
    ) -> tuple[AdapterEntityFacts, ...]:
        self._operation("entity_facts_by_handles", (handles, include))
        require(type(handles) is tuple and 1 <= len(handles) <= 256, "Invalid handle lookup count")
        require(type(include) is ContextInclude, "Invalid include flags")
        normalized = tuple(normalize_handle(handle) for handle in handles)
        require(len(set(normalized)) == len(normalized), "Duplicate handle lookup")
        index = {item.handle: item for item in self._raw_entities}
        require(
            all(handle in index for handle in normalized),
            "Entity handle was not found",
            code="ENTITY_NOT_FOUND",
        )
        return tuple(index[handle] for handle in normalized)

    def _filtered(
        self, request: AdapterEntityReadRequest
    ) -> tuple[tuple[AdapterEntityFacts, ...], tuple[AdapterContextIssue, ...]]:
        filters = normalize_filters(request_filters(request))
        issues: tuple[AdapterContextIssue, ...] = ()
        if filters.intersects_wcs is not None:
            require(
                "block_definition" not in filters.spaces,
                "Definition coordinates have no drawing WCS projection",
                code="UNSUPPORTED_CAPABILITY",
            )
            if not filters.spaces and any(
                item.space_kind == "block_definition" for item in self._raw_entities
            ):
                issues = (
                    AdapterContextIssue(
                        "UNSUPPORTED_CAPABILITY",
                        "definition_wcs_projection",
                        None,
                        None,
                        "Definition coordinates have no drawing WCS projection",
                    ),
                )

        return tuple(
            item for item in self._raw_entities if _matches(item, request, filters)
        ), issues

    def read_entity_page(self, request: AdapterEntityReadRequest) -> AdapterEntityPage:
        self._operation("read_entity_page", request)
        require(type(request) is AdapterEntityReadRequest, "Invalid raw entity request")
        token = self._token()
        revision = "sha256:" + hashlib.sha256(token.opaque_value.encode()).hexdigest()
        document = build_document_identity(self._document.identity)
        digest = filter_digest(request_filters(request), asdict(request.include))
        source, issues = self._filtered(request)
        offset = 0
        if request.cursor is not None:
            cursor = self._codec.decode(request.cursor)
            require(
                cursor.kind == "live_query"
                and cursor.document_id == document.document_id
                and cursor.session_id == document.session_document_id,
                "Cursor document session changed",
                code="STALE_CURSOR",
            )
            require(
                cursor.revision_token_digest == revision,
                "Cursor revision changed",
                code="STALE_CURSOR",
            )
            require(
                cursor.filter_digest == digest and cursor.page_size == request.page_size,
                "Cursor request changed",
                code="INVALID_CURSOR",
            )
            boundary = next(
                (index for index, item in enumerate(source) if item.handle == cursor.last_handle),
                None,
            )
            require(boundary is not None, "Cursor boundary is missing", code="INVALID_CURSOR")
            offset = cast(int, boundary) + 1
        entities = source[offset : offset + request.page_size]
        next_cursor = None
        if offset + len(entities) < len(source):
            now = self._clock.now()
            next_cursor = self._codec.encode(
                PageCursor(
                    "live_query",
                    document.document_id,
                    document.session_document_id,
                    digest,
                    request.page_size,
                    entities[-1].handle,
                    now,
                    now + timedelta(seconds=900),
                    revision_token_digest=revision,
                )
            )
        partial = self._partial
        self._partial = None
        return AdapterEntityPage(
            "1.0", token, entities, next_cursor, partial is not None, issues + (partial or ())
        )


class StaticContextAdapterProvider:
    def __init__(self, adapter: ContextAutoCADAdapter) -> None:
        self._adapter = adapter

    def get(self) -> ContextAutoCADAdapter:
        return self._adapter
