# EPIC-02 work-package review matrix

This controller ledger freezes the review assignments and evidence destinations for
[EPIC-02](../epics/EPIC-02-canonical-mcp-core.md). A row is not evidence that its
work package or gate has passed.

| Work package | Roles | Evidence artifact | Gate authority |
| --- | --- | --- | --- |
| E02-WP1: Approve the compatibility and type contract | controller; independent contract reviewer; independent quality reviewer | `docs/verification/evidence/epic-02/E02-WP1-contract-and-schema-baseline.md` | independent contract reviewer at E02-G1 |
| E02-WP2: Enable the installable canonical package test-first | controller; independent contract reviewer; independent quality reviewer | `docs/verification/evidence/epic-02/E02-WP2-package-red-and-frozen-sync.md` | controller records evidence for E02-G2 |
| E02-WP3: Build typed models and closed schemas test-first | controller; independent contract reviewer; independent quality reviewer | `docs/verification/evidence/epic-02/E02-WP3-model-and-schema-tests.md` | independent contract reviewer at E02-G2 |
| E02-WP4: Add the service port and centralized dispatch | controller; independent contract reviewer; independent quality reviewer | `docs/verification/evidence/epic-02/E02-WP4-dispatch-tests.md` | controller records evidence for E02-G3 |
| E02-WP5: Create the canonical package server and compatibility shim | controller; independent contract reviewer; independent quality reviewer | `docs/verification/evidence/epic-02/E02-WP5-stdio-contracts.md` | independent contract reviewer at E02-G3 |
| E02-WP6: Retire duplicate server and mismatched Flask tests | controller; independent contract reviewer; independent quality reviewer | `docs/verification/evidence/epic-02/E02-WP6-retirement-and-regression.md` | independent quality reviewer at E02-G4 |
| E02-WP7: Align manifest and canonical documentation | controller; independent contract reviewer; independent quality reviewer | `docs/verification/evidence/epic-02/E02-WP7-documentation-and-final-regression.md` | independent quality reviewer at E02-G5 |

Linux package, unit, and stdio-contract results are automated evidence only. They
do not substitute for the Windows/full-AutoCAD evidence controlled by EPIC-03.
