"""
Advanced algorithms module for AutoCAD MCP Server Phase 4.

This module contains sophisticated algorithms for:
- LSCM (Least Squares Conformal Mapping) surface unfolding
- Geodesic path calculation
- Surface curvature analysis
- Triangle mesh processing
"""

from .lscm import LSCMSolver
from .mesh_utils import extract_triangle_mesh, analyze_mesh_curvature
from .geodesic import calculate_geodesic_paths

__all__ = [
    'LSCMSolver',
    'extract_triangle_mesh', 
    'analyze_mesh_curvature',
    'calculate_geodesic_paths'
]