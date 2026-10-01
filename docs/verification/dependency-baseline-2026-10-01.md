# Dependency baseline and installer retirement — 2026-10-01

The active package uses PEP 621 metadata and `uv.lock`. The obsolete Poetry lock
and unsupported root Docker/Compose artifacts are retired under the maintainer's
instruction to finish the remaining implementation tasks, including the listed
old-installer cleanup. [Decision 0001](../decisions/0001-container-artifact-disposition.md)
records the container rationale and Git-history recovery path.

## Fresh cross-platform evidence

[Portable tests run 36884626607](https://github.com/ahmetcemkaraca/AutoCAD_MCP/actions/runs/36884626607)
tested commit `b8574cbee5bb9917f7514fc8e9e3ce13142f5b75`, subsequently merged through
[PR #6](https://github.com/ahmetcemkaraca/AutoCAD_MCP/pull/6).

| Host | Interpreter | Test result |
| --- | --- | --- |
| Hosted Ubuntu | 64-bit CPython 3.12.3 | 227 passed, 9 skipped |
| Hosted Windows Server 2025 | 64-bit CPython 3.12.10 | 233 passed, 3 skipped |

Both clean jobs used uv 0.12.7 with cache disabled. They passed `uv lock --check`,
`uv sync --frozen --group dev`, interpreter/platform-marker checks, the full
automated suite, active Ruff and mypy checks, syntax/manifest validation, delayed
COM-import assertions, and a clean-worktree check. The workflow prints the
tested commit and `uv.lock` blob identity for reproducibility.

Windows COM packages were present only on Windows; no AutoCAD process was
attached to or started. Protocol calls use an injected unavailable service, and
separate real module-entry checks request only the catalog. AutoCAD tests remain
opt-in; this evidence does not verify AutoCAD or a Windows desktop user workflow.

## Removal boundary

- `poetry.lock` was inactive since the uv migration. The clean Windows witness
  required before retiring it now exists, alongside Linux evidence.
- `Dockerfile` and `docker-compose.yml` targeted an unsupported Linux HTTP server
  and missing inputs; no canonical runtime or CI path consumes them.
- No dependency requirement, uv lock content, canonical launch command, or source
  code changes in this retirement.
- Restore any removed file from commit `2cb0ea4` if a reviewed new consumer
  requires it; do not advertise the historical container as supported.

EPIC-01's dependency setup has cross-platform evidence. EPIC-03 and later
feature-specific real-AutoCAD acceptance remain pending operator execution.
