# Documentation

This index defines the current AutoCAD MCP documentation surface. Files below [`legacy/`](legacy/README.md) are preserved historical material and are not current product guidance.

## Project documentation

- [Project status](project-status.md): observed source state, known inconsistencies, and current validation limits
- [Architecture](architecture.md): adopted architecture and approved modernization target
- [Roadmap](roadmap.md): ordered deliveries with evidence-based acceptance gates
- [Epic portfolio](epics/README.md): detailed, dependency-gated work packages for parallel AI-agent development
- [Testing](testing.md): pure Python, MCP contract, and real AutoCAD test boundaries
- [Windows AutoCAD 2026 smoke guide](windows-testing-guide.md): first guarded real-device handoff
- [Compatibility](compatibility.md): targeted, verified, and excluded platforms and releases
- [Constrained code generation](advanced/constrained-code-generation-decision.md): literal recipe usage, output-only limits, and portable security evidence
- [Surface unfolding](advanced/surface-unfolding-decision.md): caller-supplied mesh support, independent numerical gates and bounded MCP evidence

## Maintainer documents

- [Repository rules](../AGENTS.md): mandatory language, workflow, test, security, and documentation policy
- [Modernization design](superpowers/specs/2026-08-25-maintenance-and-modernization-design.md): approved product and architecture decisions
- [Stewardship implementation plan](superpowers/plans/2026-08-25-stewardship-baseline.md): execution plan for the first maintenance pull request

## Historical material

- [Legacy archive](legacy/README.md): archived documentation and usage warning
- [Document audit](legacy/document-audit.md): disposition and evidence for every imported document

When a current document and a legacy document disagree, use the current document and verify important behavior against source code and fresh test evidence.
