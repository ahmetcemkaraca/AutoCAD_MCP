"""
Pattern optimization and nesting algorithms for material efficiency.
Implements algorithms for optimal layout of unfolded patterns on material sheets.
"""

import logging
import numpy as np
import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Pattern:
    """Represents an unfolded pattern for nesting optimization."""
    id: str
    width: float
    height: float
    area: float
    vertices: List[Tuple[float, float]]  # 2D vertices defining pattern boundary
    rotation_allowed: bool = True
    material_grain_direction: Optional[str] = None  # 'horizontal', 'vertical', or None
    priority: float = 1.0  # Higher priority patterns placed first
    
    def __post_init__(self):
        """Calculate area if not provided."""
        if self.area == 0 and self.vertices:
            self.area = self._calculate_polygon_area()
    
    def _calculate_polygon_area(self) -> float:
        """Calculate area of polygon using shoelace formula."""
        if len(self.vertices) < 3:
            return self.width * self.height
        
        area = 0.0
        n = len(self.vertices)
        for i in range(n):
            j = (i + 1) % n
            area += self.vertices[i][0] * self.vertices[j][1]
            area -= self.vertices[j][0] * self.vertices[i][1]
        
        return abs(area) / 2.0
    
    def get_rotated_bounds(self, angle_degrees: float) -> Tuple[float, float]:
        """Get bounding box dimensions after rotation."""
        if not self.rotation_allowed:
            return self.width, self.height
        
        angle_rad = math.radians(angle_degrees)
        cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
        
        # Rotate bounding box corners
        corners = [
            (0, 0), (self.width, 0), 
            (self.width, self.height), (0, self.height)
        ]
        
        rotated_corners = [
            (x * cos_a - y * sin_a, x * sin_a + y * cos_a)
            for x, y in corners
        ]
        
        # Find new bounding box
        min_x = min(x for x, y in rotated_corners)
        max_x = max(x for x, y in rotated_corners)
        min_y = min(y for x, y in rotated_corners)
        max_y = max(y for x, y in rotated_corners)
        
        return max_x - min_x, max_y - min_y


@dataclass
class MaterialSheet:
    """Represents a material sheet for pattern nesting."""
    width: float
    height: float
    material_type: str = "generic"
    grain_direction: Optional[str] = None  # 'horizontal', 'vertical', or None
    cost_per_area: float = 1.0
    waste_factor: float = 0.05  # Expected waste percentage
    
    @property
    def area(self) -> float:
        """Total area of the material sheet."""
        return self.width * self.height
    
    @property
    def usable_area(self) -> float:
        """Usable area accounting for waste factor."""
        return self.area * (1.0 - self.waste_factor)


@dataclass
class PlacedPattern:
    """Represents a pattern placed on a material sheet."""
    pattern: Pattern
    x: float
    y: float
    rotation: float = 0.0  # Rotation angle in degrees
    
    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        """Get bounding box: (min_x, min_y, max_x, max_y)."""
        width, height = self.pattern.get_rotated_bounds(self.rotation)
        return self.x, self.y, self.x + width, self.y + height


class PatternNestingOptimizer:
    """
    Advanced pattern nesting optimizer using bin packing algorithms
    optimized for manufacturing material efficiency.
    """
    
    def __init__(self, material_sheets: List[MaterialSheet]):
        """
        Initialize the nesting optimizer.
        
        Args:
            material_sheets: List of available material sheet types
        """
        self.material_sheets = material_sheets
        self.algorithms = {
            'bottom_left_fill': self._bottom_left_fill,
            'best_fit_decreasing': self._best_fit_decreasing,
            'genetic_algorithm': self._genetic_algorithm_nest,
            'simulated_annealing': self._simulated_annealing_nest
        }
        
        logger.info(f"Pattern nesting optimizer initialized with {len(material_sheets)} material types")
    
    def optimize_nesting(self, patterns: List[Pattern], algorithm: str = 'best_fit_decreasing',
                        max_sheets: int = 10, rotation_angles: List[float] = [0, 90, 180, 270]) -> Dict[str, Any]:
        """
        Optimize pattern nesting to minimize material waste.
        
        Args:
            patterns: List of patterns to nest
            algorithm: Nesting algorithm to use
            max_sheets: Maximum number of material sheets to use
            rotation_angles: Allowed rotation angles for patterns
            
        Returns:
            Dictionary containing nesting optimization results
        """
        try:
            logger.info(f"Optimizing nesting for {len(patterns)} patterns using {algorithm}")
            
            if algorithm not in self.algorithms:
                raise ValueError(f"Unknown algorithm: {algorithm}. Available: {list(self.algorithms.keys())}")
            
            # Sort patterns by priority and size (largest first for better packing)
            sorted_patterns = sorted(patterns, key=lambda p: (p.priority, p.area), reverse=True)
            
            # Apply the selected algorithm
            nesting_result = self.algorithms[algorithm](sorted_patterns, max_sheets, rotation_angles)
            
            # Calculate optimization metrics
            metrics = self._calculate_optimization_metrics(nesting_result)
            
            result = {
                'success': True,
                'algorithm': algorithm,
                'patterns_count': len(patterns),
                'sheets_used': len(nesting_result['sheet_layouts']),
                'nesting_result': nesting_result,
                'optimization_metrics': metrics,
                'material_utilization': metrics['total_material_utilization'],
                'total_cost': metrics['total_material_cost']
            }
            
            logger.info(f"Nesting optimization completed: {metrics['total_material_utilization']:.1f}% utilization")
            
            return result
            
        except Exception as e:
            logger.error(f"Nesting optimization failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _bottom_left_fill(self, patterns: List[Pattern], max_sheets: int, 
                         rotation_angles: List[float]) -> Dict[str, Any]:
        """Bottom-left fill algorithm for pattern nesting."""
        sheet_layouts = []
        unplaced_patterns = patterns.copy()
        
        for sheet_idx in range(max_sheets):
            if not unplaced_patterns:
                break
                
            # Choose best material sheet for remaining patterns
            best_sheet = self._select_best_sheet(unplaced_patterns)
            placed_patterns = []
            
            # Try to place patterns using bottom-left strategy
            for pattern in unplaced_patterns.copy():
                best_placement = self._find_bottom_left_position(pattern, placed_patterns, 
                                                              best_sheet, rotation_angles)
                
                if best_placement:
                    placed_patterns.append(best_placement)
                    unplaced_patterns.remove(pattern)
            
            if placed_patterns:
                sheet_layouts.append({
                    'sheet': best_sheet,
                    'placed_patterns': placed_patterns,
                    'utilization': self._calculate_sheet_utilization(placed_patterns, best_sheet)
                })
        
        return {
            'sheet_layouts': sheet_layouts,
            'unplaced_patterns': unplaced_patterns,
            'algorithm_details': 'Bottom-left fill with rotation optimization'
        }
    
    def _best_fit_decreasing(self, patterns: List[Pattern], max_sheets: int,
                           rotation_angles: List[float]) -> Dict[str, Any]:
        """Best-fit decreasing algorithm for optimal space utilization."""
        sheet_layouts = []
        unplaced_patterns = patterns.copy()
        
        # Sort patterns by area (decreasing)
        unplaced_patterns.sort(key=lambda p: p.area, reverse=True)
        
        for sheet_idx in range(max_sheets):
            if not unplaced_patterns:
                break
                
            # Start with the best sheet for the largest remaining pattern
            best_sheet = self._select_best_sheet([unplaced_patterns[0]])
            placed_patterns = []
            
            # Place patterns using best-fit strategy
            for pattern in unplaced_patterns.copy():
                best_fit = self._find_best_fit_position(pattern, placed_patterns, 
                                                      best_sheet, rotation_angles)
                
                if best_fit and self._fits_on_sheet(best_fit, best_sheet):
                    placed_patterns.append(best_fit)
                    unplaced_patterns.remove(pattern)
            
            if placed_patterns:
                sheet_layouts.append({
                    'sheet': best_sheet,
                    'placed_patterns': placed_patterns,
                    'utilization': self._calculate_sheet_utilization(placed_patterns, best_sheet)
                })
        
        return {
            'sheet_layouts': sheet_layouts,
            'unplaced_patterns': unplaced_patterns,
            'algorithm_details': 'Best-fit decreasing with area optimization'
        }
    
    def _genetic_algorithm_nest(self, patterns: List[Pattern], max_sheets: int,
                              rotation_angles: List[float]) -> Dict[str, Any]:
        """Genetic algorithm for optimal pattern nesting (simplified implementation)."""
        # This is a simplified GA - full implementation would require more sophisticated operators
        logger.info("Using simplified genetic algorithm for nesting")
        
        # For now, fall back to best-fit decreasing with some randomization
        best_result = None
        best_utilization = 0.0
        
        # Try multiple random arrangements
        for generation in range(10):  # Limited generations for performance
            # Shuffle patterns for variation
            shuffled_patterns = patterns.copy()
            np.random.shuffle(shuffled_patterns)
            
            # Apply best-fit decreasing to shuffled patterns
            result = self._best_fit_decreasing(shuffled_patterns, max_sheets, rotation_angles)
            
            # Calculate total utilization
            total_utilization = self._calculate_total_utilization(result['sheet_layouts'])
            
            if total_utilization > best_utilization:
                best_utilization = total_utilization
                best_result = result
                best_result['algorithm_details'] = f'Genetic algorithm (generation {generation + 1})'
        
        return best_result or {'sheet_layouts': [], 'unplaced_patterns': patterns}
    
    def _simulated_annealing_nest(self, patterns: List[Pattern], max_sheets: int,
                                rotation_angles: List[float]) -> Dict[str, Any]:
        """Simulated annealing for pattern nesting optimization."""
        logger.info("Using simulated annealing for nesting optimization")
        
        # Start with a basic solution
        current_result = self._best_fit_decreasing(patterns, max_sheets, rotation_angles)
        current_cost = self._calculate_nesting_cost(current_result)
        
        best_result = current_result
        best_cost = current_cost
        
        # Simulated annealing parameters
        initial_temp = 100.0
        cooling_rate = 0.95
        min_temp = 1.0
        
        temperature = initial_temp
        
        for iteration in range(50):  # Limited iterations for performance
            if temperature < min_temp:
                break
            
            # Generate neighbor solution by swapping two patterns
            neighbor_result = self._generate_neighbor_solution(current_result, patterns, 
                                                             max_sheets, rotation_angles)
            neighbor_cost = self._calculate_nesting_cost(neighbor_result)
            
            # Accept or reject the neighbor
            cost_diff = neighbor_cost - current_cost
            
            if cost_diff < 0 or np.random.random() < np.exp(-cost_diff / temperature):
                current_result = neighbor_result
                current_cost = neighbor_cost
                
                if current_cost < best_cost:
                    best_result = current_result
                    best_cost = current_cost
            
            temperature *= cooling_rate
        
        best_result['algorithm_details'] = f'Simulated annealing (final cost: {best_cost:.2f})'
        return best_result
    
    def _select_best_sheet(self, patterns: List[Pattern]) -> MaterialSheet:
        """Select the most appropriate material sheet for given patterns."""
        if not patterns:
            return self.material_sheets[0]
        
        # Calculate total area needed
        total_area = sum(p.area for p in patterns)
        
        # Find smallest sheet that can fit all patterns (with margin)
        required_area = total_area * 1.2  # 20% margin for spacing
        
        suitable_sheets = [sheet for sheet in self.material_sheets if sheet.area >= required_area]
        
        if suitable_sheets:
            # Choose sheet with best cost per area ratio
            return min(suitable_sheets, key=lambda s: s.cost_per_area)
        else:
            # Choose largest available sheet
            return max(self.material_sheets, key=lambda s: s.area)
    
    def _find_bottom_left_position(self, pattern: Pattern, placed_patterns: List[PlacedPattern],
                                 sheet: MaterialSheet, rotation_angles: List[float]) -> Optional[PlacedPattern]:
        """Find the bottom-left position for a pattern."""
        best_placement = None
        best_waste = float('inf')
        
        for angle in rotation_angles:
            if not pattern.rotation_allowed and angle != 0:
                continue
            
            width, height = pattern.get_rotated_bounds(angle)
            
            # Try different positions (simplified - should use more sophisticated placement)
            for y in np.arange(0, sheet.height - height + 1, 5):  # 5mm grid
                for x in np.arange(0, sheet.width - width + 1, 5):
                    candidate = PlacedPattern(pattern, x, y, angle)
                    
                    if (self._fits_on_sheet(candidate, sheet) and 
                        not self._overlaps_with_placed(candidate, placed_patterns)):
                        
                        # Calculate waste (prefer bottom-left positions)
                        waste_score = y * 1000 + x  # Prioritize lower y, then lower x
                        
                        if waste_score < best_waste:
                            best_waste = waste_score
                            best_placement = candidate
                        
                        break  # Take first valid x position for this y
                
                if best_placement:
                    break  # Take first valid position
        
        return best_placement
    
    def _find_best_fit_position(self, pattern: Pattern, placed_patterns: List[PlacedPattern],
                              sheet: MaterialSheet, rotation_angles: List[float]) -> Optional[PlacedPattern]:
        """Find the best fitting position for a pattern."""
        best_placement = None
        best_fit_score = float('inf')
        
        for angle in rotation_angles:
            if not pattern.rotation_allowed and angle != 0:
                continue
            
            width, height = pattern.get_rotated_bounds(angle)
            
            # Search for positions with good fit
            for y in np.arange(0, sheet.height - height + 1, 2):  # 2mm grid for precision
                for x in np.arange(0, sheet.width - width + 1, 2):
                    candidate = PlacedPattern(pattern, x, y, angle)
                    
                    if (self._fits_on_sheet(candidate, sheet) and 
                        not self._overlaps_with_placed(candidate, placed_patterns)):
                        
                        # Calculate fit score (prefer tight packing)
                        fit_score = self._calculate_fit_score(candidate, placed_patterns, sheet)
                        
                        if fit_score < best_fit_score:
                            best_fit_score = fit_score
                            best_placement = candidate
        
        return best_placement
    
    def _fits_on_sheet(self, placed_pattern: PlacedPattern, sheet: MaterialSheet) -> bool:
        """Check if a placed pattern fits on the material sheet."""
        min_x, min_y, max_x, max_y = placed_pattern.bounds
        return max_x <= sheet.width and max_y <= sheet.height and min_x >= 0 and min_y >= 0
    
    def _overlaps_with_placed(self, candidate: PlacedPattern, placed_patterns: List[PlacedPattern]) -> bool:
        """Check if candidate pattern overlaps with any placed patterns."""
        cand_min_x, cand_min_y, cand_max_x, cand_max_y = candidate.bounds
        
        for placed in placed_patterns:
            placed_min_x, placed_min_y, placed_max_x, placed_max_y = placed.bounds
            
            # Check for overlap with small margin
            margin = 1.0  # 1mm margin between patterns
            if not (cand_max_x + margin <= placed_min_x or 
                   placed_max_x + margin <= cand_min_x or
                   cand_max_y + margin <= placed_min_y or 
                   placed_max_y + margin <= cand_min_y):
                return True
        
        return False
    
    def _calculate_fit_score(self, candidate: PlacedPattern, placed_patterns: List[PlacedPattern],
                           sheet: MaterialSheet) -> float:
        """Calculate how well a pattern fits with existing patterns."""
        min_x, min_y, max_x, max_y = candidate.bounds
        
        # Prefer positions that minimize wasted space
        score = 0.0
        
        # Distance from bottom-left corner (prefer closer)
        score += min_x + min_y
        
        # Distance from existing patterns (prefer closer packing)
        if placed_patterns:
            min_distance = float('inf')
            for placed in placed_patterns:
                p_min_x, p_min_y, p_max_x, p_max_y = placed.bounds
                
                # Calculate minimum distance between patterns
                dx = max(0, max(min_x - p_max_x, p_min_x - max_x))
                dy = max(0, max(min_y - p_max_y, p_min_y - max_y))
                distance = math.sqrt(dx*dx + dy*dy)
                
                min_distance = min(min_distance, distance)
            
            score += min_distance * 10  # Encourage tight packing
        
        return score
    
    def _calculate_sheet_utilization(self, placed_patterns: List[PlacedPattern], 
                                   sheet: MaterialSheet) -> float:
        """Calculate material utilization for a sheet."""
        if not placed_patterns:
            return 0.0
        
        total_pattern_area = sum(p.pattern.area for p in placed_patterns)
        return (total_pattern_area / sheet.area) * 100.0
    
    def _calculate_total_utilization(self, sheet_layouts: List[Dict[str, Any]]) -> float:
        """Calculate overall material utilization across all sheets."""
        if not sheet_layouts:
            return 0.0
        
        total_pattern_area = 0.0
        total_sheet_area = 0.0
        
        for layout in sheet_layouts:
            total_pattern_area += sum(p.pattern.area for p in layout['placed_patterns'])
            total_sheet_area += layout['sheet'].area
        
        return (total_pattern_area / total_sheet_area) * 100.0 if total_sheet_area > 0 else 0.0
    
    def _calculate_nesting_cost(self, nesting_result: Dict[str, Any]) -> float:
        """Calculate total cost of a nesting solution."""
        total_cost = 0.0
        
        for layout in nesting_result.get('sheet_layouts', []):
            sheet_cost = layout['sheet'].area * layout['sheet'].cost_per_area
            utilization_penalty = (100.0 - layout['utilization']) * 0.01  # Penalty for waste
            total_cost += sheet_cost + utilization_penalty
        
        # Add penalty for unplaced patterns
        unplaced_penalty = len(nesting_result.get('unplaced_patterns', [])) * 1000
        total_cost += unplaced_penalty
        
        return total_cost
    
    def _generate_neighbor_solution(self, current_result: Dict[str, Any], all_patterns: List[Pattern],
                                  max_sheets: int, rotation_angles: List[float]) -> Dict[str, Any]:
        """Generate a neighbor solution for simulated annealing."""
        # Simple neighbor generation: randomly swap two patterns and re-optimize
        patterns_copy = all_patterns.copy()
        
        if len(patterns_copy) >= 2:
            # Randomly swap two patterns
            i, j = np.random.choice(len(patterns_copy), 2, replace=False)
            patterns_copy[i], patterns_copy[j] = patterns_copy[j], patterns_copy[i]
        
        # Re-apply best-fit decreasing algorithm
        return self._best_fit_decreasing(patterns_copy, max_sheets, rotation_angles)
    
    def _calculate_optimization_metrics(self, nesting_result: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive optimization metrics."""
        sheet_layouts = nesting_result.get('sheet_layouts', [])
        unplaced_patterns = nesting_result.get('unplaced_patterns', [])
        
        if not sheet_layouts:
            return {
                'total_material_utilization': 0.0,
                'total_material_cost': 0.0,
                'sheets_used': 0,
                'patterns_placed': 0,
                'patterns_unplaced': len(unplaced_patterns)
            }
        
        total_pattern_area = 0.0
        total_sheet_area = 0.0
        total_cost = 0.0
        patterns_placed = 0
        
        sheet_utilizations = []
        
        for layout in sheet_layouts:
            sheet = layout['sheet']
            placed_patterns = layout['placed_patterns']
            
            layout_pattern_area = sum(p.pattern.area for p in placed_patterns)
            layout_utilization = layout['utilization']
            
            total_pattern_area += layout_pattern_area
            total_sheet_area += sheet.area
            total_cost += sheet.area * sheet.cost_per_area
            patterns_placed += len(placed_patterns)
            sheet_utilizations.append(layout_utilization)
        
        return {
            'total_material_utilization': (total_pattern_area / total_sheet_area) * 100.0,
            'average_sheet_utilization': np.mean(sheet_utilizations),
            'min_sheet_utilization': np.min(sheet_utilizations),
            'max_sheet_utilization': np.max(sheet_utilizations),
            'total_material_cost': total_cost,
            'sheets_used': len(sheet_layouts),
            'patterns_placed': patterns_placed,
            'patterns_unplaced': len(unplaced_patterns),
            'total_pattern_area': total_pattern_area,
            'total_sheet_area': total_sheet_area,
            'material_waste': total_sheet_area - total_pattern_area,
            'waste_percentage': ((total_sheet_area - total_pattern_area) / total_sheet_area) * 100.0 if total_sheet_area > 0 else 0.0
        }


def create_patterns_from_unfolding_results(unfolding_results: List[Dict[str, Any]]) -> List[Pattern]:
    """
    Convert unfolding results to Pattern objects for nesting optimization.
    
    Args:
        unfolding_results: List of unfolding result dictionaries
        
    Returns:
        List of Pattern objects ready for nesting
    """
    patterns = []
    
    try:
        for i, result in enumerate(unfolding_results):
            if not result.get('success', False):
                logger.warning(f"Skipping failed unfolding result {i}")
                continue
            
            # Extract pattern dimensions
            if 'pattern_bounds' in result:
                bounds = result['pattern_bounds']
                min_pt = bounds['min']
                max_pt = bounds['max']
                width = max_pt[0] - min_pt[0]
                height = max_pt[1] - min_pt[1]
            elif 'pattern_size' in result:
                size = result['pattern_size']
                width = size[0]
                height = size[1] if len(size) > 1 else size[0]
            else:
                logger.warning(f"No pattern dimensions found in result {i}")
                continue
            
            # Create vertices from UV coordinates if available
            vertices = []
            if 'uv_coordinates' in result:
                vertices = [(coord[0], coord[1]) for coord in result['uv_coordinates']]
            else:
                # Create rectangular vertices
                vertices = [(0, 0), (width, 0), (width, height), (0, height)]
            
            # Calculate area
            area = width * height
            if 'distortion_metrics' in result and 'total_surface_area' in result['distortion_metrics']:
                area = result['distortion_metrics']['total_surface_area']
            
            # Determine if rotation is allowed based on distortion
            rotation_allowed = True
            if 'distortion_metrics' in result:
                max_distortion = result['distortion_metrics'].get('max_angle_distortion', 0)
                rotation_allowed = max_distortion < 10.0  # Don't rotate high-distortion patterns
            
            # Set priority based on method and quality
            priority = 1.0
            method = result.get('method', '').lower()
            if method == 'lscm':
                priority = 2.0  # Higher priority for LSCM patterns
            elif 'distortion_metrics' in result:
                if result['distortion_metrics'].get('max_angle_distortion', 0) < 1.0:
                    priority = 1.5  # Higher priority for low-distortion patterns
            
            pattern = Pattern(
                id=f"pattern_{i}_{method}",
                width=width,
                height=height,
                area=area,
                vertices=vertices,
                rotation_allowed=rotation_allowed,
                priority=priority
            )
            
            patterns.append(pattern)
            logger.info(f"Created pattern {pattern.id}: {width:.1f}x{height:.1f}mm, area={area:.1f}mm²")
    
    except Exception as e:
        logger.error(f"Failed to create patterns from unfolding results: {e}")
    
    return patterns


def optimize_material_usage(patterns: List[Pattern], material_sheets: List[MaterialSheet],
                          algorithm: str = 'best_fit_decreasing') -> Dict[str, Any]:
    """
    High-level function to optimize material usage for multiple patterns.
    
    Args:
        patterns: List of patterns to optimize
        material_sheets: Available material sheet types
        algorithm: Optimization algorithm to use
        
    Returns:
        Dictionary containing optimization results
    """
    try:
        logger.info(f"Optimizing material usage for {len(patterns)} patterns")
        
        if not patterns:
            return {'success': False, 'error': 'No patterns provided'}
        
        if not material_sheets:
            return {'success': False, 'error': 'No material sheets provided'}
        
        # Initialize optimizer
        optimizer = PatternNestingOptimizer(material_sheets)
        
        # Run optimization
        result = optimizer.optimize_nesting(patterns, algorithm=algorithm, max_sheets=10)
        
        if result['success']:
            logger.info(f"Material optimization completed: "
                       f"{result['optimization_metrics']['total_material_utilization']:.1f}% utilization, "
                       f"{result['sheets_used']} sheets used")
        
        return result
        
    except Exception as e:
        logger.error(f"Material usage optimization failed: {e}")
        return {'success': False, 'error': str(e)}