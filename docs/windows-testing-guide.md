# Windows AutoCAD 2026 smoke guide

## Verification status

No real AutoCAD verification has been recorded yet. This procedure prepares
the first full AutoCAD 2026 read-only Stable-core smoke; it does not verify
AutoCAD 2021-2026 until a successful Windows run is recorded.

## Operator procedure

Complete the following actions manually in an interactive Windows session.

1. Fetch and check out the review branch:

   ```powershell
   git fetch origin
   git checkout codex/local-autocad-testable
   git pull --ff-only origin codex/local-autocad-testable
   ```

2. Install and select 64-bit CPython 3.12 and `uv` yourself. Confirm that the
   selected interpreter is 64-bit and that `uv --version` runs. From the
   repository root, create the frozen environment:

   ```powershell
   uv sync --frozen --group dev
   ```

3. Start licensed **full AutoCAD 2026** manually in the same interactive
   Windows session. Do not use AutoCAD LT. Close every modal dialog and do not
   start a second verification controller.

4. Choose a small, immutable, read-only `.dwg` with at least one queryable
   entity. Keep its source path outside the temporary guard location; the
   runner makes its own disposable copy and never opens the source. Record a
   SHA-256 for the source if your fixture process requires it.

5. Run the guarded smoke. Replace the two example paths with your source DWG
   and the actual full-AutoCAD `acad.exe` installation path:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/run_autocad_2026_smoke.ps1 -SourceDwg C:\autocad-mcp-fixtures\basic-smoke.dwg -AutoCADInstallationPath "C:\Program Files\Autodesk\AutoCAD 2026\acad.exe"
   ```

The runner requires a frozen sync, an explicitly read-only source, release
environment value `2026`, disposable-DWG authorization, and the controller's
exclusive AutoCAD lease. It attaches only to the AutoCAD process you already
started, opens only the generated copy read-only, and never saves or sends an
AutoCAD command.

## Expected successful result

Pytest reports one passing `test_autocad_2026_read_only_mcp_smoke` test. The
test initializes two fresh `python -m autocad_mcp.server` stdio processes. In
each process it confirms exactly these three tools, then queries status, lists
at least one entity, and reads the first entity's matching detail:

- `server_status`
- `list_entities`
- `get_entity_info`

The harness verifies the copy path, read-only state, source/copy hashes, file
metadata, `DBMOD`, entity count, and entity digest before and after the first
process and after the reconnect process. It closes the disposable document
with `Close(False)`. A genuine pass is still not a release claim until its
redacted evidence is reviewed and recorded.

## Configure an MCP client after the smoke

For Codex or ChatGPT MCP configuration, point the server entry at the checked
out repository and use this exact command:

```text
uv run python -m autocad_mcp.server
```

For a JSON-style configuration, use the equivalent command, arguments, and
working directory (replace the example directory):

```json
{
  "mcpServers": {
    "autocad-mcp": {
      "command": "uv",
      "args": ["run", "python", "-m", "autocad_mcp.server"],
      "cwd": "C:\\src\\AutoCAD_MCP"
    }
  }
}
```

The runner closes its guarded copy at the end. For manual client calls, first
make and open a separate disposable copy yourself as read-only in the already
running full AutoCAD 2026 session; never use the immutable source. Then call
only `server_status`, `list_entities`, and `get_entity_info`. The last call
needs the `entity_id` returned by `list_entities`. No mutation tool is
registered: editing remains outside this smoke, under EPIC-06, and extrusion
and revolution remain unregistered.

## Failure diagnostics and rollback

On a failure, stop the run, close any AutoCAD modal dialog, and keep the
original source untouched. The test asks the guard to preserve the disposable
copy on a smoke assertion failure; record its path from the failure output and
do not delete it. Collect the console output, lease acquire/release evidence,
AutoCAD product/build, Windows build, Python and `uv` versions, lock revision,
source hash, and fingerprint fields. Redact personal path components and
proprietary drawing content before sharing the report.

To roll back this local trial, remove the MCP client configuration and return
the checkout to the stewardship baseline:

```powershell
git checkout origin/docs/stewardship-baseline
```

Never delete a preserved evidence copy during rollback. Do not label any
AutoCAD release verified, promote compatibility, or close Stage 2 after a
failed, skipped, or unrecorded run.
