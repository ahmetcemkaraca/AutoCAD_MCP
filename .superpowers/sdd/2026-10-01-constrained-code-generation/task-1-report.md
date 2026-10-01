# Task 1 implementation report

Date: 2026-10-01. Branch: `codex/epic-09c-constrained-code-generation`.
Baseline: `164bf61`, including accepted shared bounds `343d584`.

## Outcome and scope

Implemented the exact EPIC-09C recipe/artifact dataclasses and strict recipe
codec, without rendering, static validation, service composition, registration,
or shared-file changes. Recipe validation is pure Python and output-only.
Frozen evidence covers nine template/target pairs and 873 distinct malicious
payloads (576 literal-data, 297 rejection). Independent contract/security review
is pending before Task 2. Literal acceptance does not establish safe rendering.

Owned changed files:

- `src/autocad_mcp/advanced/codegen/__init__.py` and `models.py`;
- `tests/unit/advanced/codegen/__init__.py`, `test_models.py`, and
  `test_contract_rejections.py`;
- `tests/fixtures/codegen/catalogue.json` and `malicious-corpus.json`;
- `docs/advanced/codegen-threat-model.md`;
- this Task 1 evidence report.

## Public interfaces

In `autocad_mcp.advanced.codegen.models`:

```python
class CodeTarget(StrEnum):  # python, autolisp, vba
    ...

@dataclass(frozen=True)
class CodeRecipe:
    schema_version: Literal["1"]
    template_id: str
    template_version: str
    target: CodeTarget
    literals: Mapping[str, JsonValue]

@dataclass(frozen=True)
class StaticFinding:
    rule_id: str
    severity: Literal["error", "warning"]
    location: str
    message: str

@dataclass(frozen=True)
class GeneratedCodeArtifact:
    target: CodeTarget
    template_id: str
    template_version: str
    source: str
    digest: str
    findings: tuple[StaticFinding, ...]
    executed: Literal[False]
    warning: Literal["Generated text was not executed; review it outside AutoCAD MCP."]

class CodeGenerationError(ValueError):
    code: str

def decode_recipe(payload: object) -> CodeRecipe: ...
def recipe_payload(recipe: CodeRecipe) -> dict[str, JsonValue]: ...
def canonical_recipe_bytes(recipe: CodeRecipe) -> bytes: ...
```

Constants: `MAX_RECIPE_BYTES = 16384`, `MAX_ARTIFACT_BYTES = 65536`,
`TEMPLATE_VERSION = "1.0.0"`, `TEMPLATE_IDS` (the three frozen IDs), and
`HUMAN_REVIEW_WARNING` (exact epic warning). There are no package-level exports.
The private error vocabulary is the six codes frozen in the plan; failure
messages are exactly their code and contain no caller data.

`CodeRecipe` also validates direct construction from JSON-shaped literals,
normalizes handles/numbers, and freezes all nested mappings/lists as mapping
proxies/tuples. `JsonValue` retains the exact epic wire annotation; the codec
thaws immutable storage into fresh JSON lists/dictionaries. Existing immutable
storage is not an alternative JSON input format. Caller strings remain literal
data, including injection-looking words. The input limit counts original compact
JSON UTF-8 bytes, before number/case normalization. The artifact constructor
rejects `executed != False` or a changed mandatory warning and detaches findings
into a tuple. It does not perform source validation or response-envelope sizing.

## Fresh verification evidence

Commands ran using the preexisting `.venv` and its installed dependencies. No
new dependency was installed. Red evidence preceded all production model code.

| Command | Result |
| --- | --- |
| `.venv/bin/python -m pytest tests/unit/advanced/codegen/test_models.py tests/unit/advanced/codegen/test_contract_rejections.py -q` (initial red) | 23 failed: explicit failure that the recipe contract was not implemented; no production code existed. |
| `.venv/bin/python -m pytest tests/unit/advanced/codegen -q --tb=no` (expanded red, frozen corpus and maxima/cycle tests) | 25 failed for the missing contract. |
| `.venv/bin/python -m pytest tests/unit/advanced/codegen -q --tb=short` (initial green) | 25 passed in 3.53s. |
| `.venv/bin/python -m pytest tests/unit/advanced/codegen/test_models.py tests/unit/advanced/codegen/test_contract_rejections.py -q` (final focused) | 25 passed in 1.00s. |
| `.venv/bin/python -m pytest -q` (full portable suite, once) | 277 passed, 9 skipped in 16.98s; exit 0. |
| `.venv/bin/ruff check src/autocad_mcp/advanced/codegen/models.py tests/unit/advanced/codegen` | All checks passed; exit 0. |
| `.venv/bin/mypy src/autocad_mcp/advanced/codegen` | Success: no issues found in 2 source files; exit 0. |
| `.venv/bin/python -m compileall -q src tests` | No output; exit 0. |
| `git diff --check` | No output; exit 0. |

Initial Ruff found formatting/line-length issues and a test lambda assignment;
these were corrected with source-local changes and `ruff format`. No behavior
changed after final green. Ruff reports the existing deprecated top-level lint
settings; mypy notes unused existing Windows-module override sections. These
configuration files were not changed.

The guarded import/source check below passed with this output:
`Guarded codegen import, source import allowlist, and normalized recipe check passed`.

```bash
.venv/bin/python - <<'PY'
import ast
import importlib.abc
import sys
from pathlib import Path
import autocad_mcp
import autocad_mcp.core.models

class RejectRuntimeImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        forbidden = (
            'pythoncom', 'win32com', 'pyautocad', 'autocad_mcp.adapters',
            'autocad_mcp.context', 'autocad_mcp.capture', 'autocad_mcp.editing',
            'subprocess', 'socket', 'urllib', 'requests',
        )
        if any(fullname == name or fullname.startswith(name + '.') for name in forbidden):
            raise AssertionError('Forbidden codegen import: ' + fullname)
        return None

sys.meta_path.insert(0, RejectRuntimeImports())
from autocad_mcp.advanced.codegen.models import decode_recipe, canonical_recipe_bytes
recipe = decode_recipe(dict(
    schema_version='1', template_id='iterate_handles', template_version='1.0.0',
    target='python', literals={'handles': ['abc']},
))
assert b'ABC' in canonical_recipe_bytes(recipe)
assert not any(name.startswith((
    'pythoncom', 'win32com', 'pyautocad', 'autocad_mcp.adapters',
    'autocad_mcp.context', 'autocad_mcp.capture', 'autocad_mcp.editing',
)) for name in sys.modules)
allowed = {
    'json', 'math', 're', 'collections.abc', 'dataclasses', 'enum', 'types',
    'typing', 'autocad_mcp.core.models',
}
for path in Path('src/autocad_mcp/advanced/codegen').glob('*.py'):
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            assert all(alias.name in allowed for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.module in allowed
print('Guarded codegen import, source import allowlist, and normalized recipe check passed')
PY
```

An initial broader process-start import guard failed because the existing root
package imports `importlib.metadata`, which imports `email.utils` and then the
stdlib `socket` module. This is inherited package initialization, not a codegen
network import or network call. The passing check preloads the shared package and
core contracts and guards the added codegen import; an AST allowlist separately
checks every direct codegen import. No shared-package change was made. This is
not evidence of full future service/MCP zero-call file/process spies.

## Frozen evidence and remaining gates

- Catalogue SHA-256:
  `c87a5206c1791162d6f2ca76bafcb57a1e010f31981eca104bc3dd05c824a9a5`.
- Corpus SHA-256:
  `99f7622181d35afa382a2ea005dea0caa0034ec50fc2432fa2e6c8ff14d977ef`.
- Tests pin exact bytes/digests, IDs, distinct payloads, expected classifications,
  supported examples, literal maxima, strict rejection, canonical bytes, detached
  exports, deep immutability, normalized numbers/handles, and input byte boundary.
- Threat documentation distinguishes current data validation from future target
  encoding/parser trust, executable-token validation, and no-execution gates.
- No real AutoCAD release was used or required. Linux results are portable
  contract evidence only; they do not change AutoCAD compatibility labels.
- Task 2 rendering/goldens, Task 3 independent validation/service, and Task 4
  registration/envelope/no-execution tests remain unimplemented in this task.
- Review must accept these contracts and fixed corpus before Task 2; later authors
  must preserve rejection classifications and prove escaping or explicitly reject
  target-unrepresentable literal data without hiding injection failures.
