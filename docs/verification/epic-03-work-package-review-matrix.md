# EPIC-03 work-package review matrix

This controller ledger freezes the review assignments and evidence destinations for
[EPIC-03](../epics/EPIC-03-windows-autocad-adapter-and-contract-tests.md). A row is
not evidence that its work package or gate has passed.

| Work package | Roles | Evidence artifact | Gate authority |
| --- | --- | --- | --- |
| E03-WP1: Approve protocol, error, and safety boundaries | controller; independent contract reviewer; independent quality reviewer | `docs/verification/evidence/epic-03/E03-WP1-protocol-and-safety-review.md` | independent contract reviewer at E03-G1 |
| E03-WP2: Build boundary models, focused fake, and reusable contracts test-first | controller; independent contract reviewer; independent quality reviewer | `docs/verification/evidence/epic-03/E03-WP2-fake-adapter-contract-tests.md` | independent contract reviewer at E03-G2 |
| E03-WP3: Prove delayed imports and implement the Windows COM boundary | controller; independent contract reviewer; independent quality reviewer | `docs/verification/evidence/epic-03/E03-WP3-delayed-import-and-com-boundary.md` | independent contract reviewer at E03-G3 |
| E03-WP4: Map the three active MCP tools through the fake adapter | controller; independent contract reviewer; independent quality reviewer | `docs/verification/evidence/epic-03/E03-WP4-fake-mcp-contracts.md` | independent contract reviewer at E03-G3 |
| E03-WP5: Build the copy guard, exclusive lease, and read-only harness | controller; independent contract reviewer; independent quality reviewer | `docs/verification/evidence/epic-03/E03-WP5-lease-and-read-only-harness.md` | maintainer approval at E03-G4 |
| E03-WP6: Write the full AutoCAD 2026 smoke sequence test-first | controller; independent contract reviewer; independent quality reviewer | `docs/verification/evidence/epic-03/E03-WP6-smoke-red-and-preflight.md` | controller records non-real preflight; no independent reviewer gate; real read-only execution waits for E03-WP7 after E03-G4 |
| E03-WP7: Execute and review the real AutoCAD 2026 gate | controller; independent contract reviewer; independent quality reviewer | `docs/verification/autocad-2026-smoke.md` | independent contract reviewer at E03-G5; maintainer at E03-G6 |

Only E03-WP7 can produce real-AutoCAD evidence. It is human-operator-only: the
controller must run it in an interactive Windows session with full AutoCAD 2026,
an acquired `AutoCADLease`, and a disposable read-only DWG copy. Linux, mocked-COM,
and fake-adapter results cannot replace that evidence.
