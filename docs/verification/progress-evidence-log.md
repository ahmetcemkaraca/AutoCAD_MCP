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
