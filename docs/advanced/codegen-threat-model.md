# Constrained code generation: recipe threat boundary

This is Task 1 contract evidence for [EPIC-09 Track C](../epics/EPIC-09-validated-advanced-feature-recovery.md).
The [implementation plan](../superpowers/plans/2026-10-01-constrained-code-generation.md)
freezes the literal shapes and nine target/template pairs. Rendering, static
validation, service composition, and MCP registration are future work subject to
independent review. These contracts provide no safe-execution claim or AutoCAD
compatibility evidence. Track C has no AutoCAD verification gate.

## Untrusted input and current boundary

The attacker controls the JSON request, all selector values, literal records,
geometry coordinates/radii, handles, object/layer names, property keys, and scalar
values. Unknown or missing fields, unsupported selections, malformed types,
nonfinite/unbounded numbers, nested properties, duplicate normalized handles,
NUL, surrogates, and actual compact JSON above 16,384 UTF-8 bytes are rejected.
Errors contain only a fixed private code, never supplied content or exceptions.
JSON mappings cannot represent duplicate property keys; a transport decoder must
preserve/reject duplicates before it collapses them if duplicate detection is
required at that earlier boundary.

Accepted numbers and handles normalize deterministically. Recipe dictionaries
and lists are detached, then stored as read-only mapping proxies and tuples at
every nested level; the epic's `JsonValue` annotation describes the wire shape.
`recipe_payload` produces fresh mutable dictionaries/lists for transport.
`canonical_recipe_bytes` emits normalized compact, sorted, non-ASCII-preserving
JSON with nonfinite numbers forbidden. Input byte accounting uses the original
compact JSON before number/case normalization. The actual full MCP response
ceiling of 65,536 bytes must be enforced by the later service, including findings,
warning, and envelope; the model does not claim to enforce that future envelope.

## Forbidden sinks and later target trust

No recipe value may become an identifier, expression, import, member name,
format string, source fragment, template, or executable instruction. Facts are
supplied data; handles are literals with no lookup. Geometry is memory data,
not drawing mutation. Runtime imports are limited to the standard library and
core JSON data contracts. There is no adapter/context/capture/editing dependency,
file staging, credential/environment access, network, subprocess, interpreter,
macro dispatch, command dispatch, or execution companion.

| Target | Later encoding and independent validation requirement |
| --- | --- |
| Python | Reviewed literal encoding must round-trip data; static `ast.parse` and an exact AST/identifier/receiver allowlist validate source without execution. |
| AutoLISP | Reviewed quoted strings or fixed numeric code-unit constructors must preserve literals; a conservative tokenizer and exact template structure must reject unknown executable forms. |
| VBA | Reviewed quoted strings or fixed numeric code-unit constructors must preserve literals; a conservative tokenizer and exact template structure must reject unknown statements/member dispatch. |

Executable deny checks must inspect tokens outside literals. Quotes, comments,
newlines, control characters other than NUL, Unicode, and injection-looking words
are intentionally permitted in bounded fact strings. Their acceptance here
proves only that they are data: a later renderer must safely encode them or reject
an unrepresentable literal explicitly. Static acceptance cannot justify executing
an artifact. Later validators must fail closed on uncertainty, and any error
finding must prevent release. Template catalogue/golden changes require versioned
review and updated immutable evidence.

## Frozen synthetic evidence

The catalogue contains all nine pairs at template version `1.0.0`:
`literal_geometry`, `serialize_entity_facts`, and `iterate_handles` for `python`,
`autolisp`, and `vba`. The 873-case corpus has unique stable IDs and distinct
payloads: 576 `literal-data` cases and 297 fixed-code `reject` cases. Each target
has quote, delimiter/comment, newline/control, Unicode, import/evaluation,
process/network, file/credential, and macro/member attack families, plus schema
and byte-boundary failures. All content is synthetic; network examples use
`example.invalid` and credential examples use explicitly synthetic names.

| Fixture | SHA-256 |
| --- | --- |
| `tests/fixtures/codegen/catalogue.json` | `c87a5206c1791162d6f2ca76bafcb57a1e010f31981eca104bc3dd05c824a9a5` |
| `tests/fixtures/codegen/malicious-corpus.json` | `99f7622181d35afa382a2ea005dea0caa0034ec50fc2432fa2e6c8ff14d977ef` |

Focused tests pin both file digests, classifications, uniqueness, catalogue
examples, normalized handles/numbers, deep immutability, scalar/count/length
limits, cyclic/nested rejection, and exact request-byte acceptance/overflow.
The corpus is frozen before rendering. Later authors must not relabel cases to
hide escaping or injection failures. Independent contract/security acceptance
remains pending; rendered-source, golden, validator, and non-execution MCP gates
have not yet run.
