# Imported Documentation Audit

This audit covers every documentation file adopted from the previous repository state. The review compared document structure, commands, endpoint claims, referenced paths, duplicate content, repository URLs, and completion claims with the source tree adopted on 2026-08-25.

## Classifications

| Code | Classification | Meaning |
| --- | --- | --- |
| D | Duplicate | Exact or near-duplicate content exists elsewhere in the imported set. |
| O | Obsolete | Setup, ownership, transport, or workflow information no longer matches the repository. |
| S | Speculative | Proposed behavior, metrics, or integrations are presented without reproducible evidence. |
| C | Code-inconsistent | Described endpoints, entry points, files, tests, or tools do not match the adopted source tree. |
| R | Historical research | Potentially useful research or requirements that have not been validated as product behavior. |
| U | Unrelated tooling | Documentation is not part of the AutoCAD MCP product or contributor workflow. |

All files were preserved below `docs/legacy/imported-2025/`. Multiple codes indicate multiple reasons for archival.

## Root and user guides

| Original path | Archived path | Class | Review finding |
| --- | --- | --- | --- |
| `README.md` | `imported-2025/README.md` | O, S, C | Uses the unavailable upstream URL and advertises unverified production and enterprise behavior. |
| `docs/00-README-First.md` | `imported-2025/docs/00-README-First.md` | O, S | Introduces capabilities without a verified runtime baseline. |
| `docs/01-Installation-Setup.md` | `imported-2025/docs/01-Installation-Setup.md` | D, O | Exact duplicate of the drafter guide and uses the unavailable upstream URL. |
| `docs/02-Basic-Drawing-Operations.md` | `imported-2025/docs/02-Basic-Drawing-Operations.md` | D, C | Generated guide includes operations not registered by the current entry point. |
| `docs/02-Your-First-Success.md` | `imported-2025/docs/02-Your-First-Success.md` | D, O | Exact duplicate of the drafter guide and relies on unverified setup behavior. |
| `docs/03-AI-Code-Generation.md` | `imported-2025/docs/03-AI-Code-Generation.md` | D, S | Describes a code-generation product flow not exposed by the current server. |
| `docs/03-Basic-Drawing-Operations.md` | `imported-2025/docs/03-Basic-Drawing-Operations.md` | D, C | Duplicate topic with unsupported operations. |
| `docs/04-AI-Code-Generation.md` | `imported-2025/docs/04-AI-Code-Generation.md` | D, S | Duplicate speculative code-generation guide. |
| `docs/04-API-Recommendations.md` | `imported-2025/docs/04-API-Recommendations.md` | D, S | Describes a tool absent from the canonical MCP entry point. |
| `docs/05-3D-Surface-Unfolding.md` | `imported-2025/docs/05-3D-Surface-Unfolding.md` | D, S | Presents research code as an available end-user workflow. |
| `docs/05-API-Recommendations.md` | `imported-2025/docs/05-API-Recommendations.md` | D, S | Duplicate speculative API-recommendation guide. |
| `docs/06-3D-Surface-Unfolding.md` | `imported-2025/docs/06-3D-Surface-Unfolding.md` | D, S | Exact duplicate of a drafter guide and lacks real-AutoCAD validation. |
| `docs/06-Parametric-Design.md` | `imported-2025/docs/06-Parametric-Design.md` | D, S | Describes a parametric tool surface absent from the server. |
| `docs/07-Parametric-Design.md` | `imported-2025/docs/07-Parametric-Design.md` | D, S | Duplicate speculative parametric workflow. |
| `docs/07-Pattern-Optimization.md` | `imported-2025/docs/07-Pattern-Optimization.md` | D, S | Presents unintegrated optimization code as a user feature. |
| `docs/08-Deployment-Automation.md` | `imported-2025/docs/08-Deployment-Automation.md` | D, S | Describes deployment automation outside the current product surface. |
| `docs/08-Pattern-Optimization.md` | `imported-2025/docs/08-Pattern-Optimization.md` | D, S | Duplicate speculative optimization guide. |
| `docs/09-Deployment-Automation.md` | `imported-2025/docs/09-Deployment-Automation.md` | D, S | Duplicate speculative deployment guide. |
| `docs/09-Mock-AutoCAD-System.md` | `imported-2025/docs/09-Mock-AutoCAD-System.md` | D, C | Describes a user-facing mock mode not exposed by the root server. |
| `docs/10-Mock-AutoCAD-System.md` | `imported-2025/docs/10-Mock-AutoCAD-System.md` | D, C | Duplicate mock-system guide inconsistent with the entry point. |
| `docs/10-Troubleshooting-Guide.md` | `imported-2025/docs/10-Troubleshooting-Guide.md` | D, C | Troubleshoots tools and errors absent from the current server. |
| `docs/11-FAQ.md` | `imported-2025/docs/11-FAQ.md` | D, O | Exact duplicate of `docs/12-FAQ.md` with stale setup statements. |
| `docs/11-Troubleshooting-Guide.md` | `imported-2025/docs/11-Troubleshooting-Guide.md` | D, O | Exact duplicate of the drafter troubleshooting guide. |
| `docs/12-FAQ.md` | `imported-2025/docs/12-FAQ.md` | D, O | Duplicate FAQ with unverified requirements. |
| `docs/README.md` | `imported-2025/docs/README.md` | O | Links the unavailable upstream owner and routes to misleading guides. |

## Product, architecture, and planning documents

| Original path | Archived path | Class | Review finding |
| --- | --- | --- | --- |
| `docs/AutoCAD_MCP_Summary.md` | `imported-2025/docs/AutoCAD_MCP_Summary.md` | S, C | Claims completed endpoints, metrics, and manufacturing features absent from the stdio server. |
| `docs/PRD.md` | `imported-2025/docs/PRD.md` | R, C | Useful historical requirements are based on a Flask server and unimplemented endpoints. |
| `docs/USER_STORIES.md` | `imported-2025/docs/USER_STORIES.md` | S, C | User stories call many HTTP endpoints not present in the adopted tree. |
| `docs/backward-compatibility-requirements.md` | `imported-2025/docs/backward-compatibility-requirements.md` | S, C | Attempts to preserve a large HTTP API that is not the current runtime. |
| `docs/development-workflow-enhanced.md` | `imported-2025/docs/development-workflow-enhanced.md` | S, C | Provides code for missing modules and an unsafe arbitrary execution direction. |
| `docs/enhancement-specification.md` | `imported-2025/docs/enhancement-specification.md` | S, C | Specifies absent `/tools/*` endpoints and speculative enterprise requirements. |
| `docs/feature-checklist.md` | `imported-2025/docs/feature-checklist.md` | S | A broad aspirational checklist cannot establish implemented status. |
| `docs/implementation-roadmap.md` | `imported-2025/docs/implementation-roadmap.md` | S, C | Calendar plan references missing files and completed-looking acceptance claims. |
| `docs/master-coder-architecture.md` | `imported-2025/docs/master-coder-architecture.md` | S, C | Describes a Flask and VS Code architecture not used by the root command. |
| `docs/master-coder-development-plan.md` | `imported-2025/docs/master-coder-development-plan.md` | S, C | Plans missing source areas and unsafe execution capabilities. |
| `docs/mcp-api-specification.md` | `imported-2025/docs/mcp-api-specification.md` | C | Specifies HTTP endpoints rather than the adopted stdio MCP tool surface. |
| `docs/migration-path.md` | `imported-2025/docs/migration-path.md` | S, C | References missing migration scripts, wrapper files, tests, and benchmarks. |
| `docs/mission.md` | `imported-2025/docs/mission.md` | R | Historical mission input is too narrow and is superseded by the approved design. |
| `docs/openapi-specification.yaml` | `imported-2025/docs/openapi-specification.yaml` | C | Describes an HTTP API not served by the current entry point. |
| `docs/technical-architecture.md` | `imported-2025/docs/technical-architecture.md` | S, C | References absent modules, containers, monitoring, caching, and Flask routing. |
| `docs/testing-validation.md` | `imported-2025/docs/testing-validation.md` | S, C | Describes test files, CI, coverage, security, and performance suites that do not exist. |
| `docs/user-stories-enhanced.md` | `imported-2025/docs/user-stories-enhanced.md` | S | Treats speculative development and enterprise systems as committed product scope. |
| `docs/vba-integration-specification.md` | `imported-2025/docs/vba-integration-specification.md` | S | Proposes broad VBA execution and enterprise capabilities outside the approved safe scope. |

## Development and research documents

| Original path | Archived path | Class | Review finding |
| --- | --- | --- | --- |
| `docs/development/POLYFACE_MESH_RESEARCH.md` | `imported-2025/docs/development/POLYFACE_MESH_RESEARCH.md` | R | Potentially useful COM research; product behavior remains unverified. |
| `docs/development/development-workflow.md` | `imported-2025/docs/development/development-workflow.md` | O, C | Workflow references missing integration and performance suites. |
| `docs/development/phase1-implementation-plan.md` | `imported-2025/docs/development/phase1-implementation-plan.md` | S, C | Planned Flask endpoints and tests do not match the current entry point. |
| `docs/development/phase2-implementation-plan.md` | `imported-2025/docs/development/phase2-implementation-plan.md` | S, C | Planned HTTP 3D operations are not current MCP registrations. |
| `docs/development/roadmap.md` | `imported-2025/docs/development/roadmap.md` | O, S | Dated calendar roadmap lacks evidence-based exit gates. |
| `docs/surface-unfolding-algorithm.md` | `imported-2025/docs/surface-unfolding-algorithm.md` | R | Mathematical research is useful input but has no current end-to-end validation. |

## Imported integration documents

| Original path | Archived path | Class | Review finding |
| --- | --- | --- | --- |
| `docs/legacy/mcp-client-library.md` | `imported-2025/docs/legacy/mcp-client-library.md` | R, C | Historical client design does not match the current package or server boundary. |
| `docs/legacy/roo-code-compatibility.md` | `imported-2025/docs/legacy/roo-code-compatibility.md` | O | Historical editor integration is not a maintained compatibility commitment. |
| `docs/legacy/vscode-integration.md` | `imported-2025/docs/legacy/vscode-integration.md` | O, C | Uses a localhost REST architecture and references a missing client module. |

## Use cases

| Original path | Archived path | Class | Review finding |
| --- | --- | --- | --- |
| `docs/use-cases/architecture-engineering.md` | `imported-2025/docs/use-cases/architecture-engineering.md` | S, C | Advertises BIM, MEP, analysis, and compliance tools not exposed by the server. |
| `docs/use-cases/education-training.md` | `imported-2025/docs/use-cases/education-training.md` | S, C | Advertises learning management and collaboration systems absent from the code path. |
| `docs/use-cases/manufacturing.md` | `imported-2025/docs/use-cases/manufacturing.md` | S, C | Advertises CNC, G-code, quality, and costing workflows without verified tools. |
| `docs/use-cases/product-design.md` | `imported-2025/docs/use-cases/product-design.md` | S, C | Advertises ergonomic, DFM, and assembly analysis absent from the current server. |

## Drafter guides

| Original path | Archived path | Class | Review finding |
| --- | --- | --- | --- |
| `docs_for_drafters/00-README-First.md` | `imported-2025/docs_for_drafters/00-README-First.md` | D, O | Near-duplicate introduction based on unverified behavior. |
| `docs_for_drafters/01-Installation-Setup.md` | `imported-2025/docs_for_drafters/01-Installation-Setup.md` | D, O | Exact duplicate with unavailable upstream URL and screenshot placeholders. |
| `docs_for_drafters/02-Your-First-Success.md` | `imported-2025/docs_for_drafters/02-Your-First-Success.md` | D, O | Exact duplicate with unverified setup outcome and screenshot placeholders. |
| `docs_for_drafters/03-Basic-Drawing-Operations.md` | `imported-2025/docs_for_drafters/03-Basic-Drawing-Operations.md` | D, C | Exact duplicate with unsupported operations. |
| `docs_for_drafters/04-3D-Surface-Unfolding.md` | `imported-2025/docs_for_drafters/04-3D-Surface-Unfolding.md` | D, S | Exact duplicate presenting research as an end-user feature. |
| `docs_for_drafters/05-Troubleshooting-Guide.md` | `imported-2025/docs_for_drafters/05-Troubleshooting-Guide.md` | D, O | Exact duplicate with generic, unverified advice. |
| `docs_for_drafters/06-FAQ.md` | `imported-2025/docs_for_drafters/06-FAQ.md` | O, S | Makes safety and cost claims without an established product baseline. |

## Unrelated tooling

| Original path | Archived path | Class | Review finding |
| --- | --- | --- | --- |
| `monitoring-tools/MONITORING_TOOLS_GUIDE.md` | `imported-2025/monitoring-tools/MONITORING_TOOLS_GUIDE.md` | U, O | Documents third-party Claude token dashboards, not AutoCAD MCP runtime monitoring. |

## Duplicate evidence

The audit found these exact-content groups after normalizing trailing whitespace:

- `docs/01-Installation-Setup.md` and `docs_for_drafters/01-Installation-Setup.md`
- `docs/02-Your-First-Success.md` and `docs_for_drafters/02-Your-First-Success.md`
- `docs/03-Basic-Drawing-Operations.md` and `docs_for_drafters/03-Basic-Drawing-Operations.md`
- `docs/06-3D-Surface-Unfolding.md` and `docs_for_drafters/04-3D-Surface-Unfolding.md`
- `docs/11-FAQ.md` and `docs/12-FAQ.md`
- `docs/11-Troubleshooting-Guide.md` and `docs_for_drafters/05-Troubleshooting-Guide.md`

## Source evidence that drove archival

- The root command in `mcp.json` starts `src/server.py`, a stdio MCP server.
- `src/server.py` registers seven tools; it does not create a Flask `app` or expose the documented HTTP routes.
- `tests/test_server.py` and `tests/unit/test_drawing_operations.py` import `src.server.app`, which is absent.
- Multiple planning documents reference files such as `src/enhanced_autocad.py`, `src/error_handling.py`, `src/development_tools/`, and planned test suites that do not exist at those paths.
- The adopted README and several guides reference `BarryMcAdams/AutoCAD_MCP`, while the maintained repository is `ahmetcemkaraca/AutoCAD_MCP`.
