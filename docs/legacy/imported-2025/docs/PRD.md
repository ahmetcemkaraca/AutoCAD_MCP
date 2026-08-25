## PRD.md

### Document Version
- **Version**: 2.0 (Updated for pyautocad, 3D emphasis, and specific utilities)
- **Date**: January 10, 2025
- **Author**: Barry Adams
- **Purpose**: This Product Requirements Document (PRD) provides a complete specification for the AutoCAD MCP Server, ensuring no gaps for AI agents. It incorporates pyautocad for COM interactions, focuses on 3D workflows, and details utilities for unfolding 3D entities (LSCM-based surface parameterization) and layout auto-dimensioning.

## Overview
### Product Description
The AutoCAD MCP Server enables AI-driven automation of AutoCAD 2025 via Python, with a focus on 3D operations. It exposes APIs for entity creation, manipulation, and advanced transformations, integrated with VS Code for script development. Key utilities include unfolding double-curvature surfaces into 2D patterns for CNC (using approximation algorithms) and placing 3D entities in layouts with automatic dimensioning.

### Target Users
CAD designers specializing in 3D modeling for manufacturing/CNC.

### Key Benefits
- Provides experimental 3D-to-2D transformation algorithms (distortion measurement in development).
- Seamless VS Code integration for AI-assisted plugin creation.

### Scope
- In Scope: pyautocad-based APIs, 3D utilities, plugin framework.
- Out of Scope: macOS support, real-time multi-user.

### Assumptions and Dependencies
- AutoCAD 2025 full version running.
- Python 3.12 with pyautocad installed.

## Goals
### Business Goals
- Enable 50% faster 3D workflow automation.
### Technical Goals
- Research non-developable surface unfolding via LSCM algorithms.
### User Goals
- Create CNC-ready 2D patterns from 3D models effortlessly.

## User Stories
- As a designer, I want to unfold a double-curvature surface into a 2D polyline pattern to prepare for CNC cutting.
- As a designer, I want to place a 3D entity in a layout tab and auto-dimension it for documentation.

## Functional Requirements
### Core MCP Server Features
1. **Server Architecture**:
   - Flask-based, localhost:5001.
   - Use pyautocad for AutoCAD interactions (e.g., acad = Autocad()).

2. **Basic CAD Operations**:
   - Draw 3D primitives: AddLine, AddCircle, AddExtrudedSolid.

3. **Advanced CAD Operations**:
   - 3D Modeling: AddExtrudedSolid, AddRevolvedSolid, Union, Subtract.
   - Surface/Mesh: Add3DMesh, AddPolyFaceMesh, SectionSolid.

4. **Unfolding Utility (Mimicking SmartUnfold)**:
   - Endpoint: POST /unfold_surface: {'entity_id': int, 'tolerance': float, 'method': 'triangulation'}.
   - Logic: Segment surface into triangles/strips (using NumPy/SciPy for mesh triangulation), calculate geodesic paths (via shortest path algorithms on graph representation), generate 2D polylines with minimal distortion.
   - Handle multi-surfaces: Merge into single contour.
   - Output: 2D pattern with annotations (e.g., fold lines); accuracy <0.1% area deviation.
   - Approximation: For non-developable surfaces, use least-squares conformal mapping or similar.

5. **Layout and Dimensioning Utility**:
   - Endpoint: POST /create_layout: {'entity_id': int, 'layout_name': str, 'scale': float}.
   - Create viewport, set 3D view, add associative dimensions (e.g., AddDimAligned) on visible edges.

6. **Plugin Framework**:
   - Register custom modules with GUI (Tkinter) for inputs, pre-programmed logic.

### Non-Functional Requirements
- Performance: <1s for unfolding simple surfaces.
- Reliability: Auto-reconnect; log to mcp.log.
- Testing: Mock AutoCAD for CI.

## Technical Specifications
- **API Example**: /unfold: JSON input/output.
- **Success Criteria**: Utilities produce accurate outputs matching video demo; 100% test success.