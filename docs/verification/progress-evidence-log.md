# Progress evidence log

## Baseline inventory

- Baseline commit: `00207ed084e9ef81538b5283615e689d483632d1` (`docs: add modernization epic portfolio`, 2026-08-29).
- Direct runtime dependencies: Flask, pyautocad, NumPy, SciPy, pypiwin32, FastAPI, uvicorn[standard], python-multipart, MCP, websockets, aiofiles, Jinja2, requests, python-dotenv, and cryptography. Optional ML dependencies: scikit-learn, transformers, torch, and accelerate. Development dependencies: pytest, pytest-cov, pytest-html, pytest-mock, Black, Ruff, mypy, Bandit, and safety.
- Relevant Poetry-lock inventory: `mcp` 1.12.2; `pyautocad` 0.2.0; `pypiwin32` 223; transitive `pywin32` 311.
- Current seven schemas: `draw_line`, `draw_circle`, `extrude_profile`, `revolve_profile`, `list_entities`, `get_entity_info`, and `server_status`.
- Source/launch mismatch: `mcp.json` launches `uv run python src/server.py` with `PYTHONPATH=src`; the approved EPIC-01 target is `uv run python -m src.server`, and EPIC-02 later changes the canonical target to `python -m autocad_mcp.server` while retaining a tested `src.server` shim.
- Stale Docker observations: `Dockerfile` copies absent `requirements.txt` and `requirements-prod.txt`, advertises 1.0.0, selects an enhanced server, and probes `/health`; `docker-compose.yml` references absent `init.sql`, `nginx.conf`, and `ssl/`, and declares unused Redis, PostgreSQL, and nginx services. A Linux container cannot host the supported Windows COM runtime.
- Baseline tracking constraint: `.gitignore` line 72 globally ignores `test_*.py`, which hides the required E01-WP2 metadata test. Task 2 owns the narrow remediation `!tests/**/test_*.py`; this ledger does not modify `.gitignore`.

## Evidence status

| Date | Scope | Evidence status | Boundary statement |
| --- | --- | --- | --- |
| 2026-08-29 | Controller ledger setup | Baseline source inventory recorded; no implementation gate passed | This is observed source evidence only. |
| 2026-08-29 | Linux/fake checks | No result recorded | Future Linux unit, mocked-COM, fake-adapter, and MCP-contract results demonstrate only their stated automated contracts; they are not AutoCAD compatibility evidence. |
| 2026-08-29 | Real AutoCAD | No result recorded | Windows full-AutoCAD evidence is human-operator-only under E03-WP7 and requires the specified interactive session, lease, disposable read-only DWG, fingerprints, and reviewer gates. It is never substituted by Linux/fake checks. |

## Final Linux automated evidence

The final portable gate ran from the isolated
`codex/local-autocad-testable` worktree with `uv 0.12.7`, 64-bit CPython
3.12.14, and Linux 7.0.0-30-generic. These are Linux/pure-contract results,
not Windows or AutoCAD compatibility evidence.

| Scope | Exact command | Result | Limitation |
| --- | --- | --- | --- |
| Lock and environment | `uv lock --check`; `uv sync --frozen --group dev` | Passed; 116 packages resolved and 74 checked | No clean Windows sync has been recorded. |
| Complete portable suite | `uv run pytest -q -ra` | 215 passed, 9 skipped | One smoke test requires explicit disposable-DWG authorization; eight lease tests require Windows APIs/sessions. |
| Metadata, package, catalog, and stdio | `uv run pytest tests/unit/test_project_metadata.py tests/unit/test_package_entrypoints.py tests/compatibility/test_legacy_mutating_tool_schemas.py tests/contract/test_stdio_server.py -q` | 11 passed | Uses unavailable/injected services, never real AutoCAD. |
| Active lint | `uv run ruff check src/autocad_mcp src/server.py tests/adapter tests/compatibility tests/contract tests/mcp tests/unit/test_mcp_models.py tests/unit/test_mcp_tools.py tests/unit/test_mcp_dispatch.py tests/windows tests/conftest.py scripts` | Passed | Full-tree legacy Ruff is intentionally not represented as passing; historical paths retain pre-existing diagnostics. |
| Active source typing | `uv run mypy -p autocad_mcp -m src.server` | Passed: 16 source files, no issues | Windows COM remains dynamically exercised only on Windows. |
| Syntax, manifest, and import boundary | `uv run python -m compileall -q src tests`; `uv run python -m json.tool mcp.json`; `uv run python -c "import autocad_mcp.server, autocad_mcp.adapter.windows_session, autocad_mcp.adapter.windows, src.server, sys; assert not {'pythoncom', 'win32com', 'win32com.client', 'pyautocad'} & set(sys.modules)"`; `git diff --check` | Passed | Import-boundary evidence is Linux-only. |

`poetry.lock` remains archival and inactive until the first clean Windows
frozen-sync witness permits its evidence-gated removal. `Dockerfile` and
`docker-compose.yml` remain unsupported historical artifacts because decision
0001 requires explicit E01-G3 maintainer approval before their removal. Neither
retention is a supported runtime instruction.

The prepared PowerShell runner and AutoCAD 2026 smoke have not run on Windows.
Do not create `docs/verification/autocad-2026-smoke.md`, promote any AutoCAD
release, or describe the smoke as verified until an operator supplies the
redacted real-device evidence.

## 2026-10-01 dependency follow-up

Clean hosted Windows and Linux frozen-install and automated-test evidence is now
recorded in [the dependency baseline report](dependency-baseline-2026-10-01.md).
That witness and the maintainer's remaining-work authorization permit retirement
of the inactive Poetry lock and unsupported root container artifacts. The
August retention statements above describe that earlier checkpoint. Actual
AutoCAD execution remains pending; the prepared smoke is not promoted by CI.
