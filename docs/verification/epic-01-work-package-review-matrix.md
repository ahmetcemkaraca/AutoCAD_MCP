# EPIC-01 work-package review matrix

This controller ledger freezes the review assignments and evidence destinations for
[EPIC-01](../epics/EPIC-01-reproducible-windows-development-baseline.md). A row is
not evidence that its work package or gate has passed.

| Work package | Roles | Evidence artifact | Gate authority |
| --- | --- | --- | --- |
| E01-WP1: Freeze the dependency and metadata inventory | controller; independent contract reviewer; independent quality reviewer | `docs/verification/evidence/epic-01/E01-WP1-inventory.md` | independent contract reviewer at E01-G1 |
| E01-WP2: Write failing metadata and marker tests | controller; independent contract reviewer; independent quality reviewer | `docs/verification/evidence/epic-01/E01-WP2-red-metadata-tests.md` | controller records the red state; the controller must record the baseline `.gitignore` constraint and Task 2's narrow `!tests/**/test_*.py` remediation |
| E01-WP3: Migrate to PEP 621 and generate `uv.lock` | controller; independent contract reviewer; independent quality reviewer | `docs/verification/evidence/epic-01/E01-WP3-frozen-sync-and-marker-checks.md` | independent contract reviewer at E01-G2 |
| E01-WP4: Classify the root Docker artifacts before disposition | controller; independent contract reviewer; independent quality reviewer | `docs/verification/evidence/epic-01/E01-WP4-container-disposition.md` | maintainer approval at E01-G3 |
| E01-WP5: Update canonical developer instructions with fresh evidence | controller; independent contract reviewer; independent quality reviewer | `docs/verification/evidence/epic-01/E01-WP5-final-baseline-verification.md` | independent quality reviewer at E01-G4 |

Evidence for E01-WP3 and E01-WP5 must keep Linux marker/syntax results separate
from the Windows frozen-sync witness. Neither is real-AutoCAD evidence.
