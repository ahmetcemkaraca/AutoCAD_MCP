# Windows AutoCAD 2026 smoke guide

## Verification status

No real AutoCAD verification is recorded. This guide prepares the first
full-AutoCAD 2026 read-only smoke only; AutoCAD 2021-2026 remain targeted, not
verified until a successful Windows result is reviewed and recorded.

## What you must do manually

Use an interactive Windows desktop session with a licensed **full AutoCAD
2026** instance. Do not use AutoCAD LT, do not use a shared production drawing,
and do not run a second smoke controller. Start AutoCAD yourself, close every
modal dialog, and leave it running for the whole test. The runner only attaches
to the existing process; it never starts AutoCAD.

## Run the guarded smoke

1. Install Git, 64-bit CPython 3.12, and `uv`. Run this from a new PowerShell
   window:

   ```powershell
   winget install --exact --id Git.Git --source winget
   winget install --exact --id Python.Python.3.12 --source winget
   winget install --exact --id astral-sh.uv --source winget
   ```

   Close that PowerShell window, open a new one so the installers' `PATH`
   changes take effect, then clone and enter the exact review branch:

   ```powershell
   New-Item -ItemType Directory -Force C:\src | Out-Null
   git clone https://github.com/ahmetcemkaraca/AutoCAD_MCP.git C:\src\AutoCAD_MCP
   Set-Location C:\src\AutoCAD_MCP
   git fetch origin
   git switch --track -c codex/local-autocad-testable origin/codex/local-autocad-testable
   ```

   If your organization blocks `winget`, install those exact products through
   its approved installer channel, open a new PowerShell window, and continue
   at the verification commands below. If the checkout already exists, first
   run `Set-Location C:\src\AutoCAD_MCP`, then use `git switch
   codex/local-autocad-testable` followed by `git pull --ff-only origin
   codex/local-autocad-testable` instead of cloning/switching with `-c`.

2. Select 64-bit CPython 3.12 and verify `uv`. The runner repeats this check
   and fails closed if the synchronized interpreter is not exactly 64-bit
   CPython 3.12.

   ```powershell
   py -3.12 -c "import struct, sys; assert sys.version_info[:2] == (3, 12) and struct.calcsize('P') == 8; print(sys.version)"
   uv --version
   $env:UV_PYTHON = "3.12"
   uv sync --frozen --group dev
   ```

3. Pick a small `.dwg` fixture with at least one queryable entity. It must be
   outside `%TEMP%`, not be the drawing you normally edit, and be explicitly
   read-only. Record its hash before the run:

   ```powershell
   $source = "C:\autocad-mcp-fixtures\basic-smoke.dwg"
   attrib +R $source
   (Get-Item -LiteralPath $source).Attributes
   Get-FileHash -LiteralPath $source -Algorithm SHA256
   ```

4. Start full AutoCAD 2026 manually in the same Windows session, then run the
   only supported smoke command. Replace the example installation path with the
   `acad.exe` that belongs to the AutoCAD 2026 instance you started:

   ```powershell
   .\scripts\run_autocad_2026_smoke.ps1 -SourceDwg $source -AutoCADInstallationPath "C:\Program Files\Autodesk\AutoCAD 2026\acad.exe"
   ```

The runner accepts only those two absolute paths. It makes a GUID-scoped
disposable copy, acquires the exclusive lease, proves the source/copy hashes
match, binds the running AutoCAD window to the leased `acad.exe`, requires an
AutoCAD 2026 caption, and opens only the copy read-only. It runs the four
production adapter methods, then two fresh canonical stdio MCP processes. Each
process confirms the exact three-tool catalog and calls `server_status`,
`list_entities`, and `get_entity_info`. It checks the guarded full path,
read-only state, file metadata and hashes, `DBMOD`, entity count, and entity
digest before closing with `Close(False)`.

## Expected result and evidence

Success ends with one passing `test_autocad_2026_read_only_mcp_smoke` test.
The runner writes a local, ignored log under `logs/autocad-mcp-smoke-*.log`.
That local log intentionally contains the private source and installation paths
needed to diagnose the run; do not share it unchanged.

The console and log include these machine-readable records:

- `AUTOCAD_MCP_SMOKE_RUNNER_EVIDENCE=` — Windows build, interpreter/`uv`,
  checked-out branch/commit, clean tracked-worktree assertion, `uv.lock` Git
  blob/hash, installation identity, and source before/after metadata and hash.
- `AUTOCAD_MCP_SMOKE_LEASE_EVIDENCE=` — acquired and released lease lifecycle
  facts with the metadata path redacted to a digest.
- `AUTOCAD_MCP_SMOKE_EVIDENCE=` — a shareable report containing redacted
  source/copy path classifications, process identity, guard evidence, and
  post-open/pre-close drawing fingerprints plus post-close file metadata and
  hash.
- `AUTOCAD_MCP_SMOKE_PRESERVED_COPY=` — only on failure; this is the private
  local path to preserve for diagnosis.

A pass proves only the recorded AutoCAD 2026 fixture/run. It does not verify
AutoCAD 2021-2025, promote compatibility, or close Stage 2 by itself.

## Use the local server with Codex

After a successful smoke, register the local stdio server with Codex from a
PowerShell prompt. Replace the example checkout path exactly once if yours is
different:

```powershell
codex mcp add autocad-mcp -- uv --directory C:\src\AutoCAD_MCP run python -m autocad_mcp.server
codex mcp get autocad-mcp --json
```

The registered launch is equivalent to the canonical command
`uv run python -m autocad_mcp.server`, with `uv --directory` fixing the checked
out project as the working directory. Restart Codex after registration.

For manual post-smoke calls, first make a **new** disposable copy and open it
yourself as read-only in the already-running AutoCAD 2026 session. These manual
calls are not a substitute for the guarded smoke and must never target the
immutable source:

```powershell
$manualCopy = Join-Path $env:TEMP ("autocad-mcp-client-" + [guid]::NewGuid().ToString() + ".dwg")
Copy-Item -LiteralPath $source -Destination $manualCopy -ErrorAction Stop
attrib +R $manualCopy
Get-FileHash -LiteralPath $manualCopy -Algorithm SHA256
```

Use AutoCAD's file-open UI to open `$manualCopy` read-only, then ask Codex for
these exact calls in order:

1. `Call autocad-mcp server_status with {} and show the JSON result.`
2. `Call autocad-mcp list_entities with {} and show the first entity id.`
3. `Call autocad-mcp get_entity_info with {"entity_id": <the returned id>} and show the JSON result.`

Only `server_status`, `list_entities`, and `get_entity_info` are registered.
There is no mutation tool. Close the manual copy without saving when finished.

This release does not configure a hosted ChatGPT connector: it ships only a
local stdio server. Do not expose, tunnel, or publish this local smoke endpoint
to make a ChatGPT connector; a separately reviewed remote transport and its
authentication boundary are outside EPIC-01 through EPIC-03.

## Failure diagnostics and rollback

| Symptom | Safe response |
| --- | --- |
| `requires explicit disposable-DWG authorization` | Use the supplied PowerShell runner rather than calling the marked test directly. |
| Missing full AutoCAD / a modal dialog | Start full AutoCAD 2026 manually, clear dialogs, and rerun; do not start it from the runner. |
| `does not match the leased acad.exe` or `not AutoCAD 2026` | Stop. Supply the `acad.exe` for the already-running full 2026 process; do not relabel another release. |
| Source is not immutable | Stop and set its read-only attribute. Do not make the user drawing writable for the test. |
| Lease contention | Stop the second controller. Never delete lease files to bypass contention. |
| Changed fingerprint, active-path mismatch, or writable document | Stop. Keep the `AUTOCAD_MCP_SMOKE_PRESERVED_COPY` path and collect the evidence. |

For every failure, retain the original source and preserved copy, copy the
redacted `AUTOCAD_MCP_SMOKE_*_EVIDENCE` lines, and redact personal path
components and drawing content before sharing. Include AutoCAD product/caption,
version, `acad.exe` build, Windows build, CPython/`uv` versions, and the branch
commit. Do not write an AutoCAD verification record for a failed, skipped, or
unrecorded run.

To undo the local client trial, close the disposable drawing without saving,
then run:

```powershell
codex mcp remove autocad-mcp
git switch --detach origin/docs/stewardship-baseline
```

Do not delete a preserved evidence copy during rollback.
