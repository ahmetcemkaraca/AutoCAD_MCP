"""
Geodesic path calculation for optimal fold line placement on 3D surfaces.
"""

import numpy as np
import heapq
import logging
from typing import List, Tuple, Dict, Any, Optional

logger = logging.getLogger(__name__)


def calculate_geodesic_distance_dijkstra(vertices: np.ndarray, triangles: np.ndarray, 
                                        source_vertex: int, target_vertex: Optional[int] = None) -> Dict[str, Any]:
    """
    Calculate geodesic distances from a source vertex using Dijkstra's algorithm on the mesh.
    
    Args:
        vertices: Nx3 array of vertex coordinates
        triangles: Mx3 array of triangle indices
        source_vertex: Index of source vertex
        target_vertex: Optional target vertex (if None, calculates distances to all vertices)
        
    Returns:
        Dictionary containing geodesic distances and paths
    """
    logger.info(f"Calculating geodesic distances from vertex {source_vertex}")
    
    try:
        n_vertices = len(vertices)
        
        # Build adjacency graph with edge weights as Euclidean distances
        adjacency = {i: [] for i in range(n_vertices)}
        
        for triangle in triangles:
            v0, v1, v2 = triangle
            
            # Add edges for each pair of vertices in the triangle
            edges = [(v0, v1), (v1, v2), (v2, v0)]
            
            for va, vb in edges:
                # Calculate Euclidean distance as edge weight
                distance = np.linalg.norm(vertices[va] - vertices[vb])
                
                # Add bidirectional edges
                adjacency[va].append((vb, distance))
                adjacency[vb].append((va, distance))
        
        # Remove duplicate edges and keep minimum distance
        for vertex in adjacency:
            edges_dict = {}
            for neighbor, distance in adjacency[vertex]:
                if neighbor not in edges_dict or distance < edges_dict[neighbor]:
                    edges_dict[neighbor] = distance
            
            adjacency[vertex] = list(edges_dict.items())
        
        # Dijkstra's algorithm
        distances = {i: float('inf') for i in range(n_vertices)}
        distances[source_vertex] = 0.0
        previous = {i: None for i in range(n_vertices)}
        
        # Priority queue: (distance, vertex)
        pq = [(0.0, source_vertex)]
        visited = set()
        
        while pq:
            current_dist, current_vertex = heapq.heappop(pq)
            
            if current_vertex in visited:
                continue
            
            visited.add(current_vertex)
            
            # Early termination if we only need distance to target
            if target_vertex is not None and current_vertex == target_vertex:
                break
            
            # Update distances to neighbors
            for neighbor, edge_weight in adjacency[current_vertex]:
                if neighbor not in visited:
                    new_distance = current_dist + edge_weight
                    
                    if new_distance < distances[neighbor]:
                        distances[neighbor] = new_distance
                        previous[neighbor] = current_vertex
                        heapq.heappush(pq, (new_distance, neighbor))
        
        # Reconstruct path if target specified
        path = None
        if target_vertex is not None and distances[target_vertex] != float('inf'):
            path = []
            current = target_vertex
            while current is not None:
                path.append(current)
                current = previous[current]
            path.reverse()
        
        result = {
            'distances': distances,
            'source_vertex': source_vertex,
            'target_vertex': target_vertex,
            'path': path,
            'path_length': distances[target_vertex] if target_vertex else None,
            'n_vertices_processed': len(visited)
        }
        
        logger.info(f"Geodesic calculation completed, processed {len(visited)} vertices")
        
        return result
        
    except Exception as e:
        logger.error(f"Geodesic distance calculation failed: {e}")
        return {'error': str(e)}


def calculate_geodesic_paths(vertices: np.ndarray, triangles: np.ndarray, 
                           key_vertices: List[int]) -> Dict[str, Any]:
    """
    Calculate geodesic paths between key vertices for fold line generation.
    
    Args:
        vertices: Nx3 array of vertex coordinates
        triangles: Mx3 array of triangle indices
        key_vertices: List of important vertex indices (corners, high curvature points)
        
    Returns:
        Dictionary containing geodesic paths between key vertices
    """
    logger.info(f"Calculating geodesic paths between {len(key_vertices)} key vertices")
    
    try:
        paths_matrix = {}
        all_paths = []
        
        # Calculate paths between all pairs of key vertices
        for i, source in enumerate(key_vertices):
            for j, target in enumerate(key_vertices):
                if i < j:  # Avoid duplicate paths
                    result = calculate_geodesic_distance_dijkstra(vertices, triangles, source, target)
                    
                    if 'error' not in result and result['path'] is not None:
                        path_info = {
                            'source': source,
                            'target': target,
                            'path': result['path'],
                            'length': result['path_length'],
                            'vertices': [vertices[v].tolist() for v in result['path']]
                        }
                        
                        paths_matrix[(source, target)] = path_info
                        all_paths.append(path_info)
        
        # Find optimal fold lines based on path analysis
        fold_lines = generate_fold_lines_from_paths(vertices, triangles, all_paths)
        
        return {
            'key_vertices': key_vertices,
            'paths_matrix': paths_matrix,
            'all_paths': all_paths,
            'fold_lines': fold_lines,
            'n_paths': len(all_paths)
        }
        
    except Exception as e:
        logger.error(f"Geodesic paths calculation failed: {e}")
        return {'error': str(e)}


def generate_fold_lines_from_paths(vertices: np.ndarray, triangles: np.ndarray, 
                                  geodesic_paths: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generate fold lines from geodesic paths based on curvature and manufacturing constraints.
    
    Args:
        vertices: Vertex coordinates
        triangles: Triangle connectivity
        geodesic_paths: List of geodesic path dictionaries
        
    Returns:
        List of fold line specifications
    """
    logger.info("Generating fold lines from geodesic paths...")
    
    try:
        fold_lines = []
        
        for path_info in geodesic_paths:
            path_vertices = path_info['path']
            path_length = path_info['length']
            
            if len(path_vertices) < 2:
                continue
            
            # Analyze path curvature to determine fold type
            path_curvatures = []
            for i in range(1, len(path_vertices) - 1):
                v_prev = vertices[path_vertices[i-1]]
                v_curr = vertices[path_vertices[i]]
                v_next = vertices[path_vertices[i+1]]
                
                # Calculate angle change (curvature indicator)
                edge1 = v_curr - v_prev
                edge2 = v_next - v_curr
                
                edge1_norm = np.linalg.norm(edge1)
                edge2_norm = np.linalg.norm(edge2)
                
                if edge1_norm > 1e-12 and edge2_norm > 1e-12:
                    cos_angle = np.clip(np.dot(edge1, edge2) / (edge1_norm * edge2_norm), -1, 1)
                    angle_change = np.pi - np.arccos(cos_angle)
                    path_curvatures.append(abs(angle_change))
                else:
                    path_curvatures.append(0.0)
            
            # Determine fold line properties
            mean_curvature = np.mean(path_curvatures) if path_curvatures else 0.0
            max_curvature = np.max(path_curvatures) if path_curvatures else 0.0
            
            # Classify fold type based on curvature
            if max_curvature > 0.5:  # High curvature
                fold_type = "mountain_fold"
                line_style = "dashed"
                fold_angle = np.degrees(max_curvature)
            elif mean_curvature > 0.1:  # Medium curvature
                fold_type = "valley_fold"
                line_style = "dotted"
                fold_angle = np.degrees(mean_curvature)
            else:  # Low curvature
                fold_type = "score_line"
                line_style = "solid"
                fold_angle = np.degrees(mean_curvature)
            
            # Create fold line specification
            fold_line = {
                'start_vertex': path_vertices[0],
                'end_vertex': path_vertices[-1],
                'start_coord': vertices[path_vertices[0]].tolist(),
                'end_coord': vertices[path_vertices[-1]].tolist(),
                'path_vertices': path_vertices,
                'path_coordinates': [vertices[v].tolist() for v in path_vertices],
                'length': path_length,
                'fold_type': fold_type,
                'fold_angle': fold_angle,
                'line_style': line_style,
                'mean_curvature': mean_curvature,
                'max_curvature': max_curvature,
                'manufacturing_priority': 1.0 if max_curvature > 0.3 else 0.5
            }
            
            fold_lines.append(fold_line)
        
        # Sort fold lines by manufacturing priority
        fold_lines.sort(key=lambda x: x['manufacturing_priority'], reverse=True)
        
        logger.info(f"Generated {len(fold_lines)} fold lines from geodesic paths")
        
        return fold_lines
        
    except Exception as e:
        logger.error(f"Fold line generation failed: {e}")
        return []


def find_key_vertices_for_folding(vertices: np.ndarray, triangles: np.ndarray, 
                                 curvature_analysis: Dict[str, Any]) -> List[int]:
    """
    Identify key vertices that should be connected by fold lines.
    
    Args:
        vertices: Vertex coordinates
        triangles: Triangle connectivity  
        curvature_analysis: Results from mesh curvature analysis
        
    Returns:
        List of key vertex indices
    """
    logger.info("Finding key vertices for fold line placement...")
    
    try:
        n_vertices = len(vertices)
        key_vertices = []
        
        # Get curvature data
        vertex_curvatures = np.array(curvature_analysis.get('vertex_curvatures', []))
        
        if len(vertex_curvatures) != n_vertices:
            logger.warning("Curvature data size mismatch, using geometric analysis")
            vertex_curvatures = np.zeros(n_vertices)
        
        # Find high curvature vertices
        curvature_threshold = np.percentile(vertex_curvatures, 90)  # Top 10% curvature
        high_curvature_vertices = np.where(vertex_curvatures > curvature_threshold)[0]
        
        # Find boundary vertices (if mesh has boundary)
        boundary_vertices = find_boundary_vertices(triangles, n_vertices)
        
        # Find corner vertices (boundary vertices with high curvature)
        corner_vertices = []
        for vertex in boundary_vertices:
            if vertex < len(vertex_curvatures) and vertex_curvatures[vertex] > curvature_threshold:
                corner_vertices.append(vertex)
        
        # Combine all key vertex types
        key_vertices.extend(high_curvature_vertices[:10])  # Limit high curvature vertices
        key_vertices.extend(corner_vertices)
        key_vertices.extend(boundary_vertices[::max(1, len(boundary_vertices)//4)])  # Sample boundary
        
        # Remove duplicates and sort
        key_vertices = sorted(list(set(key_vertices)))
        
        # Limit total number of key vertices for performance
        if len(key_vertices) > 20:
            # Keep vertices with highest curvature
            curvature_scores = [vertex_curvatures[v] if v < len(vertex_curvatures) else 0 
                              for v in key_vertices]
            sorted_indices = np.argsort(curvature_scores)[::-1]
            key_vertices = [key_vertices[i] for i in sorted_indices[:20]]
        
        logger.info(f"Selected {len(key_vertices)} key vertices for folding analysis")
        
        return key_vertices
        
    except Exception as e:
        logger.error(f"Key vertex finding failed: {e}")
        return []


def find_boundary_vertices(triangles: np.ndarray, n_vertices: int) -> List[int]:
    """
    Find vertices that lie on the boundary of the mesh.
    
    Args:
        triangles: Triangle connectivity array
        n_vertices: Total number of vertices
        
    Returns:
        List of boundary vertex indices
    """
    # Build edge adjacency count
    edge_count = {}
    
    for triangle in triangles:
        for i in range(3):
            v1 = triangle[i]
            v2 = triangle[(i + 1) % 3]
            
            # Create canonical edge (smaller index first)
            edge = tuple(sorted([v1, v2]))
            
            if edge in edge_count:
                edge_count[edge] += 1
            else:
                edge_count[edge] = 1
    
    # Find boundary edges (appear only once)
    boundary_vertices = set()
    for edge, count in edge_count.items():
        if count == 1:
            boundary_vertices.update(edge)
    
    return sorted(list(boundary_vertices))