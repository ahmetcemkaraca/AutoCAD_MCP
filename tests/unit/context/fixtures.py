"""Complete, synthetic context facts shared by contract tests."""

from datetime import UTC, datetime

from autocad_mcp.context.serialization import snapshot_from_json


def snapshot_payload():
    return {
        "schema_version": "1.0",
        "snapshot_id": "ds1_" + "a" * 32,
        "reference": {
            "snapshot_id": "ds1_" + "a" * 32,
            "document_id": "dwg_" + "b" * 32,
            "session_id": "session-1",
            "fingerprint": "sha256:" + "c" * 64,
        },
        "captured_at": "2026-10-01T12:34:56.789Z",
        "document": {
            "document_id": "dwg_" + "b" * 32,
            "scope": "drawing",
            "display_name": "fixture.dwg",
            "database_fingerprint_guid": None,
            "path_hash": None,
            "session_document_id": "session-1",
            "is_saved": True,
            "is_read_only": False,
        },
        "fingerprint": {
            "algorithm": "sha256-cad-facts-v1",
            "content_digest": "sha256:" + "c" * 64,
            "presentation_digest": "sha256:" + "d" * 64,
            "coverage": "enumerated-entity-facts-v1",
            "complete": True,
            "incomplete_reasons": [],
            "entity_count": 1,
        },
        "units": {"insunits_code": 4, "name": "millimeters", "meters_per_unit": 0.001},
        "tolerance": {"linear": 0.01, "angular_radians": 0.001, "source": "drawing_units_default"},
        "active_context": {
            "space": {
                "display_space": "model",
                "active_layout_name": "Model",
                "viewport_object_id": None,
                "viewport_object_id_scope": None,
            },
            "ucs": {
                "name": None,
                "origin_wcs": {"x": 0, "y": 0, "z": 0},
                "x_axis_wcs": {"x": 1, "y": 0, "z": 0},
                "y_axis_wcs": {"x": 0, "y": 1, "z": 0},
                "is_orthonormal": True,
            },
            "view": {
                "center_ucs": {"x": 0, "y": 0},
                "target_wcs": {"x": 0, "y": 0, "z": 0},
                "direction_wcs": {"x": 0, "y": 0, "z": 1},
                "width": 100,
                "height": 100,
                "twist_radians": 0,
                "projection": "parallel",
                "visual_style": None,
            },
        },
        "entities": [
            {
                "identity": {
                    "handle": "A1",
                    "object_id": 42,
                    "object_id_scope": "session",
                    "object_name": "AcDbLine",
                    "dxf_name": "LINE",
                },
                "space": {"kind": "model", "layout_name": "Model", "owner_block_handle": None},
                "layer": {"name": "0", "is_off": False, "is_frozen": False, "is_locked": False},
                "style": {
                    "color_index": 256,
                    "true_color_rgb": [12, 34, 56],
                    "linetype": None,
                    "linetype_scale": None,
                    "lineweight": None,
                    "transparency": None,
                    "visible": True,
                },
                "geometry": {
                    "kind": "line",
                    "start": {"x": 0, "y": 0, "z": 0},
                    "end": {"x": 5, "y": 6, "z": 0},
                },
                "bounds": {
                    "minimum": {"x": 0, "y": 0, "z": 0},
                    "maximum": {"x": 5, "y": 6, "z": 0},
                },
                "block": {
                    "effective_name": "fixture",
                    "definition_handle": "B1",
                    "attribute_values": {"KEY": "VALUE"},
                    "is_dynamic": False,
                },
                "text": None,
                "dimension": None,
                "relationships": [],
                "fact_evidence": [
                    {
                        "fact_path": "/geometry/start",
                        "source": "autocad_com",
                        "member": "StartPoint",
                        "status": "observed",
                    }
                ],
                "capability_issues": [],
                "state_digest": "sha256:" + "e" * 64,
            }
        ],
        "capability_issues": [],
        "materialization": {
            "builder_version": "snapshot-builder-v1",
            "complete": True,
            "entity_count": 1,
            "relationship_count": 0,
            "canonical_byte_count": 3000,
            "revision_token_digest": "sha256:" + "f" * 64,
        },
    }


def snapshot():
    return snapshot_from_json(snapshot_payload())


CAPTURED_AT = datetime(2026, 10, 1, 12, 34, 56, 789000, tzinfo=UTC)
