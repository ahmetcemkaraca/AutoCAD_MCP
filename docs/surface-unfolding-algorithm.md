# Surface Unfolding Algorithm Specification

## Overview
This document provides the detailed mathematical and algorithmic specification for unfolding 3D surfaces to 2D patterns, implementing functionality similar to AutoCAD's SmartUnfold feature.

## Algorithm Goals
- **Accuracy**: <0.1% area deviation between 3D surface and 2D pattern
- **Performance**: <5 seconds for surfaces with <1000 faces
- **Robustness**: Handle both developable and non-developable surfaces
- **Manufacturability**: Generate patterns suitable for CNC cutting/laser cutting

## Mathematical Foundation

### Surface Classification
1. **Developable Surfaces**: Can be unfolded without distortion
   - Cylinders, cones, tangent surfaces
   - Gaussian curvature K = 0 everywhere
   
2. **Non-Developable Surfaces**: Require approximation
   - Spheres, tori, compound curved surfaces  
   - Gaussian curvature K ≠ 0

### Gaussian Curvature Calculation
For a parametric surface S(u,v) = [x(u,v), y(u,v), z(u,v)]:

```
K = (E*N - F²) / (E*G - F²)²

Where:
E = |∂S/∂u|²
F = (∂S/∂u) · (∂S/∂v)  
G = |∂S/∂v|²
N = det(∂²S/∂u², ∂²S/∂u∂v, ∂²S/∂v²)
```

## Core Algorithms

### Algorithm 1: Mesh Triangulation
Convert NURBS surfaces to triangular mesh for processing.

#### Input
- AutoCAD surface entity (NURBS, mesh, or solid face)
- Tolerance parameter (default: 0.01)

#### Process
```python
def triangulate_surface(surface_entity, tolerance=0.01):
    """
    Convert surface to triangular mesh using Delaunay triangulation.
    
    Returns:
        vertices: array of [x, y, z] coordinates
        faces: array of triangle vertex indices
        face_normals: normal vector for each face
    """
    
    # 1. Extract surface control points or tessellate
    points = extract_surface_points(surface_entity, tolerance)
    
    # 2. Project to best-fit plane for initial triangulation
    plane_normal, plane_center = fit_plane(points)
    projected_points = project_to_plane(points, plane_normal, plane_center)
    
    # 3. Perform 2D Delaunay triangulation
    triangulation = scipy.spatial.Delaunay(projected_points[:, :2])
    
    # 4. Map back to 3D and validate triangles
    vertices_3d = []
    faces = []
    face_normals = []
    
    for simplex in triangulation.simplices:
        # Validate triangle quality (aspect ratio, area)
        if is_valid_triangle(points[simplex]):
            faces.append(simplex)
            normal = compute_face_normal(points[simplex])
            face_normals.append(normal)
            
    return points, faces, face_normals
```

#### Quality Metrics
- **Aspect Ratio**: < 10:1 for numerical stability
- **Minimum Area**: > tolerance² to avoid degenerate triangles
- **Edge Length Variation**: < 5:1 within local neighborhoods

### Algorithm 2: Geodesic Path Calculation
Compute shortest paths on surface mesh for fold line generation.

#### Mathematical Basis
Geodesic distance on triangulated surface using Dijkstra's algorithm on dual graph.

```python
def compute_geodesic_distances(vertices, faces, source_vertex):
    """
    Compute geodesic distances from source vertex to all other vertices.
    
    Uses fast marching method on triangulated surface.
    """
    
    # 1. Build adjacency graph with edge weights = Euclidean distances
    graph = networkx.Graph()
    
    for face in faces:
        for i in range(3):
            v1, v2 = face[i], face[(i+1) % 3]
            edge_length = np.linalg.norm(vertices[v2] - vertices[v1])
            graph.add_edge(v1, v2, weight=edge_length)
    
    # 2. Compute shortest paths using Dijkstra
    distances = networkx.single_source_dijkstra_path_length(
        graph, source_vertex, weight='weight'
    )
    
    return distances

def find_cut_lines(vertices, faces, face_normals, curvature_threshold=0.1):
    """
    Identify natural cut lines based on curvature discontinuities.
    
    Returns paths along high-curvature edges for minimal distortion.
    """
    cut_edges = []
    
    # Find edges where adjacent faces have high normal deviation
    for edge in get_all_edges(faces):
        adjacent_faces = get_adjacent_faces(edge, faces)
        if len(adjacent_faces) == 2:
            f1, f2 = adjacent_faces
            angle = np.arccos(np.clip(
                np.dot(face_normals[f1], face_normals[f2]), -1, 1
            ))
            
            if angle > curvature_threshold:
                cut_edges.append(edge)
                
    return cut_edges
```

### Algorithm 3: 2D Flattening
Map 3D surface triangles to 2D plane with minimal distortion.

#### Approach: Least Squares Conformal Mapping (LSCM)
Minimize angle and area distortion simultaneously.

```python
def flatten_mesh_lscm(vertices, faces, boundary_vertices=None):
    """
    Flatten 3D mesh to 2D using Least Squares Conformal Mapping.
    
    Minimizes: ∫∫ |∇f|² + λ|∇g|² dA
    Where f, g are real and imaginary parts of conformal map.
    """
    
    n_vertices = len(vertices)
    
    # 1. Build Laplacian matrix for conformal energy
    L = build_conformal_laplacian(vertices, faces)
    
    # 2. Set boundary constraints (if specified)
    if boundary_vertices is None:
        boundary_vertices = find_boundary_vertices(faces)
    
    # Fix boundary to circle or rectangle
    boundary_2d = map_boundary_to_circle(boundary_vertices)
    
    # 3. Solve linear system for interior vertices
    interior_mask = np.ones(n_vertices, dtype=bool)
    interior_mask[boundary_vertices] = False
    
    # Solve: L[interior, interior] * x = -L[interior, boundary] * boundary_2d
    A = L[interior_mask][:, interior_mask]  
    b = -L[interior_mask][:, boundary_vertices] @ boundary_2d
    
    interior_coords_2d = scipy.sparse.linalg.spsolve(A, b)
    
    # 4. Combine boundary and interior coordinates
    coords_2d = np.zeros((n_vertices, 2))
    coords_2d[boundary_vertices] = boundary_2d
    coords_2d[interior_mask] = interior_coords_2d.reshape(-1, 2)
    
    return coords_2d

def build_conformal_laplacian(vertices, faces):
    """
    Build discrete Laplace-Beltrami operator with conformal weights.
    
    Uses cotangent weights: w_ij = (cot α_ij + cot β_ij) / 2
    Where α_ij, β_ij are angles opposite edge (i,j).
    """
    n = len(vertices)
    L = scipy.sparse.lil_matrix((n, n), dtype=complex)
    
    for face in faces:
        for i in range(3):
            vi = face[i]
            vj = face[(i+1) % 3] 
            vk = face[(i+2) % 3]
            
            # Compute cotangent weights
            edge_ij = vertices[vj] - vertices[vi]
            edge_ik = vertices[vk] - vertices[vi]
            edge_jk = vertices[vk] - vertices[vj]
            
            # Angle at vertex k opposite edge (i,j)
            cos_angle_k = np.dot(-edge_ik, -edge_jk) / (
                np.linalg.norm(edge_ik) * np.linalg.norm(edge_jk)
            )
            cot_k = cos_angle_k / np.sqrt(1 - cos_angle_k**2)
            
            # Add to Laplacian (complex weights for conformal mapping)
            weight = cot_k / 2
            L[vi, vj] += weight
            L[vj, vi] += weight
            L[vi, vi] -= weight
            L[vj, vj] -= weight
    
    return L.tocsr()
```

### Algorithm 4: Distortion Analysis
Quantify and minimize distortion in the unfolded pattern.

#### Distortion Metrics
1. **Area Distortion**: |A_3D - A_2D| / A_3D
2. **Angle Distortion**: RMS deviation of triangle angles
3. **Length Distortion**: Edge length variations

```python
def compute_distortion_metrics(vertices_3d, vertices_2d, faces):
    """
    Compute comprehensive distortion analysis.
    
    Returns:
        area_distortion: percentage area change per triangle
        angle_distortion: RMS angle deviation per triangle
        edge_distortion: edge length ratio statistics
    """
    
    n_faces = len(faces)
    area_distortion = np.zeros(n_faces)
    angle_distortion = np.zeros(n_faces)
    
    for i, face in enumerate(faces):
        # Get triangle vertices in 3D and 2D
        tri_3d = vertices_3d[face]
        tri_2d = vertices_2d[face]
        
        # Area distortion
        area_3d = triangle_area(tri_3d)
        area_2d = triangle_area(tri_2d)
        area_distortion[i] = abs(area_3d - area_2d) / area_3d
        
        # Angle distortion
        angles_3d = triangle_angles(tri_3d)
        angles_2d = triangle_angles(tri_2d) 
        angle_distortion[i] = np.sqrt(np.mean((angles_3d - angles_2d)**2))
    
    # Edge length distortion
    edge_ratios = []
    for edge in get_all_edges(faces):
        v1, v2 = edge
        len_3d = np.linalg.norm(vertices_3d[v2] - vertices_3d[v1])
        len_2d = np.linalg.norm(vertices_2d[v2] - vertices_2d[v1])
        edge_ratios.append(len_2d / len_3d)
    
    return {
        'area_distortion': area_distortion,
        'angle_distortion': angle_distortion, 
        'edge_distortion_stats': {
            'mean': np.mean(edge_ratios),
            'std': np.std(edge_ratios),
            'min': np.min(edge_ratios),
            'max': np.max(edge_ratios)
        }
    }
```

## Implementation Pipeline

### Step 1: Surface Analysis
```python
def analyze_surface(entity_id, tolerance=0.01):
    """
    Analyze surface properties to determine optimal unfolding strategy.
    """
    
    # Extract surface from AutoCAD
    acad = get_autocad_instance()
    entity = acad.doc.ObjectIdToObject(entity_id)
    
    # Classify surface type
    surface_type = classify_surface_type(entity)
    curvature_analysis = compute_curvature_distribution(entity, tolerance)
    
    # Determine unfolding method
    if curvature_analysis['max_gaussian_curvature'] < 1e-6:
        method = 'exact_developable'
    elif curvature_analysis['area_high_curvature'] < 0.1:
        method = 'triangulation_lscm'
    else:
        method = 'adaptive_segmentation'
        
    return {
        'surface_type': surface_type,
        'recommended_method': method,
        'curvature_stats': curvature_analysis,
        'estimated_distortion': estimate_unfolding_distortion(curvature_analysis)
    }
```

### Step 2: Mesh Generation
```python
def generate_unfolding_mesh(entity, tolerance, method):
    """
    Generate optimized mesh for unfolding based on analysis.
    """
    
    if method == 'exact_developable':
        return unfold_developable_surface(entity)
    elif method == 'triangulation_lscm':
        vertices, faces, normals = triangulate_surface(entity, tolerance)
        return flatten_mesh_lscm(vertices, faces)
    elif method == 'adaptive_segmentation':
        return unfold_with_segmentation(entity, tolerance)
```

### Step 3: Pattern Generation
```python
def generate_2d_pattern(vertices_2d, faces, cut_lines, fold_lines):
    """
    Generate final 2D pattern with manufacturing annotations.
    """
    
    # Create boundary polyline
    boundary = extract_boundary_polyline(vertices_2d, faces)
    
    # Add cut lines (solid lines)
    cut_geometry = []
    for cut_line in cut_lines:
        polyline_points = [vertices_2d[v] for v in cut_line]
        cut_geometry.append(create_polyline(polyline_points, line_type='continuous'))
    
    # Add fold lines (dashed lines)
    fold_geometry = []
    for fold_line in fold_lines:
        polyline_points = [vertices_2d[v] for v in fold_line]
        fold_geometry.append(create_polyline(polyline_points, line_type='dashed'))
    
    # Add dimension annotations
    dimensions = generate_pattern_dimensions(boundary, cut_geometry)
    
    # Add text labels
    labels = generate_pattern_labels(boundary, fold_lines, cut_lines)
    
    return {
        'boundary': boundary,
        'cut_lines': cut_geometry,
        'fold_lines': fold_geometry,
        'dimensions': dimensions,
        'labels': labels,
        'material_utilization': compute_material_efficiency(boundary)
    }
```

## Error Handling and Edge Cases

### Numerical Stability
- **Degenerate Triangles**: Skip triangles with area < tolerance²
- **Near-Singular Matrices**: Use regularization parameter λ = 1e-8
- **Boundary Conditions**: Ensure at least 3 boundary vertices for unique solution

### Convergence Criteria
- **LSCM Iteration**: Residual < 1e-6 or max 100 iterations
- **Distortion Optimization**: Improvement < 0.1% between iterations
- **Memory Management**: Chunk processing for >10,000 vertices

### Fallback Strategies
1. **High Curvature Surfaces**: Automatic segmentation at curvature maxima
2. **Complex Topology**: Multi-patch unfolding with seam optimization
3. **Numerical Failure**: Revert to simpler projection methods

## Performance Optimization

### Computational Complexity
- **Triangulation**: O(n log n) for n control points
- **Geodesic Computation**: O(n² log n) for n vertices
- **LSCM Solving**: O(n^1.5) for sparse matrices
- **Total Pipeline**: O(n²) for typical surfaces

### Memory Management
```python
def process_large_surface(entity, tolerance, max_vertices=5000):
    """
    Handle large surfaces with memory-efficient processing.
    """
    
    vertex_count = estimate_vertex_count(entity, tolerance)
    
    if vertex_count > max_vertices:
        # Adaptive mesh refinement
        patches = segment_surface_adaptively(entity, max_vertices)
        results = []
        
        for patch in patches:
            patch_result = unfold_surface_patch(patch, tolerance)
            results.append(patch_result)
            
        return merge_unfolded_patches(results)
    else:
        return unfold_surface_direct(entity, tolerance)
```

## Validation and Testing

### Unit Tests
- Developable surface accuracy (cylinder, cone)
- Distortion metrics for known surfaces
- Edge case handling (degenerate inputs)
- Performance benchmarks

### Integration Tests
- End-to-end AutoCAD workflow
- Various surface types from real models
- Manufacturing validation with cut patterns

### Acceptance Criteria
- **Accuracy**: <0.1% area deviation for test surfaces
- **Performance**: <5s for 1000-face surfaces
- **Robustness**: Handle 95% of real-world CAD surfaces
- **Manufacturability**: Patterns suitable for CNC/laser cutting