"""In-process real-clock evidence; peak RSS is cumulative, never a hard enforcement claim."""

import argparse
import hashlib
import json
import platform
import re
import sys
import time
from dataclasses import asdict
from pathlib import Path

from autocad_mcp.advanced.bounds import BoundedExecutionFailure
from autocad_mcp.advanced.unfolding.metrics import VERIFIER_VERSION
from autocad_mcp.advanced.unfolding.models import MeshValidationError, decode_request, request_json
from autocad_mcp.advanced.unfolding.service import result_payload, unfold_surface
from autocad_mcp.advanced.unfolding.solver import SOLVER_VERSION

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE = PROJECT_ROOT / "tests/fixtures/unfolding/cases/exact-max-torus.json"


def torus_band(source: dict, face_count: int) -> dict:
    """First N canonical faces, referenced source vertices, every actual edge cut."""
    faces = sorted(source["faces"], key=lambda face: face["face_id"])[:face_count]
    referenced = {vertex for face in faces for vertex in face["vertex_ids"]}
    edges = sorted(
        {
            tuple(sorted((face["vertex_ids"][index], face["vertex_ids"][(index + 1) % 3])))
            for face in faces
            for index in range(3)
        }
    )
    return {
        "request_id": f"measure-torus-band-{face_count}",
        "units_label": source["units_label"],
        "vertices": [vertex for vertex in source["vertices"] if vertex["vertex_id"] in referenced],
        "faces": faces,
        "seam_edges": [list(edge) for edge in edges],
        "root_face_id": faces[0]["face_id"],
        "policy": dict(source["policy"], deterministic_seed=9041),
    }


def peak_rss() -> tuple[int | None, str]:
    try:
        import resource
    except ImportError:
        return None, "Unavailable on this host; no RSS claim"
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(raw if sys.platform == "darwin" else raw * 1024), (
        "Process-lifetime high-water RSS; cumulative across cases in this same process; bytes"
    )


def measure(host_label: str) -> dict:
    if re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", host_label) is None:
        raise ValueError("Use an explicit nonpersonal ASCII host label")
    source_bytes = SOURCE.read_bytes()
    source = json.loads(source_bytes)
    cases = []
    for count in (500, 2000, 4000):
        data = torus_band(source, count)
        canonical = request_json(decode_request(data)).encode("utf-8")
        entry = {
            "faces": count,
            "vertices": len(data["vertices"]),
            "seams": len(data["seam_edges"]),
            "policy": data["policy"],
            "input_digest": hashlib.sha256(canonical).hexdigest(),
            "input_bytes": len(canonical),
        }
        started = time.perf_counter()
        try:
            result = unfold_surface(data)
            wall = time.perf_counter() - started
            if isinstance(result, BoundedExecutionFailure):
                entry.update(
                    outcome=result.code.value, completed_iterations=result.completed_iterations
                )
            else:
                wire = json.dumps(
                    result_payload(result),
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                    allow_nan=False,
                ).encode()
                entry.update(
                    outcome="accepted",
                    result_digest=hashlib.sha256(wire).hexdigest(),
                    result_bytes=len(wire),
                    metrics=asdict(result.metrics),
                )
        except MeshValidationError as error:
            wall = time.perf_counter() - started
            entry.update(outcome=error.code, issues=[asdict(issue) for issue in error.issues])
        rss, semantics = peak_rss()
        entry.update(wall_seconds=wall, peak_rss_bytes=rss, peak_rss_semantics=semantics)
        cases.append(entry)
    return {
        "host_label": host_label,
        "os": platform.system(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "source_fixture_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "construction": (
            "First N source faces sorted by ID; referenced vertices; "
            "every actual edge as seam; seed 9041"
        ),
        "solver_version": SOLVER_VERSION,
        "verifier_version": VERIFIER_VERSION,
        "measurement": (
            "Single process, real injected-default monotonic clock; no subprocess/hard kill; "
            "timing/RSS excluded from product results"
        ),
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host-label", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    evidence = measure(args.host_label)
    encoded = (
        json.dumps(
            evidence, ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False
        )
        + "\n"
    ).encode()
    digest = hashlib.sha256(encoded).hexdigest()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    path = args.output_dir / (digest + ".json")
    if path.exists():
        if path.read_bytes() != encoded:
            raise ValueError("Evidence digest collision")
    else:
        with path.open("xb") as artifact:
            artifact.write(encoded)
    print(f"Evidence SHA-256: {digest}")  # noqa: T201 - measurement CLI only
    for case in evidence["cases"]:
        print(  # noqa: T201 - measurement CLI only
            f"{case['faces']} faces: {case['outcome']}, {case['wall_seconds']:.6f}s, "
            f"peak RSS {case['peak_rss_bytes']} bytes (cumulative)"
        )


if __name__ == "__main__":
    main()
