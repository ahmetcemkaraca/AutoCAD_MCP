# EPIC-01: Reproducible Windows Development Baseline

## Status

Proposed. This epic is an implementation plan, not evidence that any described command currently passes.

**Dependency position:** first foundation epic. [EPIC-02](EPIC-02-canonical-mcp-core.md) and [EPIC-03](EPIC-03-windows-autocad-adapter-and-contract-tests.md) may design against the accepted lock after E01-G2, but implementation starts only after E01-G4 closes this temporary baseline. Roadmap Stage 2, Stable MCP core, remains open until all three foundation epics pass their completion gates.

**Required execution mode:** work on a focused feature branch and pull request. Future agentic workers should execute one work package at a time with tests first and a reviewer checkpoint at each named gate. No runtime behavior should be redesigned in this epic.

## Outcome

A new Windows developer can clone the repository, install one documented Python version and `uv`, reproduce the same dependency graph from `uv.lock`, and invoke the temporarily adopted server module with:

```powershell
uv sync --frozen --group dev
uv run python -m src.server
```

The project uses PEP 621 metadata as the dependency source of truth. Windows COM packages are absent from Linux resolution and installed on Windows through explicit environment markers. Active metadata agrees on project version `0.1.0`, the targeted product range is full AutoCAD 2021-2026 on Windows, and the temporary adopted module entry point is `python -m src.server` everywhere.

This epic deliberately leaves `uv` in non-package mode to make the dependency migration mechanical. EPIC-02 owns the separately reviewed package-installation change: it creates `src/autocad_mcp/`, changes the canonical command to `python -m autocad_mcp.server`, and retains `src/server.py` as a tested compatibility shim until a later evidence-gated retirement.

The root Docker artifacts are either retained with a proved, supported purpose or removed only after a written disposition records why they cannot represent the Windows/AutoCAD product runtime. The evidence currently points to removal, but deletion is reviewer-gated and is not authorized merely by this plan.

## Evidence / problem

The following observations are from the repository at the 2026-08-25 stewardship baseline and must be rechecked when implementation begins:

- `pyproject.toml` mixes a `[project]` table with Poetry-only dependency tables and a Poetry build backend. `mcp.json` currently names an unfrozen `uv` install workflow, but there is no `uv.lock`.
- `poetry.lock` records `mcp` 1.12.2, `pyautocad` 0.2.0, the obsolete `pypiwin32` 223 shim, and transitive `pywin32` 311. The manifest gives none of the COM dependencies a Windows marker.
- `src/utils.py` imports `pythoncom`, `win32com.client`, and `pyautocad` at module import time. This epic makes dependency installation platform-correct; EPIC-03 moves those imports behind the adapter boundary.
- `mcp.json` runs `uv run python src/server.py` and injects `PYTHONPATH=src`. Module execution is the stable target because it gives Python one unambiguous package context.
- Active version strings disagree: `pyproject.toml` and `mcp.json` say `0.1.0`, while `src/server.py` initializes the MCP server as `1.0.0`. Several experimental subpackages also contain their own `1.0.0` strings; those are not active product metadata and are not silently rewritten here.
- `pyproject.toml` describes only AutoCAD 2025 even though the approved target is full AutoCAD 2021-2026 on Windows.
- `Dockerfile` is a Linux image that copies absent `requirements.txt` and `requirements-prod.txt`, advertises version `1.0.0`, starts the unselected enhanced server, and probes an undocumented HTTP `/health` endpoint.
- `docker-compose.yml` references absent `init.sql`, `nginx.conf`, and `ssl/` inputs and adds Redis/PostgreSQL/nginx services not used by the adopted stdio server. A Linux container cannot provide the Windows COM boundary required for the product runtime.
- The only recorded verification is `python3 -m compileall -q src tests` on Linux with Python 3.14.4. It does not establish dependency installation, Windows compatibility, MCP startup, or AutoCAD operation.

The evidence labels in [project status](../project-status.md), [testing](../testing.md), and [compatibility](../compatibility.md) remain authoritative until fresh results replace them.

## Scope

- Convert dependency declarations to PEP 621 `[project.dependencies]`, PEP 621 optional dependencies, and the standardized `[dependency-groups]` development group supported by `uv`.
- Preserve the currently declared runtime and optional feature dependency set during the mechanical migration, except replace `pypiwin32` with `pywin32` and apply Windows markers to COM-only packages.
- Generate and commit `uv.lock`; delete `poetry.lock` only in the same reviewed change that proves the frozen `uv` workflow.
- Make `uv sync --frozen --group dev` the canonical development install command.
- Standardize active version metadata at `0.1.0` and active product wording at full AutoCAD 2021-2026 on Windows, with the compatibility status still “targeted, not verified.”
- Change all active launch documentation and `mcp.json` to `uv run python -m src.server`; remove the `PYTHONPATH` workaround from `mcp.json`.
- Add automated metadata and platform-marker checks.
- Create a written Docker disposition before deleting or retaining `Dockerfile` and `docker-compose.yml`.
- Update canonical developer documentation only after the relevant commands have been run on the named platform.

## Out of scope

- Moving COM imports or implementing an AutoCAD adapter; that belongs to EPIC-03.
- Consolidating MCP registrations, changing schemas, changing result shapes, or removing duplicate server code; that belongs to EPIC-02.
- Claiming any AutoCAD release as verified.
- Upgrading dependency major versions beyond the ranges already implied by the Poetry manifest.
- Pruning packages used only by experimental modules. A later dependency audit may do so after imports, tests, and feature classification provide evidence.
- Packaging the repository as an installable distribution or adding a console-script entry point. For this epic only, `[tool.uv] package = false` and `python -m src.server` are the controlled intermediate state. EPIC-02 enables installation of the `autocad_mcp` package and migrates the canonical module command.
- Creating a Linux AutoCAD runtime or a container-to-Windows COM bridge.
- Editing experimental subpackage `__version__` values that do not feed active project or server metadata.

## Prerequisites

1. The stewardship baseline and its canonical documentation are merged or present in the execution branch.
2. A clean focused feature branch is created from the current `main`; unrelated worktree changes are preserved.
3. `uv` is installed on one Linux environment and one Windows environment.
4. The Windows baseline uses 64-bit CPython 3.12 and Windows PowerShell. Other Python versions remain governed by `requires-python`, but CPython 3.12 is the reproducibility witness for this epic.
5. No AutoCAD installation is required for dependency resolution or metadata tests. A real AutoCAD test is deliberately deferred to EPIC-03.
6. Before dependency ranges are edited, save the current direct-dependency and locked-version inventory in the pull-request evidence.
7. Before Docker files are deleted, E01-WP4 must be complete and reviewer gate E01-G3 must explicitly approve the recorded disposition.

## Owned files and paths

| Path | Planned action | Responsibility |
| --- | --- | --- |
| `pyproject.toml` | Modify | PEP 621 dependency source, dependency groups, build/package mode, Python requirement, active metadata |
| `uv.lock` | Create | Cross-platform resolved dependency lock generated by `uv lock` |
| `poetry.lock` | Delete after E01-G2 | Retire the superseded lock only after frozen `uv` verification |
| `src/__init__.py` | Modify | Active `__version__: Final[str] = "0.1.0"` constant |
| `src/server.py` | Modify narrowly | Read active server version from `src.__version__`; no registration or behavior refactor |
| `mcp.json` | Modify | Module invocation, version, description, installation text, and removal of `PYTHONPATH` |
| `tests/unit/test_project_metadata.py` | Create | Version, command, dependency-marker, and manifest agreement tests |
| `docs/decisions/0001-container-artifact-disposition.md` | Create | Reproducible evidence and retain/remove decision for root container artifacts |
| `Dockerfile` | Delete only after E01-G3 | Remove misleading Linux product image if the evidence-backed removal decision is approved |
| `docker-compose.yml` | Delete only after E01-G3 | Remove unsupported service topology if the evidence-backed removal decision is approved |
| `README.md` | Modify | Canonical `uv` install and module launch commands; targeted compatibility wording |
| `docs/testing.md` | Modify after verification | Replace intended workflow language with exact fresh baseline results |
| `docs/project-status.md` | Modify after verification | Record dependency and entry-point evidence without implying MCP/AutoCAD verification |
| `docs/compatibility.md` | Modify only if needed | Record the tested Windows/Python development baseline without promoting AutoCAD releases |

No other source, configuration, lock, or documentation path is owned by this epic. If implementation discovers another required path, stop at a reviewer gate and revise the epic before editing it.

## Interfaces produced and consumed

### Produced active version interface

`src/__init__.py` produces one runtime constant:

```python
from typing import Final

__version__: Final[str] = "0.1.0"
```

`src.server.main()` consumes `src.__version__` for `InitializationOptions.server_version`. `tests/unit/test_project_metadata.py` consumes the same value and compares it with `project.version` in `pyproject.toml` and top-level `version` in `mcp.json`.

The repeated serialized values are intentional because neither TOML nor JSON can import a Python constant. The test is the enforcement mechanism.

### Produced dependency interface

The target PEP 621 structure is:

```toml
[project]
name = "autocad-mcp"
version = "0.1.0"
description = "An experimental Model Context Protocol bridge for full AutoCAD 2021-2026 on Windows"
requires-python = ">=3.12"
dependencies = [
  "flask>=3.0.3,<4",
  "pyautocad>=0.2.0,<0.3; sys_platform == 'win32'",
  "numpy>=2.1.0,<3",
  "scipy>=1.14.1,<2",
  "pywin32>=311; sys_platform == 'win32'",
  "fastapi>=0.116.1,<0.117",
  "uvicorn[standard]>=0.35.0,<0.36",
  "python-multipart>=0.0.20,<0.0.21",
  "mcp>=1,<2",
  "websockets>=12.0,<13",
  "aiofiles>=23.2.0,<24",
  "jinja2>=3.1.2,<4",
  "requests>=2.31.0,<3",
  "python-dotenv>=1.0.0,<2",
  "cryptography>=41.0.0,<42",
]

[project.optional-dependencies]
ml = [
  "scikit-learn>=1.4.0,<2",
  "transformers>=4.35.0,<5",
  "torch>=2.1.0,<3",
  "accelerate>=0.24,<0.25",
]

[dependency-groups]
dev = [
  "pytest>=8.3.2,<9",
  "pytest-cov>=4,<5",
  "pytest-html>=4.0.0,<5",
  "pytest-mock>=3.12.0,<4",
  "black>=24.8,<25",
  "ruff>=0.5.5,<0.6",
  "mypy>=1.0,<2",
  "bandit>=1.7,<2",
  "safety>=2,<3",
  "packaging>=24,<26",
]
```

Every range above is the PEP 508 equivalent of the declared Poetry constraint, not the version happened to be selected by `poetry.lock`. In particular, `mcp = "^1.0.0"` becomes `mcp>=1,<2`, `pytest-cov = "^4.0"` becomes `pytest-cov>=4,<5`, `black = "^24.8.0"` becomes `black>=24.8,<25`, `safety = "^2.0"` becomes `safety>=2,<3`, `ruff = "^0.5.5"` becomes `ruff>=0.5.5,<0.6`, and the zero-major `accelerate = "^0.24.0"` becomes `accelerate>=0.24,<0.25`. The only requirement changes beyond syntax translation are the classified `pypiwin32` replacement and direct `packaging` addition.

`packaging>=24,<26` is a direct development dependency because `tests/unit/test_project_metadata.py` uses `packaging.requirements.Requirement` to validate PEP 508 names and normalized markers. Depending on its incidental presence through `uv` or another tool would make that test’s dependency implicit and unstable.

The implementer must express the existing author, readme, license, keywords, and classifiers in valid PEP 621 form, remove all `[tool.poetry*]` tables, and choose a non-packaging `uv` configuration because this epic does not publish a wheel:

```toml
[tool.uv]
package = false
```

The existing tool settings for pytest, Black, Ruff, mypy, and Bandit remain unless a frozen install or the tool itself proves a syntax incompatibility. Any tool-setting syntax correction belongs in the same test-first work package and must not change the lint policy silently.

### Produced launch contract

The active command representation at the end of this epic is:

```json
{
  "command": "uv",
  "args": ["run", "python", "-m", "src.server"]
}
```

No `PYTHONPATH` value is needed when the command runs from the repository root. EPIC-02 consumes this as a compatibility baseline, enables package installation, changes `mcp.json` to `uv run python -m autocad_mcp.server`, and proves that the old `uv run python -m src.server` path delegates through a protocol-safe shim.

### Consumed policy interfaces

- Python floor and compatibility labels from [compatibility](../compatibility.md).
- Intended `uv` commands and evidence labels from [testing](../testing.md).
- Adopted entry point and logging boundary from [architecture](../architecture.md).
- No-AutoCAD-on-Linux boundary and English/documentation rules from `AGENTS.md`.

## Work packages

### E01-WP1: Freeze the dependency and metadata inventory

**Sequence:** 1. **Reviewer gate:** E01-G1.

**Files:** no repository mutation; attach output to the pull request before editing manifests.

**Tests-first steps:** in this package, “test first” means establish assertions against the pre-change state before changing the source of truth.

1. Run the inventory commands from the repository root:

   ```powershell
   uv --version
   py -3.12 --version
   Select-String -Path pyproject.toml -Pattern '^\[project\]','^\[tool\.poetry','^[A-Za-z0-9_-]+\s*='
   Select-String -Path poetry.lock -Pattern '^name = "mcp"','^name = "pyautocad"','^name = "pypiwin32"','^name = "pywin32"'
   git status --short
   ```

2. Record OS edition, architecture, Python output, `uv` output, the direct dependency table, and the four relevant locked package versions in the pull request.
3. Compare every current direct runtime, optional ML, and development dependency against the target interface above. Differences require an explicit one-line classification: preserved, PEP-508 syntax-translated, replaced (`pypiwin32` to `pywin32`), added for an owned test (`packaging`), or intentionally unchanged pending later audit.
4. E01-G1 passes when a reviewer confirms all bounds are equivalent to the Poetry constraints and the only classified non-mechanical changes are the COM-shim replacement, Windows markers, and direct `packaging` test dependency.

### E01-WP2: Write failing metadata and marker tests

**Sequence:** 2. **Depends on:** E01-G1. **Reviewer gate:** none; carry failures into E01-WP3.

**Files:** create `tests/unit/test_project_metadata.py` only.

1. Write tests using `json`, `tomllib`, `importlib.util`, `pathlib`, `packaging.requirements.Requirement`, and `src.__version__`. The required assertions are:

   ```python
   assert pyproject["project"]["version"] == manifest["version"] == __version__ == "0.1.0"
   assert manifest["mcpServers"]["autocad-mcp"]["args"] == [
       "run", "python", "-m", "src.server"
   ]
   assert "PYTHONPATH" not in manifest["mcpServers"]["autocad-mcp"].get("env", {})
   assert "tool" not in pyproject or "poetry" not in pyproject["tool"]
   assert "pypiwin32" not in "\n".join(pyproject["project"]["dependencies"]).lower()
   ```

2. Parse requirement strings with the directly declared `packaging.requirements.Requirement`. Assert both `pyautocad` and `pywin32` have the exact marker text `sys_platform == "win32"` after marker normalization.
3. Add a platform-specific assertion: on non-Windows, `importlib.util.find_spec("pythoncom") is None` after a clean sync; on Windows, it is not `None`.
4. Run the focused test before manifest changes:

   ```powershell
   python -m pytest tests/unit/test_project_metadata.py -q
   ```

   Expected result: failure because the module command, Poetry tables, active version constant, and markers do not yet satisfy the contract. If test collection cannot start because current dependencies are absent, record that as the expected red state and proceed to E01-WP3.

### E01-WP3: Migrate to PEP 621 and generate `uv.lock`

**Sequence:** 3. **Depends on:** E01-WP2 red evidence. **Reviewer gate:** E01-G2.

**Files:** `pyproject.toml`, `uv.lock`, `poetry.lock`, `src/__init__.py`, `src/server.py`, `mcp.json`.

1. Replace Poetry dependency tables with the exact PEP 621, optional dependency, dependency-group, and `[tool.uv] package = false` interfaces above.
2. Replace `pypiwin32` with direct `pywin32>=311; sys_platform == 'win32'`. Keep `pyautocad` Windows-only. Do not add markers to pure Python packages merely to make Linux resolution smaller.
3. Add `src.__version__` and make only the `InitializationOptions(server_version=...)` value in `src/server.py` consume it. Do not refactor handlers in this package.
4. Change `mcp.json` to the exact module launch contract, remove its `PYTHONPATH` environment entry, align description/version/install text to `uv sync --frozen --group dev`, and mechanically retain the observed seven-tool catalog only for this dependency-baseline epic. Record that EPIC-02 must unregister the four mutating tools and preserve their schemas only as compatibility evidence.
5. Generate the lock and validate it:

   ```powershell
   uv lock
   uv lock --check
   uv sync --frozen --group dev
   uv run pytest tests/unit/test_project_metadata.py -q
   uv run python -m compileall -q src tests
   ```

6. On Linux, create a clean environment and prove COM packages were skipped:

   ```bash
   rm -rf .venv
   uv sync --frozen --group dev
   uv run python -c "import importlib.util; assert importlib.util.find_spec('pythoncom') is None; assert importlib.util.find_spec('win32com') is None"
   uv run pytest tests/unit/test_project_metadata.py -q
   ```

   The `.venv` removal is limited to the repository-local generated environment and must not be used if it contains user-managed work.

7. On Windows, create a clean environment and prove COM packages were installed:

   ```powershell
   if (Test-Path .venv) { Remove-Item -Recurse -Force .venv }
   uv sync --frozen --group dev
   uv run python -c "import importlib.util; assert importlib.util.find_spec('pythoncom') is not None; assert importlib.util.find_spec('win32com') is not None; assert importlib.util.find_spec('pyautocad') is not None"
   uv run pytest tests/unit/test_project_metadata.py -q
   uv run python -m compileall -q src tests
   ```

   Removal is restricted to the repository-local `.venv` after confirming its resolved path is below the checkout.

8. Delete `poetry.lock` only after both `uv lock --check` and the Windows frozen sync pass. E01-G2 passes when the reviewer sees the generated `uv.lock`, Linux marker evidence, Windows marker evidence, and a dependency diff with no unexplained direct-dependency loss.

### E01-WP4: Classify the root Docker artifacts before disposition

**Sequence:** 4. **May run in parallel with:** E01-WP2 and E01-WP3. **Reviewer gate:** E01-G3 before any deletion.

**Files:** create `docs/decisions/0001-container-artifact-disposition.md`; do not edit or delete Docker files until the gate.

1. Write the assessment with these fixed headings: Context, Product runtime boundary, Reproducible observations, Options considered, Decision, Consequences, and Reintroduction criteria.
2. Run and copy exact output or exit status for:

   ```powershell
   @('requirements.txt','requirements-prod.txt','init.sql','nginx.conf','ssl') | ForEach-Object { "$_=$(Test-Path $_)" }
   docker compose -f docker-compose.yml config
   Select-String -Path Dockerfile -Pattern 'FROM ','COPY requirements','HEALTHCHECK','enhanced_mcp_server','LABEL version'
   Select-String -Path docker-compose.yml -Pattern 'redis','postgres','nginx','init.sql','/health'
   ```

   If Docker is not installed, record that fact; static missing-input and platform-boundary evidence is still valid. Do not describe an unrun image build as failed.
3. Evaluate exactly three options:

   - retain as a supported product deployment, which requires a feasible Windows COM path and tests;
   - retain under a clearly experimental archive, which requires a named current consumer;
   - remove the two root artifacts because they are incomplete, select the wrong server, and cannot host the supported runtime.

4. The recommended decision is removal. E01-G3 passes only when a maintainer approves the written decision and agrees that Git history is sufficient recovery.
5. After approval, delete `Dockerfile` and `docker-compose.yml` in one focused change and run:

   ```powershell
   git diff --name-status -- Dockerfile docker-compose.yml docs/decisions/0001-container-artifact-disposition.md
   git grep -n -E 'docker compose|docker-compose|Dockerfile' -- README.md docs pyproject.toml mcp.json
   ```

6. Update any active documentation hit to state the approved disposition. Historical hits below `docs/legacy/` remain unchanged.

### E01-WP5: Update canonical developer instructions with fresh evidence

**Sequence:** 5. **Depends on:** E01-G2 and E01-G3. **Reviewer gate:** E01-G4.

**Files:** `README.md`, `docs/testing.md`, `docs/project-status.md`, and only if necessary `docs/compatibility.md`.

1. Replace Poetry or script-path install/start instructions in active docs with:

   ```powershell
   uv sync --frozen --group dev
   uv run python -m src.server
   ```

2. In `docs/testing.md`, record Windows edition, CPython 3.12 patch version, `uv` version, `uv.lock` Git blob ID, exact frozen-sync command, and result. Label this “dependency baseline verified”; do not label MCP or AutoCAD verified.
3. In `docs/project-status.md`, record PEP 621 migration, lock presence, marker checks, and module-command agreement as observed/automated evidence.
4. Keep every AutoCAD 2021-2026 row targeted. The Windows dependency sync does not promote an AutoCAD release.
5. Run the final epic suite on both platforms:

   ```powershell
   uv lock --check
   uv sync --frozen --group dev
   uv run pytest tests/unit/test_project_metadata.py -q
   uv run ruff check src tests
   uv run python -m compileall -q src tests
   python -m json.tool mcp.json > $null
   git diff --check
   ```

   Linux equivalent for the JSON check is `python3 -m json.tool mcp.json >/dev/null`.
6. E01-G4 passes when the reviewer can reproduce the Windows sync from `uv.lock`, the metadata test passes, no docs overclaim runtime evidence, and the Docker decision is linked from active documentation.

## Parallel subagent lanes

Parallel execution is optional. If used, each lane gets a separate worktree or branch and must not edit another lane’s files.

| Lane | Work packages | Exclusive file ownership | Start condition | Merge order |
| --- | --- | --- | --- | --- |
| E01-A: dependency baseline | E01-WP1, E01-WP3 dependency portion | `pyproject.toml`, `uv.lock`, `poetry.lock` | Immediate | First, after E01-G2 |
| E01-B: metadata and launch | E01-WP2, E01-WP3 metadata portion | `src/__init__.py`, `src/server.py`, `mcp.json`, `tests/unit/test_project_metadata.py` | E01-G1 | Second; re-run tests on Lane A result |
| E01-C: container disposition | E01-WP4 | `docs/decisions/0001-container-artifact-disposition.md`, `Dockerfile`, `docker-compose.yml` | Immediate; deletion waits for E01-G3 | Third |
| E01-D: evidence documentation | E01-WP5 | `README.md`, `docs/testing.md`, `docs/project-status.md`, `docs/compatibility.md` | E01-G2 and E01-G3 | Last |

Lane A owns all `pyproject.toml` conflict resolution. Lane B communicates required test dependencies as a message and does not edit the manifest. Lane D consumes final command output and does not “anticipate” results. The integrating agent reruns the full E01-WP5 commands after all lanes merge.

## Windows / AutoCAD test matrix

| Environment | Dependency action | Expected COM package state | Tests in this epic | AutoCAD evidence label |
| --- | --- | --- | --- | --- |
| Windows 11, 64-bit CPython 3.12, no AutoCAD required | `uv sync --frozen --group dev` | `pythoncom`, `win32com`, and `pyautocad` import specs present | Lock, metadata, marker, JSON, lint, compile | No AutoCAD claim |
| Linux, 64-bit CPython 3.12 | `uv sync --frozen --group dev` | COM import specs absent | Lock, metadata, marker, JSON, lint, compile | Linux is pure-Python test host only |
| Full AutoCAD 2026 on Windows | No application launch in this epic | Packages installed but unused | None against AutoCAD | Targeted; first validation environment |
| Full AutoCAD 2021-2025 on Windows | No application launch in this epic | Not exercised | None against AutoCAD | Targeted, not verified |
| AutoCAD LT, Linux-hosted AutoCAD, macOS | No product install | Not applicable | None | Out of scope |

The frozen dependency result is necessary input to EPIC-03 but is not proof that COM calls or AutoCAD operations work.

## Acceptance criteria

- `pyproject.toml` contains PEP 621 dependencies and no Poetry dependency or build tables.
- `uv.lock` exists, `uv lock --check` passes, and `poetry.lock` is absent only after E01-G2.
- A clean Windows CPython 3.12 environment completes `uv sync --frozen --group dev`.
- A clean Linux CPython 3.12 environment completes the same sync without installing `pythoncom`, `win32com`, or `pyautocad`.
- `pywin32`, not `pypiwin32`, supplies Windows COM support and has an explicit `sys_platform == 'win32'` marker.
- `pyautocad` has the same Windows-only marker.
- `pyproject.toml`, `mcp.json`, `src.__version__`, and MCP initialization agree on version `0.1.0`.
- At this epic’s completion boundary, `mcp.json` and active documentation use `uv run python -m src.server` and do not inject `PYTHONPATH`; EPIC-02 is explicitly authorized to migrate the canonical command after package-installation tests pass.
- Active descriptions say the product targets full AutoCAD 2021-2026 on Windows without claiming those releases are verified.
- The direct dependency inventory has no unexplained loss relative to the pre-change Poetry manifest.
- Dependency ranges are PEP 508 equivalents of the Poetry declarations rather than lock-selected lower bounds, and `packaging>=24,<26` is a classified direct development dependency for metadata tests.
- The seven-tool catalog at this temporary boundary is explicitly marked for EPIC-02 safety reduction; this epic does not endorse the four mutating registrations as canonical behavior.
- The Docker disposition contains reproducible evidence before `Dockerfile` or `docker-compose.yml` is removed.
- All E01-WP5 verification commands pass with fresh output, and canonical docs report only the evidence actually obtained.
- E01-G1 through E01-G4 are recorded as approved in the pull request.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| A Poetry-to-PEP-621 translation silently changes an allowed version range | Compare every direct requirement, retain equivalent lower/upper bounds, and require E01-G1 inventory review. |
| Universal locking resolves a package on Linux that cannot install on Windows | Generate one lock, then perform a clean frozen sync on both platforms before deleting `poetry.lock`. |
| `pypiwin32` removal changes transitive behavior | Replace it explicitly with the already locked underlying package `pywin32>=311` and prove imports on Windows. |
| Python `>=3.12` resolves future versions not usable by COM wheels | Use CPython 3.12 as the reproducibility witness; narrow the declared range only in a later evidence-backed compatibility change. |
| Keeping the entire historical dependency set preserves bloat | This epic prioritizes a behavior-neutral migration. A later audit may remove packages only after feature ownership and import tests exist. |
| Non-packaging `uv` mode makes installed metadata unavailable | Use `src.__version__` and an agreement test; do not depend on `importlib.metadata.version()` until the project intentionally becomes a package. |
| Deleting Docker artifacts removes a future deployment option | Require a decision record and reviewer approval; Git history provides recovery, and reintroduction criteria require an actual supported boundary and tests. |
| Documentation is updated before commands pass | Lane D starts only after E01-G2/E01-G3 and copies fresh results rather than expected outcomes. |

## Rollback

Rollback is a normal Git revert of the epic’s focused commits; do not use destructive worktree resets.

1. Revert documentation evidence before reverting the configuration it describes.
2. Restore `Dockerfile` and `docker-compose.yml` from the parent commit if their approved removal causes an unforeseen documented consumer failure. Keep the decision record and amend it with the rollback evidence.
3. Restore `poetry.lock` and the prior Poetry tables together if frozen `uv` installation cannot be repaired within the epic. Do not leave two competing lock files as an ambiguous steady state.
4. Restore the prior `mcp.json` command only together with its documentation. Version strings must remain mutually consistent at every rollback point.
5. Run `python3 -m json.tool mcp.json`, `python3 -m compileall -q src tests`, and `git diff --check` after rollback.

Rollback does not authorize marking an unverified AutoCAD release as verified or reintroducing a container as a supported runtime without new evidence.

## Completion evidence

The pull request must contain or link all of the following:

- Pre-change direct dependency and selected lock-version inventory.
- `uv --version`, Windows edition, architecture, and CPython 3.12 patch version.
- `uv lock --check` output and the `uv.lock` Git blob ID.
- Clean `uv sync --frozen --group dev` output from Windows and Linux.
- Windows import-spec result showing COM packages present and Linux result showing them absent.
- Focused metadata test, Ruff, compileall, JSON validation, and whitespace-check outputs.
- `git diff --name-status` showing `uv.lock` creation and the gated disposition of `poetry.lock`, `Dockerfile`, and `docker-compose.yml`.
- The approved container disposition record with command results, not inferred build claims.
- Reviewer approvals for E01-G1, E01-G2, E01-G3, and E01-G4.
- Canonical documentation changes that use precise labels: dependency baseline verified, syntax checked, and no AutoCAD verification performed.

## Handoff

After E01-G4, hand the following immutable inputs to EPIC-02 and EPIC-03 implementers:

- the accepted `uv.lock` blob ID;
- the supported baseline command `uv sync --frozen --group dev`;
- the module entry contract `uv run python -m src.server`;
- the temporary `[tool.uv] package = false` decision and the mandatory EPIC-02 package-migration gate;
- the mandatory EPIC-02 active-catalog reduction to `server_status`, `list_entities`, and `get_entity_info`, with all four legacy mutating schemas unregistered and retained only in compatibility evidence;
- active version `0.1.0` from `src.__version__`;
- the rule that COM packages are Windows-only and must not be imported by platform-independent modules;
- the exact Windows/Python environment used for the baseline;
- the Docker disposition and any reintroduction criteria.

EPIC-02 must then create the installable `autocad_mcp` package, move canonical registration to `autocad_mcp.server`, update `mcp.json`, and preserve `src.server` as a tested compatibility shim. EPIC-03 may build and verify the COM boundary only under that package. Neither downstream epic may reinterpret a successful dependency sync as MCP startup or AutoCAD compatibility evidence.
