# Compatibility

Compatibility claims require a repeatable test result on the named environment. The project distinguishes targeted environments from verified environments.

## AutoCAD releases

| Product | Platform | Status | Evidence |
| --- | --- | --- | --- |
| Full AutoCAD 2021 | Windows | Targeted, not verified | No recorded real-installation test |
| Full AutoCAD 2022 | Windows | Targeted, not verified | No recorded real-installation test |
| Full AutoCAD 2023 | Windows | Targeted, not verified | No recorded real-installation test |
| Full AutoCAD 2024 | Windows | Targeted, not verified | No recorded real-installation test |
| Full AutoCAD 2025 | Windows | Targeted, not verified | Historical claims were not reproducible from the adopted tests |
| Full AutoCAD 2026 | Windows | Targeted, not verified; first validation environment | The opt-in read-only smoke is prepared; no real-installation result is recorded |
| AutoCAD LT | Windows | Out of scope | Required 3D and automation behavior is not part of the product target |

No AutoCAD release is currently marked verified.

## Host platforms

| Host | Product runtime | Test use |
| --- | --- | --- |
| Windows | Targeted for full AutoCAD 2021-2026 | Pure Python, MCP contract, and real AutoCAD tests |
| Linux | Out of scope for AutoCAD operation | Pure Python and MCP contract tests only |
| macOS | Out of scope | No supported AutoCAD COM runtime or planned test matrix |

## Python

`pyproject.toml` declares Python 3.12 or newer and the committed `uv.lock`
supports a frozen Linux development sync. The first real-device smoke requires
64-bit CPython 3.12 exactly and records that interpreter in its local evidence
log. A Windows frozen sync has not yet been recorded, so this does not claim
Windows dependency-installation verification.

## Capability policy

The implemented adapter detects required COM capabilities after connecting. A
feature returns a structured unsupported-capability result when the connected
release lacks a required member; it does not assume that every API behaves
identically across AutoCAD 2021-2026.

## Promoting a compatibility scope to verified

Verification is feature-specific; a passing narrow scope does not promote an entire AutoCAD release. The first read-only Stable-core scope records:

1. frozen dependency installation;
2. MCP startup and initialization;
3. server status and document discovery;
4. entity listing and property extraction from a guarded disposable copy opened read-only;
5. unchanged source/copy hashes and drawing fingerprint;
6. clean shutdown; and
7. reconnect behavior.

Drawing mutation is a separate later scope. Its verification additionally requires trusted human approval, stale-state rejection, a fresh disposable copy per case, successful line/circle application through the edit-plan path, Undo recovery, injected mid-plan failure, and persistent `rollback_failed` handling. Visual capture, semantic analysis, and any future 3D operation likewise retain separate compatibility evidence. A release row may be promoted beyond `Targeted` only when canonical documentation names the exact verified scopes and links their reproducible records.
