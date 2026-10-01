"""Deterministic strict JSON encoding for the versioned context contract."""

import json
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import datetime
from typing import Any

from .models import AnalyzeDrawingResult, DrawingSnapshot
from .validation import (
    MAX_RESULT_BYTES,
    MAX_SNAPSHOT_BYTES,
    ContextValidationError,
    record_from_payload,
    require,
)


def record_to_payload(record: Any) -> Any:
    """Produce JSON primitives without retaining mutable domain containers."""
    if is_dataclass(record) and not isinstance(record, type):
        return {
            field.name: record_to_payload(getattr(record, field.name)) for field in fields(record)
        }
    if isinstance(record, Mapping):
        return {key: record_to_payload(value) for key, value in record.items()}
    if isinstance(record, tuple):
        return [record_to_payload(value) for value in record]
    if isinstance(record, datetime):
        return record.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return record


def record_to_json(record: Any) -> str:
    """Encode context records as sorted-key compact UTF-8-compatible JSON."""
    return json.dumps(
        record_to_payload(record),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    )


def _bounded_payload(record: Any, limit: int, code: str) -> dict[str, object]:
    result: dict[str, object] = record_to_payload(record)
    require(
        len(record_to_json(result).encode("utf-8")) <= limit,
        "Serialized context exceeds byte bound",
        code=code,
    )
    return result


def snapshot_to_json(snapshot: DrawingSnapshot) -> dict[str, object]:
    require(type(snapshot) is DrawingSnapshot, "Expected a DrawingSnapshot")
    return _bounded_payload(snapshot, MAX_SNAPSHOT_BYTES, "COMPLETE_SNAPSHOT_LIMIT")


def snapshot_from_json(value: Mapping[str, object]) -> DrawingSnapshot:
    require(isinstance(value, Mapping), "Expected a snapshot JSON object")
    result: DrawingSnapshot = record_from_payload(DrawingSnapshot, value)
    _bounded_payload(result, MAX_SNAPSHOT_BYTES, "COMPLETE_SNAPSHOT_LIMIT")
    return result


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON field")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ContextValidationError("Non-finite JSON number")


def snapshot_from_json_text(payload: str) -> DrawingSnapshot:
    """Decode JSON text with duplicate-key checks before the mapping boundary."""
    require(isinstance(payload, str), "Expected snapshot JSON text")
    try:
        measured = len(payload.encode("utf-8"))
    except UnicodeEncodeError:
        raise ContextValidationError("Snapshot JSON must be valid UTF-8") from None
    require(
        measured <= MAX_SNAPSHOT_BYTES,
        "Snapshot exceeds byte bound",
        code="COMPLETE_SNAPSHOT_LIMIT",
    )
    try:
        value = json.loads(
            payload, object_pairs_hook=_unique_object, parse_constant=_reject_constant
        )
    except (ValueError, RecursionError) as error:
        if isinstance(error, ContextValidationError):
            raise
        raise ContextValidationError("Invalid snapshot JSON") from None
    return snapshot_from_json(value)


def analyze_result_to_json(result: AnalyzeDrawingResult) -> dict[str, object]:
    require(type(result) is AnalyzeDrawingResult, "Expected an AnalyzeDrawingResult")
    return _bounded_payload(result, MAX_RESULT_BYTES, "PAYLOAD_LIMIT")
