# Constrained Code Generation Implementation Plan

> Use superpowers:subagent-driven-development. This is the independent EPIC-09C
> output-only track. No AutoCAD execution or drawing approval is involved.

**Goal:** Return statically validated educational source text from nine fixed
target/template pairs. Never execute, save, import or apply the generated text.

**Spec:** EPIC-09 Track C in
`docs/epics/EPIC-09-validated-advanced-feature-recovery.md`.

**Baseline:** Main599e8a9 plus the accepted shared cooperative-bounds commit
789b30e (cherry-picked as343d584). Shared bounds are read-only to this lane;
final integration must reconcile the identical shared source from Track U.

## Global constraints

- Exact CodeTarget, CodeRecipe, StaticFinding and GeneratedCodeArtifact fields
  from the epic; immutable nested recipe data, literal schema version `1`.
- Standard library and existing test dependencies only. Production modules may
  import core data contracts and other codegen modules; no adapter, context,
  capture, editing, COM, filesystem staging, network, subprocess or interpreter.
- Only reviewed built-in templates; no caller source/template/expression/import/
  identifier/body/format or postprocessor input. Returned strings are data.
- Deterministic source and digest for the same normalized recipe and version.
  No timestamps, elapsed time, host state or raw exceptions in output/logs.
- Full serialized MCP result at most 65,536 UTF-8 bytes, including envelope,
  findings and warning. Overflows reject; never truncate or silently substitute.
- `executed` is always false and the exact epic warning is mandatory.
- Security review of contract/catalogue precedes template rendering; independent
  review of every golden and validators precedes registration. No AutoCAD gate.

## Frozen catalogue and literal inputs

All three targets (`python`, `autolisp`, `vba`) support version `1.0.0` of:

| template_id | Exact literal fields | Behavior |
| --- | --- | --- |
| literal_geometry | lines, circles | Construct supplied line/circle data in memory only |
| serialize_entity_facts | facts | Assign canonical supplied-fact JSON to a caller-visible string |
| iterate_handles | handles | Read-only iteration over the supplied literal handles, no lookup |

No values are interpreted as member names or code. `lines` is a list of at most
64 objects with exactly `start` and `end`, each three finite non-Boolean numbers
with absolute value at most 1e15. `circles` is a list of at most64 objects with
exactly `center` (same point rule) and finite positive `radius <=1e15`. Require
at least one combined geometry record. Numbers normalize to finite float with
negative zero made positive zero. No geometry is created in AutoCAD.

`facts` is a list of 1-64 supplied entity objects, each with exactly `handle`,
`object_name`, `layer`, `properties`. A handle is 1-16 hexadecimal digits,
normalized uppercase without `0x`; handles are unique. Object/layer names are
nonempty strings up to255 Unicode code points. Properties are at most16 unique
string keys (1-128 code points) mapped to scalar JSON values only: null, bool,
bounded integers (abs <=2**53-1), finite floats (abs <=1e15), or strings of at
most1024 code points. No nested objects/arrays, surrogate code points or NUL.
Names/property strings may contain injection-looking text; they remain data
and must be escaped or explicitly rejected by the target's safe literal rules.
Do not apply source deny-word matching to literal content.

`handles` is a list of1-256 unique normalized handles under the same rule.
Input object keys, target, template and version use exact closed schemas.
Bound both the original and normalized compact JSON recipe to16KiB UTF-8
before rendering, so accepted canonical exports round-trip through the same
admission boundary. This
per-track input limit is below the shared server ceiling. Unsupported target,
template and version have distinct fixed private errors; unknown/malformed
fields are invalid arguments. Oversized input/output is a payload-limit error.

Freeze helpers in Task1:

```python
class CodeGenerationError(ValueError):
    code: str
def decode_recipe(payload: object) -> CodeRecipe: ...
def recipe_payload(recipe: CodeRecipe) -> dict[str, JsonValue]: ...
def canonical_recipe_bytes(recipe: CodeRecipe) -> bytes: ...
```

Private error vocabulary: `INVALID_ARGUMENT`, `UNSUPPORTED_TARGET`,
`UNSUPPORTED_TEMPLATE`, `UNSUPPORTED_TEMPLATE_VERSION`, `PAYLOAD_LIMIT`,
`STATIC_VALIDATION_FAILED`. Core integration owns any necessary shared enum
additions later. Helpers must not retain mutable caller data or echo it in
exceptions. Parsing receives JSON-compatible mappings, not source code.

## Task 1: Contracts, threat boundary and malicious corpus

**Own:** `advanced/codegen/{__init__,models}.py`, focused model/rejection tests,
`tests/fixtures/codegen/catalogue.json`, `malicious-corpus.json`, and a concise
`docs/advanced/codegen-threat-model.md`. No renderer, validator or registration.

- [x] Read the exact epic types/core JsonValue; test strict schemas, all bounds,
  normalized handles/numbers, deep immutability, deterministic bytes, unknown
  template/version/target and safe redacted failures before implementation.
- [x] Freeze catalogue and at least500 distinct malicious schema/literal cases
  with stable IDs and expected reject-or-literal-data classification. Cover all
  targets: quotes, delimiters/comments, newline/control/Unicode, import/eval/
  process/network/file/credential/macro/member payloads, malformed fields/types,
  nesting and byte limits. Do not count duplicate IDs/identical cases as variety.
- [x] Record attacker fields, forbidden sinks, per-target encoding/parser trust
  and later validator limits. A literal accepted here is not yet safe generated
  source; the later target escaping/static gates must prove that separately.
- [x] Implement the minimal strict models/codec, run focused and affected/full
  portable tests once, lint/type/import checks, commit/report. Independent
  contract/security review before Task2. Corpus labels cannot be weakened by
  later renderers to hide an injection failure.

## Task 2: Fixed templates and literal encoders

**Own:** `templates.py`, `render.py`, golden/escaping/determinism tests and
synthetic golden source/digest fixtures. No service/runtime registration.

Public handoff: `render_recipe(recipe: CodeRecipe) -> str` returns source only.
It consumes the accepted immutable recipe, uses only the fixed catalogue and
version, and rejects a rendered source above65,536 UTF-8 bytes with the existing
private payload-limit error. Later service/MCP owners must also bound the full
artifact/envelope; this source ceiling is not sufficient by itself. Encoding
helpers stay private unless an actual second consumer needs them. No source
execution, interpreter/compiler invocation or artifact persistence is allowed.
Use fixed local variable/procedure names, never AutoCAD command or auto-run
macro entry points. Generated iteration works only on supplied literal handles.
Source-language grammar/escape assumptions must be checked against primary
language documentation before freezing each target's goldens.

- [x] Freeze hand-reviewed expected output for every pair before rendering.
  Use fixed local identifiers and only bounded literal encoders. Prefer ordinary
  quoted strings; where a target needs a safe code-unit constructor for control
  characters, allow only fixed reviewed constructor syntax with numeric units.
- [x] Implement literal-only rendering, exact roundtrip tests across supported
  text/number boundaries, and structured unsupported literal failures when a
  target cannot represent data safely. No runtime inspection/execution.
- [x] Test the complete malicious literal corpus through safe rendering, fixed
  variables/template identity, determinism and output-size refusal. Independent
  golden/security review before Task3.

## Task 3: Independent static validation and output-only service

**Own:** `validate.py`, `service.py`, static/adversarial/service tests.

Freeze these pure public seams:

```python
def validate_source(recipe: CodeRecipe, source: str) -> tuple[StaticFinding, ...]: ...
def generate_code(payload: object) -> GeneratedCodeArtifact: ...
def artifact_payload(artifact: GeneratedCodeArtifact) -> dict[str, JsonValue]: ...
```

The validator imports models/core data and stdlib only, never renderer/templates
or their private helpers. Independently parse the exact reviewed function and
local-assignment/return/iteration structures. Reconstruct literal data as data
only and compare it to the recipe; do not evaluate a generated function or use
the renderer itself as a validation oracle. Python uses AST; AutoLISP/VBA use
bounded conservative token/structure parsing, with quotes decoded before any
executable-token policy. Unknown syntax, extra invocation/definition, changed
literal data or unsafe names fail. A fixed first-error finding is sufficient;
diagnostics contain fixed rules/messages and positions, never source fragments.

The service decodes the input before rendering, renders once, validates once,
and refuses any error finding with STATIC_VALIDATION_FAILED. Artifact digest is
`sha256:` plus SHA-256 of compact sorted UTF-8 JSON containing exactly target,
template_id, template_version and source. It constructs the exact artifact with
executed false and the mandatory warning, and bounds actual artifact JSON bytes
to65,536. The later MCP owner must separately enforce the full serialized tool
envelope (including JSON text escaping), not infer it from artifact size.
No service class/factory/cache or new dependency is needed for this stateless
pipeline. Test spies may patch these existing function seams.

- [x] A different author from rendering implements the validator. Reject
  deliberately injected executable constructs first. Python uses an exact AST
  allowlist including fixed identifiers/call receivers; ast.parse is static
  parsing only. AutoLISP/VBA use conservative token/structure allowlists and
  exact template structure. No code execution, interpreter or compiler launch.
- [x] Deny rules inspect executable tokens, not escaped literal text. Unknown
  syntax or validator uncertainty fails; any error finding prevents artifact
  release. Verify every golden and all500+ malicious cases independently.
- [x] Service validates recipe, renders once, validates artifact, computes
  SHA-256 over canonical target/template/version/source metadata, constructs
  the exact artifact/warning and checks its actual bytes. No persistence/cache.
- [x] Record scoped Bandit/source-sink/import checks, full affected tests and
  immutable catalogue/golden/corpus digests for independent security acceptance.

## Task 4: Serialized core integration and decision record

**Own:** `tools/constrained_code_generation.py`, contract/no-execution tests;
shared core/runtime/server/manifest/docs only during controller integration.

The public tool is `generate_constrained_code`; arguments are the exact
`CodeRecipe` object without a wrapper, and success contains `artifact` with the
exact artifact payload. Publish closed, template-discriminated literal schemas.
Preserve the existing basic service seam and route C directly to its pure
handler. Default runtime construction must defer adapter imports and creation
until a validated basic operation needs the existing adapter service. Invalid,
unknown and C calls must not initialize that service.

Enforce 65,536 UTF-8 bytes on the complete serialized SDK `CallToolResult` body,
including nested JSON text escaping and content/isError fields. The client
request identifier is transport metadata outside this result body. Test exact
boundary/one-over using the registered handler and real SDK serialization, plus
a quote-heavy real recipe. Return redacted `PAYLOAD_LIMIT` without source on
overflow. Source/artifact-only checks do not establish this bound.

Fresh-process default-server import guards and real stdio C calls establish the
core-only boundary without replacing runtime composition. Request-scoped
file/process/network/evaluation spies start after Python/MCP import bootstrap;
AST-only parsing is allowed. Keep basic injection tests and update canonical
catalogue, help, manifest, tool counts and documentation together. Record
content-addressed security evidence before final review and hosted CI.

- [ ] Test exact closed MCP schema, structured errors, full64KiB response bound,
  returned literal-warning/artifact shape and pure injection-only composition.
- [ ] Guard imports and forbidden file/process/adapter execution paths; actual
  stdio/core tests must prove output-only behavior and no execute companion.
- [ ] Register only after independent contract/pure/security gates. Preserve
  existing tools and record the Track C decision and content-addressed evidence.
- [ ] Run full portable/Windows-CI checks as applicable, independent final review
  and focused PR. No AutoCAD compatibility or other-epic completion claim.

## Preflight dependencies

Task1 models/catalogue/corpus bind2/3;2 rendered source/goldens bind3;3 accepted
artifact binds4. Shared core changes serialize with other tracks. Template
version/digest changes require updated independent review, not mutable evidence.
The approved version-one scope includes all nine pairs; inability to meet a
target's safety gate is recorded as revise/reject with reasons, not a fake
passing placeholder or silent narrowing of the user's full portfolio.
