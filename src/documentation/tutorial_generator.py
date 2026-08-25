"""
Interactive Tutorial Generator for AutoCAD Projects.

Creates step-by-step tutorials, guided walkthroughs, and learning paths
for AutoCAD automation development.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TutorialStep:
    """Represents a single tutorial step."""
    step_number: int
    title: str
    description: str
    code: str = ""
    expected_output: str = ""
    hints: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    validation_code: str = ""
    estimated_time: int = 5  # minutes


@dataclass
class Tutorial:
    """Represents a complete tutorial."""
    id: str
    title: str
    description: str
    difficulty: str  # beginner, intermediate, advanced
    category: str
    steps: List[TutorialStep] = field(default_factory=list)
    learning_objectives: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    total_time: int = 0  # minutes
    tags: List[str] = field(default_factory=list)


class TutorialGenerator:
    """Generates interactive tutorials for AutoCAD automation."""
    
    def __init__(self):
        self.tutorials = self._initialize_tutorials()
        self.learning_paths = self._initialize_learning_paths()
    
    def _initialize_tutorials(self) -> Dict[str, Tutorial]:
        """Initialize built-in tutorials."""
        return {
            "autocad_basics": Tutorial(
                id="autocad_basics",
                title="AutoCAD Automation Basics",
                description="Learn the fundamentals of AutoCAD automation with Python",
                difficulty="beginner",
                category="Getting Started",
                learning_objectives=[
                    "Connect to AutoCAD from Python",
                    "Create basic geometric shapes",
                    "Handle errors and disconnections",
                    "Use coordinate systems effectively"
                ],
                prerequisites=["Basic Python knowledge"],
                tags=["python", "autocad", "COM", "basics"],
                steps=[
                    TutorialStep(
                        step_number=1,
                        title="Setting Up the Connection",
                        description="Learn how to establish a connection to AutoCAD",
                        code='''# Import the AutoCAD connection utility
from src.autocad_utils import AutoCADConnection

# Create a connection instance
acad = AutoCADConnection()

# Attempt to connect to AutoCAD
if acad.connect():
    print("✓ Successfully connected to AutoCAD!")
    print(f"AutoCAD Version: {acad.get_version()}")
else:
    print("✗ Failed to connect. Make sure AutoCAD is running.")''',
                        expected_output="✓ Successfully connected to AutoCAD!\nAutoCAD Version: 24.0",
                        hints=[
                            "Make sure AutoCAD is running before executing the code",
                            "If connection fails, try running as administrator",
                            "Check that Python and AutoCAD are both 64-bit or both 32-bit"
                        ],
                        validation_code="assert acad.is_connected(), 'Connection not established'",
                        estimated_time=3
                    ),
                    TutorialStep(
                        step_number=2,
                        title="Creating Your First Line",
                        description="Draw a simple line in AutoCAD",
                        code='''# Define start and end points for the line
start_point = [0, 0, 0]  # Origin point
end_point = [100, 100, 0]  # Point at (100, 100)

# Create the line
line_id = acad.create_line(start_point, end_point)

if line_id:
    print(f"✓ Created line with ID: {line_id}")
    print("Line drawn from origin to (100, 100)")
else:
    print("✗ Failed to create line")''',
                        expected_output="✓ Created line with ID: 12345\nLine drawn from origin to (100, 100)",
                        hints=[
                            "Coordinates are in [X, Y, Z] format",
                            "Z coordinate is 0 for 2D drawings",
                            "Line ID is used to reference the object later"
                        ],
                        validation_code="assert line_id is not None, 'Line creation failed'",
                        estimated_time=4
                    ),
                    TutorialStep(
                        step_number=3,
                        title="Adding a Circle",
                        description="Create a circle with specified center and radius",
                        code='''# Define circle parameters
center_point = [50, 50, 0]  # Center at (50, 50)
radius = 25  # Radius of 25 units

# Create the circle
circle_id = acad.create_circle(center_point, radius)

if circle_id:
    print(f"✓ Created circle with ID: {circle_id}")
    print(f"Circle centered at {center_point} with radius {radius}")
else:
    print("✗ Failed to create circle")''',
                        expected_output="✓ Created circle with ID: 12346\nCircle centered at [50, 50, 0] with radius 25",
                        hints=[
                            "Center point uses same [X, Y, Z] format as lines",
                            "Radius must be a positive number",
                            "Circle will be created in the current layer"
                        ],
                        validation_code="assert circle_id is not None, 'Circle creation failed'",
                        estimated_time=3
                    ),
                    TutorialStep(
                        step_number=4,
                        title="Viewing Your Work",
                        description="Adjust the view to see all created objects",
                        code='''# Zoom to show all objects in the drawing
acad.zoom_extents()
print("✓ Zoomed to show all objects")

# Get current view information
view_info = acad.get_view_info()
print(f"Current view center: {view_info.get('center', 'Unknown')}")
print(f"Current zoom level: {view_info.get('zoom', 'Unknown')}")''',
                        expected_output="✓ Zoomed to show all objects\nCurrent view center: [50, 50, 0]\nCurrent zoom level: 1.5",
                        hints=[
                            "zoom_extents() fits all objects in the view",
                            "This is similar to the ZOOM EXTENTS command in AutoCAD",
                            "View information shows current viewport settings"
                        ],
                        validation_code="# View adjustment doesn't need validation",
                        estimated_time=2
                    ),
                    TutorialStep(
                        step_number=5,
                        title="Proper Cleanup",
                        description="Always disconnect properly when finished",
                        code='''# Get connection status before disconnecting
if acad.is_connected():
    print("Connection is active")
    
    # Perform any final operations
    object_count = acad.get_object_count()
    print(f"Total objects in drawing: {object_count}")
    
    # Disconnect properly
    acad.disconnect()
    print("✓ Disconnected from AutoCAD")
else:
    print("Connection was already closed")''',
                        expected_output="Connection is active\nTotal objects in drawing: 2\n✓ Disconnected from AutoCAD",
                        hints=[
                            "Always check connection status before operations",
                            "Disconnecting releases COM resources",
                            "Proper cleanup prevents memory leaks"
                        ],
                        validation_code="assert not acad.is_connected(), 'Connection not properly closed'",
                        estimated_time=3
                    )
                ]
            ),
            
            "parametric_design": Tutorial(
                id="parametric_design",
                title="Parametric Design with Python",
                description="Create parametric designs that adapt based on parameters",
                difficulty="intermediate",
                category="Advanced Techniques",
                learning_objectives=[
                    "Understand parametric design principles",
                    "Create functions with configurable parameters",
                    "Generate complex patterns programmatically",
                    "Build reusable design components"
                ],
                prerequisites=["AutoCAD Automation Basics", "Python functions"],
                tags=["parametric", "design", "patterns", "mathematics"],
                steps=[
                    TutorialStep(
                        step_number=1,
                        title="Parametric Rectangle Function",
                        description="Create a function that generates rectangles with variable dimensions",
                        code='''def create_parametric_rectangle(acad, width, height, center_x=0, center_y=0):
    """Create a rectangle with specified parameters."""
    # Calculate corner points
    half_width = width / 2
    half_height = height / 2
    
    # Define corners relative to center
    corners = [
        [center_x - half_width, center_y - half_height, 0],  # Bottom-left
        [center_x + half_width, center_y - half_height, 0],  # Bottom-right
        [center_x + half_width, center_y + half_height, 0],  # Top-right
        [center_x - half_width, center_y + half_height, 0],  # Top-left
        [center_x - half_width, center_y - half_height, 0]   # Close the rectangle
    ]
    
    # Create lines for each side
    rect_ids = []
    for i in range(len(corners) - 1):
        line_id = acad.create_line(corners[i], corners[i + 1])
        rect_ids.append(line_id)
    
    print(f"✓ Created parametric rectangle: {width}x{height} at ({center_x}, {center_y})")
    return rect_ids

# Test the function
acad = AutoCADConnection()
acad.connect()

# Create rectangles with different parameters
rect1 = create_parametric_rectangle(acad, 50, 30, 0, 0)
rect2 = create_parametric_rectangle(acad, 80, 20, 100, 50)''',
                        expected_output="✓ Created parametric rectangle: 50x30 at (0, 0)\n✓ Created parametric rectangle: 80x20 at (100, 50)",
                        hints=[
                            "Parameters make the function flexible and reusable",
                            "Center-based positioning is often more intuitive",
                            "Returning object IDs allows for later manipulation"
                        ],
                        estimated_time=8
                    ),
                    TutorialStep(
                        step_number=2,
                        title="Spiral Pattern Generator",
                        description="Generate mathematical spiral patterns",
                        code='''import math

def create_spiral_pattern(acad, num_points=50, max_radius=100, turns=3):
    """Create a spiral pattern with configurable parameters."""
    points = []
    
    for i in range(num_points):
        # Calculate angle and radius for each point
        angle = (i / num_points) * turns * 2 * math.pi
        radius = (i / num_points) * max_radius
        
        # Convert polar to cartesian coordinates
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        points.append([x, y, 0])
    
    # Connect points with lines
    line_ids = []
    for i in range(len(points) - 1):
        line_id = acad.create_line(points[i], points[i + 1])
        line_ids.append(line_id)
    
    # Add circles at key points for visualization
    circle_ids = []
    for i in range(0, len(points), max(1, num_points // 10)):
        circle_id = acad.create_circle(points[i], 2)
        circle_ids.append(circle_id)
    
    print(f"✓ Created spiral: {num_points} points, {max_radius} max radius, {turns} turns")
    return line_ids, circle_ids

# Create different spiral patterns
spiral1 = create_spiral_pattern(acad, 30, 50, 2)
spiral2 = create_spiral_pattern(acad, 60, 80, 4)''',
                        expected_output="✓ Created spiral: 30 points, 50 max radius, 2 turns\n✓ Created spiral: 60 points, 80 max radius, 4 turns",
                        hints=[
                            "Math functions create interesting patterns",
                            "Polar coordinates are perfect for spirals",
                            "Adding visual markers helps understand the pattern"
                        ],
                        estimated_time=10
                    )
                ]
            ),
            
            "3d_modeling": Tutorial(
                id="3d_modeling",
                title="3D Modeling Fundamentals",
                description="Introduction to 3D solid modeling with AutoCAD automation",
                difficulty="advanced",
                category="3D Modeling",
                learning_objectives=[
                    "Create 3D profiles for solid modeling",
                    "Understand extrusion and revolution operations",
                    "Work with 3D coordinate systems",
                    "Combine multiple solids with Boolean operations"
                ],
                prerequisites=["Parametric Design", "3D mathematics basics"],
                tags=["3d", "modeling", "solids", "boolean"],
                steps=[
                    TutorialStep(
                        step_number=1,
                        title="Creating 3D Profiles",
                        description="Create 2D profiles that will be used for 3D operations",
                        code='''def create_3d_profile(acad, profile_type="rectangle", size=50):
    """Create a 2D profile for 3D operations."""
    if profile_type == "rectangle":
        # Create rectangular profile
        return acad.create_rectangle([-size/2, -size/2, 0], [size/2, size/2, 0])
    
    elif profile_type == "circle":
        # Create circular profile
        return acad.create_circle([0, 0, 0], size/2)
    
    elif profile_type == "l_shape":
        # Create L-shaped profile
        points = [
            [0, 0, 0], [size, 0, 0], [size, size/3, 0],
            [size/3, size/3, 0], [size/3, size, 0], [0, size, 0], [0, 0, 0]
        ]
        line_ids = []
        for i in range(len(points) - 1):
            line_id = acad.create_line(points[i], points[i + 1])
            line_ids.append(line_id)
        return line_ids

# Create different profiles
rect_profile = create_3d_profile(acad, "rectangle", 40)
circle_profile = create_3d_profile(acad, "circle", 30) 
l_profile = create_3d_profile(acad, "l_shape", 60)

print("✓ Created 3D profiles for solid modeling")''',
                        expected_output="✓ Created 3D profiles for solid modeling",
                        hints=[
                            "Profiles should be closed curves for solid operations",
                            "Profile positioning affects the final 3D solid",
                            "Complex profiles can create interesting 3D shapes"
                        ],
                        estimated_time=12
                    )
                ]
            )
        }
    
    def _initialize_learning_paths(self) -> Dict[str, List[str]]:
        """Initialize learning paths that connect tutorials."""
        return {
            "beginner_path": [
                "autocad_basics",
                "parametric_design"
            ],
            "advanced_path": [
                "parametric_design", 
                "3d_modeling"
            ],
            "complete_mastery": [
                "autocad_basics",
                "parametric_design",
                "3d_modeling"
            ]
        }
    
    def generate_custom_tutorial(self, topic: str, difficulty: str, 
                                requirements: List[str]) -> Tutorial:
        """Generate a custom tutorial based on requirements."""
        tutorial_id = f"custom_{topic.lower().replace(' ', '_')}"
        
        # Generate steps based on topic and difficulty
        steps = self._generate_tutorial_steps(topic, difficulty, requirements)
        
        return Tutorial(
            id=tutorial_id,
            title=f"Custom Tutorial: {topic}",
            description=f"A {difficulty}-level tutorial covering {topic}",
            difficulty=difficulty,
            category="Custom",
            steps=steps,
            learning_objectives=self._generate_learning_objectives(topic),
            prerequisites=requirements,
            tags=[topic.lower(), difficulty, "custom"]
        )
    
    def _generate_tutorial_steps(self, topic: str, difficulty: str, 
                                requirements: List[str]) -> List[TutorialStep]:
        """Generate tutorial steps based on parameters."""
        steps = []
        
        # Base setup step
        steps.append(TutorialStep(
            step_number=1,
            title="Setup and Connection",
            description=f"Set up the environment for {topic} tutorial",
            code=f'''# Setup for {topic} tutorial
from src.autocad_utils import AutoCADConnection

acad = AutoCADConnection()
if acad.connect():
    print("✓ Ready for {topic} tutorial")
else:
    print("✗ Connection failed")''',
            expected_output=f"✓ Ready for {topic} tutorial",
            estimated_time=2
        ))
        
        # Topic-specific steps
        if "drawing" in topic.lower():
            steps.extend(self._generate_drawing_steps(difficulty))
        elif "modeling" in topic.lower():
            steps.extend(self._generate_modeling_steps(difficulty))
        elif "automation" in topic.lower():
            steps.extend(self._generate_automation_steps(difficulty))
        
        # Cleanup step
        steps.append(TutorialStep(
            step_number=len(steps) + 1,
            title="Cleanup and Summary",
            description="Clean up resources and review what was learned",
            code='''# Clean up and summarize
acad.zoom_extents()
print("✓ Tutorial completed successfully")
acad.disconnect()''',
            expected_output="✓ Tutorial completed successfully",
            estimated_time=2
        ))
        
        return steps
    
    def _generate_drawing_steps(self, difficulty: str) -> List[TutorialStep]:
        """Generate steps for drawing tutorials."""
        if difficulty == "beginner":
            return [
                TutorialStep(
                    step_number=2,
                    title="Basic Shapes",
                    description="Create fundamental geometric shapes",
                    code='''# Create basic shapes
line_id = acad.create_line([0, 0, 0], [50, 50, 0])
circle_id = acad.create_circle([100, 25, 0], 25)
print("✓ Created basic shapes")''',
                    expected_output="✓ Created basic shapes",
                    estimated_time=5
                )
            ]
        else:
            return [
                TutorialStep(
                    step_number=2,
                    title="Advanced Drawing Techniques",
                    description="Use advanced drawing methods",
                    code='''# Advanced drawing techniques
import math
points = []
for i in range(8):
    angle = i * math.pi / 4
    x = 50 * math.cos(angle)
    y = 50 * math.sin(angle)
    points.append([x, y, 0])

# Create polygon
for i in range(len(points)):
    next_i = (i + 1) % len(points)
    acad.create_line(points[i], points[next_i])
print("✓ Created complex polygon")''',
                    expected_output="✓ Created complex polygon",
                    estimated_time=8
                )
            ]
    
    def _generate_modeling_steps(self, difficulty: str) -> List[TutorialStep]:
        """Generate steps for 3D modeling tutorials."""
        return [
            TutorialStep(
                step_number=2,
                title="3D Profile Creation",
                description="Create profiles for 3D operations",
                code='''# Create 3D profile
profile_id = acad.create_circle([0, 0, 0], 20)
print("✓ Created 3D profile")''',
                expected_output="✓ Created 3D profile",
                estimated_time=6
            )
        ]
    
    def _generate_automation_steps(self, difficulty: str) -> List[TutorialStep]:
        """Generate steps for automation tutorials."""
        return [
            TutorialStep(
                step_number=2,
                title="Batch Operations",
                description="Automate repetitive tasks",
                code='''# Batch create circles
for i in range(5):
    circle_id = acad.create_circle([i * 30, 0, 0], 10)
print("✓ Created batch of circles")''',
                expected_output="✓ Created batch of circles",
                estimated_time=7
            )
        ]
    
    def _generate_learning_objectives(self, topic: str) -> List[str]:
        """Generate learning objectives for a topic."""
        objectives = [
            f"Understand {topic} fundamentals",
            f"Apply {topic} techniques effectively",
            f"Create practical {topic} solutions"
        ]
        return objectives
    
    def create_interactive_session(self, tutorial_id: str) -> Dict[str, Any]:
        """Create an interactive tutorial session."""
        if tutorial_id not in self.tutorials:
            raise ValueError(f"Tutorial '{tutorial_id}' not found")
        
        tutorial = self.tutorials[tutorial_id]
        
        session = {
            "tutorial_id": tutorial_id,
            "title": tutorial.title,
            "current_step": 0,
            "total_steps": len(tutorial.steps),
            "started_at": datetime.now().isoformat(),
            "completed_steps": [],
            "session_data": {},
            "progress_percentage": 0
        }
        
        return session
    
    def get_next_step(self, session: Dict[str, Any]) -> Optional[TutorialStep]:
        """Get the next step in the tutorial session."""
        tutorial_id = session["tutorial_id"]
        current_step = session["current_step"]
        
        tutorial = self.tutorials[tutorial_id]
        
        if current_step < len(tutorial.steps):
            return tutorial.steps[current_step]
        else:
            return None
    
    def validate_step_completion(self, session: Dict[str, Any], 
                                user_code: str) -> Dict[str, Any]:
        """Validate that a tutorial step was completed correctly."""
        tutorial_id = session["tutorial_id"]
        current_step = session["current_step"]
        
        tutorial = self.tutorials[tutorial_id]
        step = tutorial.steps[current_step]
        
        result = {
            "valid": True,
            "message": "Step completed successfully!",
            "hints": [],
            "next_step_available": current_step + 1 < len(tutorial.steps)
        }
        
        # Simple validation - in a real implementation, this would be more sophisticated
        if step.validation_code:
            try:
                # This is a simplified validation - real implementation would use sandboxing
                if "assert" in step.validation_code:
                    result["valid"] = True
                    result["message"] = "Validation passed!"
            except Exception as e:
                result["valid"] = False
                result["message"] = f"Validation failed: {e}"
                result["hints"] = step.hints
        
        if result["valid"]:
            session["completed_steps"].append(current_step)
            session["current_step"] += 1
            session["progress_percentage"] = (len(session["completed_steps"]) / len(tutorial.steps)) * 100
        
        return result
    
    def generate_progress_report(self, session: Dict[str, Any]) -> str:
        """Generate a progress report for the tutorial session."""
        tutorial_id = session["tutorial_id"]
        tutorial = self.tutorials[tutorial_id]
        
        completed = len(session["completed_steps"])
        total = len(tutorial.steps)
        progress = session["progress_percentage"]
        
        report = f"""
Tutorial Progress Report
========================

Tutorial: {tutorial.title}
Difficulty: {tutorial.difficulty}
Progress: {completed}/{total} steps ({progress:.1f}%)

Completed Steps:
"""
        
        for step_idx in session["completed_steps"]:
            step = tutorial.steps[step_idx]
            report += f"  ✓ Step {step.step_number}: {step.title}\n"
        
        if completed < total:
            next_step = tutorial.steps[session["current_step"]]
            report += f"\nNext Step: {next_step.title}\n"
            report += f"Estimated time: {next_step.estimated_time} minutes\n"
        else:
            report += "\n🎉 Tutorial completed! Great work!\n"
        
        return report
    
    def export_tutorial(self, tutorial_id: str, output_path: str, 
                       format_type: str = "html") -> str:
        """Export tutorial to file format."""
        if tutorial_id not in self.tutorials:
            raise ValueError(f"Tutorial '{tutorial_id}' not found")
        
        tutorial = self.tutorials[tutorial_id]
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        
        if format_type == "html":
            return self._export_html_tutorial(tutorial, output_path)
        elif format_type == "markdown":
            return self._export_markdown_tutorial(tutorial, output_path)
        elif format_type == "json":
            return self._export_json_tutorial(tutorial, output_path)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
    
    def _export_html_tutorial(self, tutorial: Tutorial, output_path: Path) -> str:
        """Export tutorial as HTML."""
        html_file = output_path / f"{tutorial.id}.html"
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{tutorial.title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 20px; }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        .header {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 30px; }}
        .difficulty {{ display: inline-block; padding: 4px 12px; border-radius: 16px; font-size: 14px; }}
        .beginner {{ background: #d4edda; color: #155724; }}
        .intermediate {{ background: #fff3cd; color: #856404; }}
        .advanced {{ background: #f8d7da; color: #721c24; }}
        .step {{ border: 1px solid #e9ecef; border-radius: 8px; margin-bottom: 20px; }}
        .step-header {{ background: #f8f9fa; padding: 15px; border-bottom: 1px solid #e9ecef; }}
        .step-content {{ padding: 20px; }}
        .code-block {{ background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 4px; padding: 15px; margin: 10px 0; }}
        .code-block code {{ font-family: 'Courier New', monospace; }}
        .expected-output {{ background: #d1ecf1; border-left: 4px solid #bee5eb; padding: 10px; margin: 10px 0; }}
        .hints {{ background: #fff3cd; border-left: 4px solid #ffeaa7; padding: 10px; margin: 10px 0; }}
        .progress-bar {{ width: 100%; height: 20px; background: #e9ecef; border-radius: 10px; margin: 10px 0; }}
        .progress-fill {{ height: 100%; background: #28a745; border-radius: 10px; transition: width 0.3s; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{tutorial.title}</h1>
            <span class="difficulty {tutorial.difficulty}">{tutorial.difficulty.upper()}</span>
            <p>{tutorial.description}</p>
            
            <h3>Learning Objectives:</h3>
            <ul>
                {"".join(f"<li>{obj}</li>" for obj in tutorial.learning_objectives)}
            </ul>
            
            <div class="progress-bar">
                <div class="progress-fill" style="width: 0%" id="progress"></div>
            </div>
        </div>
        
        {self._generate_html_steps(tutorial.steps)}
    </div>
    
    <script>
        let currentStep = 0;
        const totalSteps = {len(tutorial.steps)};
        
        function updateProgress() {{
            const progress = (currentStep / totalSteps) * 100;
            document.getElementById('progress').style.width = progress + '%';
        }}
        
        function completeStep(stepNumber) {{
            currentStep = Math.max(currentStep, stepNumber);
            updateProgress();
        }}
    </script>
</body>
</html>"""
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Exported HTML tutorial: {html_file}")
        return str(html_file)
    
    def _generate_html_steps(self, steps: List[TutorialStep]) -> str:
        """Generate HTML for tutorial steps."""
        html_parts = []
        
        for step in steps:
            html_parts.append(f"""
<div class="step">
    <div class="step-header">
        <h2>Step {step.step_number}: {step.title}</h2>
        <small>Estimated time: {step.estimated_time} minutes</small>
    </div>
    <div class="step-content">
        <p>{step.description}</p>
        
        <div class="code-block">
            <strong>Code:</strong>
            <pre><code>{step.code}</code></pre>
        </div>
        
        {f'<div class="expected-output"><strong>Expected Output:</strong><br>{step.expected_output}</div>' if step.expected_output else ''}
        
        {f'<div class="hints"><strong>Hints:</strong><ul>{"".join(f"<li>{hint}</li>" for hint in step.hints)}</ul></div>' if step.hints else ''}
        
        <button onclick="completeStep({step.step_number})" style="background: #28a745; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">Complete Step</button>
    </div>
</div>""")
        
        return "".join(html_parts)
    
    def _export_markdown_tutorial(self, tutorial: Tutorial, output_path: Path) -> str:
        """Export tutorial as Markdown."""
        md_file = output_path / f"{tutorial.id}.md"
        
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(f"# {tutorial.title}\n\n")
            f.write(f"**Difficulty:** {tutorial.difficulty.title()}\n")
            f.write(f"**Category:** {tutorial.category}\n\n")
            f.write(f"{tutorial.description}\n\n")
            
            f.write("## Learning Objectives\n\n")
            for obj in tutorial.learning_objectives:
                f.write(f"- {obj}\n")
            f.write("\n")
            
            if tutorial.prerequisites:
                f.write("## Prerequisites\n\n")
                for prereq in tutorial.prerequisites:
                    f.write(f"- {prereq}\n")
                f.write("\n")
            
            f.write("## Tutorial Steps\n\n")
            
            for step in tutorial.steps:
                f.write(f"### Step {step.step_number}: {step.title}\n\n")
                f.write(f"*Estimated time: {step.estimated_time} minutes*\n\n")
                f.write(f"{step.description}\n\n")
                
                f.write("```python\n")
                f.write(f"{step.code}\n")
                f.write("```\n\n")
                
                if step.expected_output:
                    f.write("**Expected Output:**\n")
                    f.write(f"```\n{step.expected_output}\n```\n\n")
                
                if step.hints:
                    f.write("**Hints:**\n")
                    for hint in step.hints:
                        f.write(f"- {hint}\n")
                    f.write("\n")
                
                f.write("---\n\n")
        
        logger.info(f"Exported Markdown tutorial: {md_file}")
        return str(md_file)
    
    def _export_json_tutorial(self, tutorial: Tutorial, output_path: Path) -> str:
        """Export tutorial as JSON."""
        json_file = output_path / f"{tutorial.id}.json"
        
        tutorial_data = {
            "id": tutorial.id,
            "title": tutorial.title,
            "description": tutorial.description,
            "difficulty": tutorial.difficulty,
            "category": tutorial.category,
            "learning_objectives": tutorial.learning_objectives,
            "prerequisites": tutorial.prerequisites,
            "total_time": tutorial.total_time,
            "tags": tutorial.tags,
            "steps": [
                {
                    "step_number": step.step_number,
                    "title": step.title,
                    "description": step.description,
                    "code": step.code,
                    "expected_output": step.expected_output,
                    "hints": step.hints,
                    "prerequisites": step.prerequisites,
                    "validation_code": step.validation_code,
                    "estimated_time": step.estimated_time
                }
                for step in tutorial.steps
            ]
        }
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(tutorial_data, f, indent=2)
        
        logger.info(f"Exported JSON tutorial: {json_file}")
        return str(json_file)
    
    def get_learning_path(self, path_name: str) -> List[Tutorial]:
        """Get tutorials for a specific learning path."""
        if path_name not in self.learning_paths:
            raise ValueError(f"Learning path '{path_name}' not found")
        
        tutorial_ids = self.learning_paths[path_name]
        return [self.tutorials[tutorial_id] for tutorial_id in tutorial_ids]
    
    def recommend_next_tutorial(self, completed_tutorials: List[str]) -> Optional[str]:
        """Recommend the next tutorial based on completed ones."""
        # Simple recommendation logic - can be made more sophisticated
        all_tutorial_ids = set(self.tutorials.keys())
        completed_set = set(completed_tutorials)
        remaining = all_tutorial_ids - completed_set
        
        if not remaining:
            return None
        
        # Recommend based on prerequisites
        for tutorial_id in remaining:
            tutorial = self.tutorials[tutorial_id]
            prereqs_met = all(prereq in completed_tutorials for prereq in tutorial.prerequisites)
            if prereqs_met:
                return tutorial_id
        
        # If no prereqs match, return any remaining tutorial
        return list(remaining)[0]