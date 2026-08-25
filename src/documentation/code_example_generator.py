"""
Code Example Generator for AutoCAD API Documentation.

Generates working code examples, interactive tutorials, and usage patterns
for AutoCAD automation functions.
"""

import ast
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import random

logger = logging.getLogger(__name__)


@dataclass
class CodeExample:
    """Represents a code example."""
    title: str
    description: str
    code: str
    language: str = "python"
    difficulty: str = "basic"  # basic, intermediate, advanced
    category: str = "general"
    prerequisites: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass
class ExampleTemplate:
    """Template for generating code examples."""
    name: str
    pattern: str
    variables: Dict[str, List[Any]] = field(default_factory=dict)
    description_template: str = ""
    category: str = "general"


class CodeExampleGenerator:
    """Generates comprehensive code examples for AutoCAD API."""
    
    def __init__(self):
        self.templates = self._initialize_templates()
        self.autocad_examples = self._initialize_autocad_examples()
        self.generated_examples: List[CodeExample] = []
    
    def _initialize_templates(self) -> Dict[str, ExampleTemplate]:
        """Initialize code example templates."""
        return {
            "basic_drawing": ExampleTemplate(
                name="basic_drawing",
                pattern="""
# {title}
from src.autocad_utils import AutoCADConnection

def {function_name}():
    \"\"\"
    {description}
    \"\"\"
    # Connect to AutoCAD
    acad = AutoCADConnection()
    if not acad.connect():
        raise ConnectionError("Failed to connect to AutoCAD")
    
    try:
        # {operation_description}
        {main_operation}
        
        # Zoom to show the result
        acad.zoom_extents()
        
        print("✓ {success_message}")
        
    except Exception as e:
        print(f"✗ Error: {{e}}")
    finally:
        acad.disconnect()

if __name__ == "__main__":
    {function_name}()
""",
                variables={
                    "shapes": ["line", "circle", "rectangle", "polygon"],
                    "operations": ["create", "draw", "generate"],
                    "modifiers": ["simple", "complex", "custom", "parametric"]
                },
                description_template="Create a {modifier} {shape} in AutoCAD using automation",
                category="Drawing"
            ),
            
            "batch_processing": ExampleTemplate(
                name="batch_processing",
                pattern="""
# {title}
from src.autocad_utils import AutoCADConnection
import time

def {function_name}():
    \"\"\"
    {description}
    \"\"\"
    acad = AutoCADConnection()
    if not acad.connect():
        raise ConnectionError("Failed to connect to AutoCAD")
    
    try:
        print("Starting batch processing...")
        
        # Process multiple items
        {batch_items}
        
        for i, item in enumerate(items, 1):
            print(f"Processing item {{i}}/{{len(items)}}: {{item}}")
            
            {processing_operation}
            
            # Small delay to see progress
            time.sleep(0.1)
        
        print(f"✓ Successfully processed {{len(items)}} items")
        acad.zoom_extents()
        
    except Exception as e:
        print(f"✗ Batch processing failed: {{e}}")
    finally:
        acad.disconnect()

if __name__ == "__main__":
    {function_name}()
""",
                variables={
                    "batch_types": ["shapes", "layers", "blocks", "dimensions"],
                    "counts": [5, 10, 20, 50]
                },
                description_template="Batch process {count} {batch_type} in AutoCAD",
                category="Automation"
            ),
            
            "3d_modeling": ExampleTemplate(
                name="3d_modeling",
                pattern="""
# {title}
from src.autocad_utils import AutoCADConnection

def {function_name}():
    \"\"\"
    {description}
    \"\"\"
    acad = AutoCADConnection()
    if not acad.connect():
        raise ConnectionError("Failed to connect to AutoCAD")
    
    try:
        # Create base profile
        {profile_creation}
        
        # Create 3D solid
        {solid_creation}
        
        # Set 3D view
        acad.acad.ActiveDocument.SetVariable("VPOINT", [-1, -1, 1])
        acad.zoom_extents()
        
        print("✓ 3D model created successfully")
        
    except Exception as e:
        print(f"✗ 3D modeling failed: {{e}}")
    finally:
        acad.disconnect()

if __name__ == "__main__":
    {function_name}()
""",
                variables={
                    "solid_types": ["extrude", "revolve", "loft"],
                    "profiles": ["rectangle", "circle", "polygon", "custom"]
                },
                description_template="Create a 3D {solid_type} solid from a {profile} profile",
                category="3D Modeling"
            )
        }
    
    def _initialize_autocad_examples(self) -> Dict[str, List[CodeExample]]:
        """Initialize pre-built AutoCAD examples."""
        return {
            "basic": [
                CodeExample(
                    title="Hello AutoCAD",
                    description="Connect to AutoCAD and create a simple line",
                    code='''from src.autocad_utils import AutoCADConnection

def hello_autocad():
    """Create your first line in AutoCAD."""
    acad = AutoCADConnection()
    
    if acad.connect():
        # Create a line from origin to point (100, 100, 0)
        line_id = acad.create_line([0, 0, 0], [100, 100, 0])
        print(f"Created line with ID: {line_id}")
        
        acad.zoom_extents()
        acad.disconnect()
    else:
        print("Failed to connect to AutoCAD")

hello_autocad()''',
                    difficulty="basic",
                    category="Getting Started",
                    outputs=["Line drawn from (0,0,0) to (100,100,0)"],
                    notes=["Ensure AutoCAD is running before executing"]
                ),
                
                CodeExample(
                    title="Basic Shapes Collection",
                    description="Create a collection of basic geometric shapes",
                    code='''from src.autocad_utils import AutoCADConnection

def create_basic_shapes():
    """Create a collection of basic shapes in AutoCAD."""
    acad = AutoCADConnection()
    
    if not acad.connect():
        print("Failed to connect to AutoCAD")
        return
    
    try:
        # Create a rectangle
        acad.create_rectangle([0, 0, 0], [50, 30, 0])
        
        # Create a circle
        acad.create_circle([75, 15, 0], 15)
        
        # Create a line
        acad.create_line([0, 40, 0], [50, 40, 0])
        
        # Create another circle
        acad.create_circle([25, 60, 0], 10)
        
        print("✓ Created basic shapes collection")
        acad.zoom_extents()
        
    except Exception as e:
        print(f"Error creating shapes: {e}")
    finally:
        acad.disconnect()

create_basic_shapes()''',
                    difficulty="basic",
                    category="Drawing",
                    outputs=["Rectangle, circles, and line in AutoCAD"],
                    notes=["Shapes are positioned to avoid overlap", "Uses zoom extents to fit all shapes"]
                )
            ],
            
            "intermediate": [
                CodeExample(
                    title="Parametric Pattern Generator",
                    description="Generate patterns based on mathematical functions",
                    code='''import math
from src.autocad_utils import AutoCADConnection

def create_parametric_pattern():
    """Create a parametric spiral pattern."""
    acad = AutoCADConnection()
    
    if not acad.connect():
        print("Failed to connect to AutoCAD")
        return
    
    try:
        # Parameters for spiral
        num_points = 50
        max_radius = 100
        turns = 3
        
        points = []
        for i in range(num_points):
            angle = (i / num_points) * turns * 2 * math.pi
            radius = (i / num_points) * max_radius
            
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            points.append([x, y, 0])
        
        # Draw lines connecting the points
        for i in range(len(points) - 1):
            acad.create_line(points[i], points[i + 1])
        
        # Add circles at key points
        for i in range(0, len(points), 10):
            acad.create_circle(points[i], 2)
        
        print(f"✓ Created parametric spiral with {len(points)} points")
        acad.zoom_extents()
        
    except Exception as e:
        print(f"Error creating pattern: {e}")
    finally:
        acad.disconnect()

create_parametric_pattern()''',
                    difficulty="intermediate",
                    category="Parametric Design",
                    prerequisites=["Basic Python math operations", "Understanding of trigonometry"],
                    outputs=["Spiral pattern with connected lines and circles"],
                    notes=["Adjust num_points for pattern density", "Change turns for spiral tightness"]
                )
            ],
            
            "advanced": [
                CodeExample(
                    title="Automated Floor Plan Generator",
                    description="Generate a complete floor plan with rooms and annotations",
                    code='''from src.autocad_utils import AutoCADConnection
import random

def generate_floor_plan():
    """Generate an automated floor plan with multiple rooms."""
    acad = AutoCADConnection()
    
    if not acad.connect():
        print("Failed to connect to AutoCAD")
        return
    
    try:
        # Building parameters
        building_width = 200
        building_height = 150
        wall_thickness = 6
        
        # Create exterior walls
        create_exterior_walls(acad, building_width, building_height, wall_thickness)
        
        # Create interior rooms
        create_interior_rooms(acad, building_width, building_height, wall_thickness)
        
        # Add doors and windows
        add_openings(acad, building_width, building_height)
        
        print("✓ Generated complete floor plan")
        acad.zoom_extents()
        
    except Exception as e:
        print(f"Error generating floor plan: {e}")
    finally:
        acad.disconnect()

def create_exterior_walls(acad, width, height, thickness):
    """Create the exterior walls of the building."""
    # Outer walls
    acad.create_rectangle([0, 0, 0], [width, height, 0])
    # Inner walls (for wall thickness)
    acad.create_rectangle([thickness, thickness, 0], 
                         [width-thickness, height-thickness, 0])

def create_interior_rooms(acad, width, height, thickness):
    """Create interior room divisions."""
    # Vertical divider
    mid_x = width // 2
    acad.create_line([mid_x, thickness, 0], [mid_x, height-thickness, 0])
    
    # Horizontal dividers
    room_height = (height - 2*thickness) // 3
    for i in [1, 2]:
        y = thickness + i * room_height
        acad.create_line([thickness, y, 0], [width-thickness, y, 0])

def add_openings(acad, width, height):
    """Add doors and windows to the floor plan."""
    # Add door openings (represented by arcs)
    door_width = 20
    
    # Front door
    door_x = width // 2
    acad.create_line([door_x - door_width//2, 0, 0], 
                    [door_x + door_width//2, 0, 0])

generate_floor_plan()''',
                    difficulty="advanced",
                    category="Architectural Design",
                    prerequisites=["Understanding of architectural drawings", "Complex AutoCAD operations"],
                    outputs=["Complete floor plan with rooms, walls, and openings"],
                    notes=["Customizable building dimensions", "Extensible for more complex layouts"]
                )
            ]
        }
    
    def generate_examples_for_function(self, function_name: str, function_info: Dict[str, Any],
                                     num_examples: int = 3) -> List[CodeExample]:
        """Generate code examples for a specific function."""
        examples = []
        
        # Determine function category
        category = self._categorize_function(function_name, function_info)
        
        # Generate examples based on templates
        for i in range(num_examples):
            example = self._generate_from_template(function_name, function_info, category, i)
            if example:
                examples.append(example)
        
        # Add hand-crafted examples if available
        if category.lower() in self.autocad_examples:
            examples.extend(self.autocad_examples[category.lower()][:2])  # Limit to 2
        
        self.generated_examples.extend(examples)
        return examples
    
    def _categorize_function(self, function_name: str, function_info: Dict[str, Any]) -> str:
        """Categorize function to determine appropriate examples."""
        name_lower = function_name.lower()
        
        if any(keyword in name_lower for keyword in ['draw', 'create', 'add']):
            if any(keyword in name_lower for keyword in ['line', 'circle', 'rectangle']):
                return "basic"
            elif any(keyword in name_lower for keyword in ['extrude', 'revolve', '3d']):
                return "advanced"
            else:
                return "intermediate"
        elif any(keyword in name_lower for keyword in ['batch', 'process', 'multiple']):
            return "intermediate"
        elif any(keyword in name_lower for keyword in ['test', 'mock', 'validate']):
            return "basic"
        else:
            return "intermediate"
    
    def _generate_from_template(self, function_name: str, function_info: Dict[str, Any],
                              category: str, variation: int) -> Optional[CodeExample]:
        """Generate example from template."""
        # Select appropriate template
        template_key = "basic_drawing"
        if "batch" in function_name.lower():
            template_key = "batch_processing"
        elif any(keyword in function_name.lower() for keyword in ['extrude', 'revolve', '3d']):
            template_key = "3d_modeling"
        
        template = self.templates.get(template_key)
        if not template:
            return None
        
        # Generate variables for template
        variables = self._generate_template_variables(template, function_name, variation)
        
        # Fill template
        try:
            code = template.pattern.format(**variables)
            
            title = f"{variables.get('title', function_name)} Example {variation + 1}"
            description = variables.get('description', f"Example usage of {function_name}")
            
            return CodeExample(
                title=title,
                description=description,
                code=code.strip(),
                difficulty=category,
                category=template.category,
                notes=[f"Generated example for {function_name}"]
            )
        except Exception as e:
            logger.warning(f"Failed to generate example from template: {e}")
            return None
    
    def _generate_template_variables(self, template: ExampleTemplate, function_name: str,
                                   variation: int) -> Dict[str, str]:
        """Generate variables to fill template."""
        variables = {
            "function_name": f"example_{function_name.lower()}_{variation + 1}",
            "title": f"{function_name.replace('_', ' ').title()} Example"
        }
        
        # Add template-specific variables
        if template.name == "basic_drawing":
            shape = random.choice(template.variables.get("shapes", ["rectangle"]))
            modifier = random.choice(template.variables.get("modifiers", ["simple"]))
            
            variables.update({
                "modifier": modifier,
                "shape": shape,
                "description": template.description_template.format(modifier=modifier, shape=shape),
                "operation_description": f"Create a {modifier} {shape}",
                "main_operation": self._generate_drawing_operation(shape),
                "success_message": f"{shape} created successfully"
            })
        
        elif template.name == "batch_processing":
            batch_type = random.choice(template.variables.get("batch_types", ["shapes"]))
            count = random.choice(template.variables.get("counts", [10]))
            
            variables.update({
                "batch_type": batch_type,
                "count": count,
                "description": template.description_template.format(count=count, batch_type=batch_type),
                "batch_items": self._generate_batch_items(batch_type, count),
                "processing_operation": self._generate_batch_operation(batch_type)
            })
        
        elif template.name == "3d_modeling":
            solid_type = random.choice(template.variables.get("solid_types", ["extrude"]))
            profile = random.choice(template.variables.get("profiles", ["rectangle"]))
            
            variables.update({
                "solid_type": solid_type,
                "profile": profile,
                "description": template.description_template.format(solid_type=solid_type, profile=profile),
                "profile_creation": self._generate_profile_creation(profile),
                "solid_creation": self._generate_solid_creation(solid_type)
            })
        
        return variables
    
    def _generate_drawing_operation(self, shape: str) -> str:
        """Generate drawing operation code for shape."""
        operations = {
            "line": "line_id = acad.create_line([0, 0, 0], [100, 100, 0])",
            "circle": "circle_id = acad.create_circle([50, 50, 0], 25)",
            "rectangle": "rect_id = acad.create_rectangle([0, 0, 0], [100, 50, 0])",
            "polygon": """points = [[0, 0, 0], [50, 0, 0], [75, 25, 0], [50, 50, 0], [0, 50, 0]]
        for i in range(len(points)):
            next_i = (i + 1) % len(points)
            acad.create_line(points[i], points[next_i])"""
        }
        return operations.get(shape, f"# Create {shape}")
    
    def _generate_batch_items(self, batch_type: str, count: int) -> str:
        """Generate batch items code."""
        if batch_type == "shapes":
            return f"""items = ['circle', 'rectangle', 'line'] * {count // 3 + 1}
        items = items[:{count}]"""
        elif batch_type == "layers":
            return f"""items = [f'Layer_{{i+1:02d}}' for i in range({count})]"""
        else:
            return f"""items = [f'{batch_type}_{{i+1}}' for i in range({count})]"""
    
    def _generate_batch_operation(self, batch_type: str) -> str:
        """Generate batch operation code."""
        operations = {
            "shapes": """if item == 'circle':
                acad.create_circle([i*30, 0, 0], 10)
            elif item == 'rectangle':
                acad.create_rectangle([i*30, 20, 0], [i*30+20, 40, 0])
            else:  # line
                acad.create_line([i*30, 50, 0], [i*30+20, 60, 0])""",
            "layers": """# Create layer operation
            print(f"Processing layer: {item}")""",
        }
        return operations.get(batch_type, f"# Process {batch_type} item: {{item}}")
    
    def _generate_profile_creation(self, profile: str) -> str:
        """Generate profile creation code."""
        profiles = {
            "rectangle": """profile_points = [[0, 0, 0], [50, 0, 0], [50, 30, 0], [0, 30, 0], [0, 0, 0]]
        profile_id = acad.create_rectangle([0, 0, 0], [50, 30, 0])""",
            "circle": """profile_id = acad.create_circle([25, 25, 0], 20)""",
            "polygon": """profile_points = [[0, 0, 0], [30, 0, 0], [40, 20, 0], [20, 30, 0], [0, 20, 0]]
        # Create profile polygon
        for i in range(len(profile_points)-1):
            acad.create_line(profile_points[i], profile_points[i+1])
        profile_id = "polygon_profile\""""
        }
        return profiles.get(profile, f"# Create {profile} profile")
    
    def _generate_solid_creation(self, solid_type: str) -> str:
        """Generate solid creation code."""
        operations = {
            "extrude": """# Extrude the profile
        solid_id = acad.extrude_profile(profile_points, 25)""",
            "revolve": """# Revolve the profile around an axis
        axis_start = [0, 0, 0]
        axis_end = [0, 0, 100]
        solid_id = acad.revolve_profile(profile_points, axis_start, axis_end, 360)""",
            "loft": """# Create loft between profiles
        solid_id = acad.create_loft([profile_id])"""
        }
        return operations.get(solid_type, f"# Create {solid_type} solid")
    
    def generate_interactive_tutorial(self, topic: str, difficulty: str = "basic") -> Dict[str, Any]:
        """Generate an interactive tutorial for a specific topic."""
        tutorial_steps = []
        
        if topic.lower() == "basic_drawing":
            tutorial_steps = [
                {
                    "step": 1,
                    "title": "Connect to AutoCAD",
                    "description": "First, we need to establish a connection to AutoCAD",
                    "code": """from src.autocad_utils import AutoCADConnection

acad = AutoCADConnection()
if acad.connect():
    print("✓ Connected to AutoCAD!")
else:
    print("✗ Failed to connect. Make sure AutoCAD is running.")""",
                    "explanation": "This creates a connection object and attempts to connect to AutoCAD.",
                    "expected_output": "✓ Connected to AutoCAD!"
                },
                {
                    "step": 2,
                    "title": "Create Your First Line",
                    "description": "Let's create a simple line from point A to point B",
                    "code": """# Create a line from origin to point (100, 100, 0)
line_id = acad.create_line([0, 0, 0], [100, 100, 0])
print(f"Created line with ID: {line_id}")""",
                    "explanation": "The create_line method takes two 3D points as parameters.",
                    "expected_output": "Created line with ID: 12345"
                },
                {
                    "step": 3,
                    "title": "Add a Circle",
                    "description": "Now let's add a circle to our drawing",
                    "code": """# Create a circle at center (50, 50) with radius 25
circle_id = acad.create_circle([50, 50, 0], 25)
print(f"Created circle with ID: {circle_id}")""",
                    "explanation": "The create_circle method needs a center point and radius.",
                    "expected_output": "Created circle with ID: 12346"
                },
                {
                    "step": 4,
                    "title": "Zoom to Fit",
                    "description": "Let's zoom out to see all our objects",
                    "code": """# Zoom to show all objects
acad.zoom_extents()
print("✓ Zoomed to show all objects")""",
                    "explanation": "zoom_extents adjusts the view to show all objects in the drawing.",
                    "expected_output": "✓ Zoomed to show all objects"
                },
                {
                    "step": 5,
                    "title": "Clean Up",
                    "description": "Always disconnect when finished",
                    "code": """# Disconnect from AutoCAD
acad.disconnect()
print("✓ Disconnected from AutoCAD")""",
                    "explanation": "Proper cleanup ensures resources are released.",
                    "expected_output": "✓ Disconnected from AutoCAD"
                }
            ]
        
        return {
            "topic": topic,
            "difficulty": difficulty,
            "title": f"Interactive {topic.replace('_', ' ').title()} Tutorial",
            "description": f"Learn {topic.replace('_', ' ')} step by step",
            "steps": tutorial_steps,
            "total_steps": len(tutorial_steps),
            "estimated_time": f"{len(tutorial_steps) * 2} minutes"
        }
    
    def generate_usage_patterns(self, functions: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Generate common usage patterns for functions."""
        patterns = {}
        
        for function_name in functions:
            function_patterns = []
            
            # Common patterns based on function type
            if "create" in function_name.lower() or "add" in function_name.lower():
                function_patterns.extend([
                    {
                        "pattern_name": "Basic Usage",
                        "description": f"Simple usage of {function_name}",
                        "code_template": f"""result = {function_name}({{parameters}})
if result:
    print(f"Success: {{result}}")
else:
    print("Operation failed")""",
                        "use_case": "Quick object creation"
                    },
                    {
                        "pattern_name": "Error Handling",
                        "description": f"Robust usage with error handling",
                        "code_template": f"""try:
    result = {function_name}({{parameters}})
    print(f"Created successfully: {{result}}")
except Exception as e:
    print(f"Error: {{e}}")
    # Handle error appropriately""",
                        "use_case": "Production code with error handling"
                    },
                    {
                        "pattern_name": "Batch Processing",
                        "description": f"Using {function_name} in batch operations",
                        "code_template": f"""results = []
for item in batch_items:
    try:
        result = {function_name}(item)
        results.append(result)
    except Exception as e:
        print(f"Failed to process {{item}}: {{e}}")

print(f"Processed {{len(results)}}/{{len(batch_items)}} items")""",
                        "use_case": "Processing multiple items"
                    }
                ])
            
            patterns[function_name] = function_patterns
        
        return patterns
    
    def export_examples(self, output_dir: str, format_type: str = "html") -> str:
        """Export generated examples to files."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        if format_type == "html":
            return self._export_html_examples(output_path)
        elif format_type == "markdown":
            return self._export_markdown_examples(output_path)
        elif format_type == "json":
            return self._export_json_examples(output_path)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
    
    def _export_html_examples(self, output_path: Path) -> str:
        """Export examples as HTML."""
        html_file = output_path / "code_examples.html"
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AutoCAD Code Examples</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.1/themes/prism.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.1/components/prism-core.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.1/components/prism-python.min.js"></script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
        .container {{ max-width: 1000px; margin: 0 auto; padding: 20px; }}
        .example {{ margin-bottom: 40px; border: 1px solid #e1e4e8; border-radius: 6px; }}
        .example-header {{ background: #f6f8fa; padding: 15px; border-bottom: 1px solid #e1e4e8; }}
        .example-content {{ padding: 20px; }}
        .difficulty {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; color: white; }}
        .basic {{ background: #28a745; }}
        .intermediate {{ background: #ffc107; color: black; }}
        .advanced {{ background: #dc3545; }}
        .copy-btn {{ float: right; padding: 5px 10px; cursor: pointer; }}
        pre {{ max-height: 400px; overflow-y: auto; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>AutoCAD Code Examples</h1>
        <p>Collection of working code examples for AutoCAD automation.</p>
        
        {self._generate_html_examples()}
    </div>
    
    <script>
        function copyCode(button) {{
            const code = button.parentElement.nextElementSibling.querySelector('code');
            navigator.clipboard.writeText(code.textContent);
            button.textContent = 'Copied!';
            setTimeout(() => button.textContent = 'Copy', 2000);
        }}
    </script>
</body>
</html>"""
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Exported HTML examples: {html_file}")
        return str(html_file)
    
    def _generate_html_examples(self) -> str:
        """Generate HTML for all examples."""
        html_parts = []
        
        # Group examples by category
        categories = {}
        for example in self.generated_examples:
            category = example.category
            if category not in categories:
                categories[category] = []
            categories[category].append(example)
        
        for category, examples in categories.items():
            html_parts.append(f'<h2>{category}</h2>')
            
            for example in examples:
                html_parts.append(f'''
<div class="example">
    <div class="example-header">
        <h3>{example.title}</h3>
        <span class="difficulty {example.difficulty}">{example.difficulty.upper()}</span>
        <button class="copy-btn" onclick="copyCode(this)">Copy</button>
    </div>
    <div class="example-content">
        <p>{example.description}</p>
        <pre><code class="language-python">{example.code}</code></pre>
        {self._generate_example_notes(example)}
    </div>
</div>''')
        
        return '\\n'.join(html_parts)
    
    def _generate_example_notes(self, example: CodeExample) -> str:
        """Generate notes section for example."""
        if not example.notes and not example.outputs:
            return ""
        
        notes_html = ['<div class="example-notes">']
        
        if example.outputs:
            notes_html.append('<h4>Expected Output:</h4>')
            notes_html.append('<ul>')
            for output in example.outputs:
                notes_html.append(f'<li>{output}</li>')
            notes_html.append('</ul>')
        
        if example.notes:
            notes_html.append('<h4>Notes:</h4>')
            notes_html.append('<ul>')
            for note in example.notes:
                notes_html.append(f'<li>{note}</li>')
            notes_html.append('</ul>')
        
        notes_html.append('</div>')
        return '\\n'.join(notes_html)
    
    def _export_markdown_examples(self, output_path: Path) -> str:
        """Export examples as Markdown."""
        md_file = output_path / "code_examples.md"
        
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write("# AutoCAD Code Examples\\n\\n")
            
            # Group by category
            categories = {}
            for example in self.generated_examples:
                category = example.category
                if category not in categories:
                    categories[category] = []
                categories[category].append(example)
            
            for category, examples in categories.items():
                f.write(f"## {category}\\n\\n")
                
                for example in examples:
                    f.write(f"### {example.title}\\n\\n")
                    f.write(f"**Difficulty:** {example.difficulty.title()}\\n\\n")
                    f.write(f"{example.description}\\n\\n")
                    f.write(f"```python\\n{example.code}\\n```\\n\\n")
                    
                    if example.outputs:
                        f.write("**Expected Output:**\\n")
                        for output in example.outputs:
                            f.write(f"- {output}\\n")
                        f.write("\\n")
                    
                    if example.notes:
                        f.write("**Notes:**\\n")
                        for note in example.notes:
                            f.write(f"- {note}\\n")
                        f.write("\\n")
                    
                    f.write("---\\n\\n")
        
        logger.info(f"Exported Markdown examples: {md_file}")
        return str(md_file)
    
    def _export_json_examples(self, output_path: Path) -> str:
        """Export examples as JSON."""
        json_file = output_path / "code_examples.json"
        
        examples_data = {
            "metadata": {
                "total_examples": len(self.generated_examples),
                "categories": list(set(ex.category for ex in self.generated_examples)),
                "difficulties": list(set(ex.difficulty for ex in self.generated_examples))
            },
            "examples": [
                {
                    "title": example.title,
                    "description": example.description,
                    "code": example.code,
                    "language": example.language,
                    "difficulty": example.difficulty,
                    "category": example.category,
                    "prerequisites": example.prerequisites,
                    "outputs": example.outputs,
                    "notes": example.notes
                }
                for example in self.generated_examples
            ]
        }
        
        import json
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(examples_data, f, indent=2)
        
        logger.info(f"Exported JSON examples: {json_file}")
        return str(json_file)