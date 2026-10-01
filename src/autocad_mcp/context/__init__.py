"""Pure immutable drawing context contract and strict JSON serialization."""

from .serialization import analyze_result_to_json, snapshot_from_json, snapshot_to_json
from .validation import ContextValidationError

__all__ = [
    "ContextValidationError",
    "analyze_result_to_json",
    "snapshot_from_json",
    "snapshot_to_json",
]
