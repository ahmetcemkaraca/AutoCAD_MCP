# Contributor and Agent Rules

## Scope and authority

This file applies to the entire repository. A more deeply nested `AGENTS.md` may add local constraints but MUST NOT weaken the safety, language, or verification rules in this file.

Direct user instructions take precedence. When a request conflicts with repository safety or would risk drawing data, stop and ask for explicit direction.

## Language

- Code, identifiers, comments, docstrings, commit messages, pull-request titles and bodies, issue text, and project documentation MUST be written in English.
- User-facing localization MAY be added as data or translated documentation when explicitly requested, but English remains the canonical project language.
- Existing historical content under `docs/legacy/` MUST NOT be used as a language or style precedent.

## Git workflow

- Routine development MUST use a focused feature or fix branch and a pull request.
- Agents and contributors MUST NOT commit routine development work directly to `main`.
- Commits MUST be small, coherent, and use imperative English messages such as `feat: add entity snapshot model`.
- Unrelated user changes MUST be preserved. Do not rewrite, discard, or reformat unrelated files.
- Force-pushing a shared branch MUST NOT occur without explicit maintainer authorization.
- The protected `archive` branch MUST remain unchanged; it preserves the adopted repository history.

## Engineering approach

- Read the affected call path, tests, and current documentation before editing.
- Prefer the smallest complete solution. Reuse the standard library, platform features, and existing dependencies before adding a dependency.
- New abstractions MUST have at least two concrete consumers or a demonstrated isolation need, such as the real COM adapter and a focused fake backend.
- Runtime source code MUST NOT be changed in a documentation-only pull request.
- Behavior changes MUST begin with a failing automated test and end with focused and regression verification.

## Platform boundary

- Product runtime support targets full AutoCAD 2021-2026 on Windows.
- AutoCAD LT and AutoCAD hosted on Linux or macOS are out of scope unless this policy is explicitly revised.
- AutoCAD-independent modules MUST remain importable and testable without Windows COM.
- Imports of `pythoncom`, `win32com`, and AutoCAD COM wrappers MUST remain behind the Windows adapter boundary.
- Linux MAY be used for pure Python unit tests and MCP contract tests only. Passing Linux tests MUST NOT be reported as proof of AutoCAD compatibility.
- AutoCAD version differences SHOULD be handled through detected capabilities instead of speculative version branches.

## AutoCAD and drawing safety

- Tests and manual checks MUST use disposable drawing copies unless the user explicitly provides another safe target.
- Destructive drawing changes MUST require a preview, explicit approval, stale-state validation, and AutoCAD Undo protection.
- An edit plan MUST identify its source snapshot and expected entity state before mutation.
- Entity handles SHOULD be used for persistent drawing identity; `ObjectID` MUST be treated as session-local.
- Drawing capture MUST be an explicitly invoked operation. It MUST NOT run automatically on every request, connection, analysis, or edit.
- Arbitrary Python, AutoLISP, VBA, shell commands, or unrestricted AutoCAD `SendCommand` execution MUST NOT be exposed through MCP.
- Credentials, tokens, personal paths, and proprietary drawing content MUST NOT be committed or logged.

## Testing and verification

- Run the narrowest relevant test first, then the broader affected suite.
- Pure Python syntax can be checked with `python -m compileall -q src tests`.
- Real AutoCAD behavior MUST be verified on Windows with full AutoCAD and the tested release MUST be recorded.
- AutoCAD 2021-2025 MUST remain labeled `targeted` until each release is tested in a real installation.
- AutoCAD 2026 MUST NOT be labeled `verified` until the documented smoke and integration checks pass.
- A passing syntax check, mock test, or Linux test MUST NOT be described as a passing AutoCAD integration test.
- Completion claims MUST include fresh command output or other reproducible evidence.

## MCP boundaries

- `src/server.py` is the adopted stdio entry point until a later pull request explicitly migrates it.
- New MCP tools MUST use constrained, documented schemas and structured errors.
- Tool metadata, `mcp.json`, implementation registrations, tests, and user documentation MUST agree.
- Logging MUST NOT write normal messages to MCP stdio output; use standard error or structured tool results.
- Vision inference belongs to the MCP client or model. The server MUST NOT require a specific vision provider or API key.

## Documentation

- Canonical documentation starts at `docs/README.md`.
- Documentation MUST distinguish observed source code, automated verification, real-AutoCAD verification, target design, and historical research.
- Unverified functionality MUST NOT be described as working, complete, production-ready, secure, compliant, or enterprise-ready.
- Version support claims MUST match `docs/compatibility.md`.
- Roadmap items MUST have observable acceptance criteria and MUST NOT be marked complete from code presence alone.
- New documentation MUST use relative links for repository files and current repository URLs for external GitHub links.

## Legacy code and documents

- `docs/legacy/` is historical evidence, not current guidance.
- Legacy code or documentation MUST NOT be removed without a tested replacement or a documented removal justification.
- A legacy idea MAY return to the active project only after it is reconciled with the current architecture, covered by focused tests, and labeled according to its actual verification level.

## Pull-request handoff

Every pull request MUST state:

- the user-visible or maintainer-visible outcome;
- the files and boundaries changed;
- the exact verification commands and results;
- the AutoCAD release used for any real integration test;
- known limitations, deferred work, and documentation impact.
