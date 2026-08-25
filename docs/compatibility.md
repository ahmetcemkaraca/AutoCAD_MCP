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
| Full AutoCAD 2026 | Windows | Targeted; first validation environment | A real installation is available, but the stable smoke suite has not run |
| AutoCAD LT | Windows | Out of scope | Required 3D and automation behavior is not part of the product target |

No AutoCAD release is marked verified by the stewardship documentation pull request.

## Host platforms

| Host | Product runtime | Test use |
| --- | --- | --- |
| Windows | Targeted for full AutoCAD 2021-2026 | Pure Python, MCP contract, and real AutoCAD tests |
| Linux | Out of scope for AutoCAD operation | Pure Python and MCP contract tests only |
| macOS | Out of scope | No supported AutoCAD COM runtime or planned test matrix |

## Python

`pyproject.toml` declares Python 3.12 or newer. The stewardship syntax check used Python 3.14.4, which does not establish dependency or COM compatibility. The stable-core delivery must test the locked dependencies on supported Windows Python releases before narrowing or expanding the Python claim.

## Capability policy

The target adapter will detect required COM capabilities after connecting. A feature should return a structured unsupported-capability result when the connected release lacks a required member; it should not assume that every API behaves identically across AutoCAD 2021-2026.

## Promoting a release to verified

A release becomes verified only after the canonical smoke suite records:

1. dependency installation;
2. MCP startup and initialization;
3. server status and document discovery;
4. line and circle creation in a disposable drawing;
5. entity query and property extraction;
6. Undo cleanup;
7. clean shutdown and reconnect behavior.

Feature-specific compatibility, such as visual capture or 3D operations, is recorded separately after its own integration tests pass.
