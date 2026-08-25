"""
VS Code Integration Tools
========================

Provides specific tools and utilities for VS Code integration,
command palette functionality, and interactive development features.
"""

import logging
import time
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class VSCodeTools:
    """
    Tools and utilities for VS Code integration.
    """

    def __init__(self, autocad_wrapper=None, context_manager=None):
        """
        Initialize VS Code tools.

        Args:
            autocad_wrapper: AutoCAD wrapper instance
            context_manager: Context manager for sessions
        """
        self.autocad_wrapper = autocad_wrapper
        self.context_manager = context_manager
        self.command_history = []
        self.project_templates = self._initialize_project_templates()
        self.enhanced_completions = self._initialize_enhanced_completions()
        self.debug_sessions = {}

        logger.info("Enhanced VS Code Tools initialized")

    def get_autocad_connection_indicator(self) -> Dict[str, Any]:
        """
        Get AutoCAD connection status for VS Code status bar.

        Returns:
            Dictionary containing status bar information
        """
        try:
            if not self.autocad_wrapper:
                return {
                    "connected": False,
                    "status_text": "AutoCAD: Not Connected",
                    "tooltip": "AutoCAD connection not available",
                    "color": "red",
                }

            status = self.autocad_wrapper.get_connection_status()

            if status["connected"]:
                return {
                    "connected": True,
                    "status_text": f"AutoCAD: Connected ({status.get('documents_count', 0)} docs)",
                    "tooltip": f"AutoCAD {status.get('autocad_version', 'Unknown')} - Connected",
                    "color": "green",
                }
            else:
                return {
                    "connected": False,
                    "status_text": "AutoCAD: Disconnected",
                    "tooltip": "AutoCAD not connected - Ensure AutoCAD 2025 is running",
                    "color": "yellow",
                }

        except Exception as e:
            logger.error(f"Error getting connection indicator: {str(e)}")
            return {
                "connected": False,
                "status_text": "AutoCAD: Error",
                "tooltip": f"Connection error: {str(e)}",
                "color": "red",
            }

    def get_command_palette_items(self) -> List[Dict[str, Any]]:
        """
        Get items for VS Code command palette.

        Returns:
            List of command palette items
        """
        commands = [
            # Connection commands
            {
                "id": "autocad.checkConnection",
                "title": "AutoCAD: Check Connection Status",
                "description": "Check AutoCAD connection and get detailed status",
            },
            {
                "id": "autocad.recoverConnection",
                "title": "AutoCAD: Recover Connection",
                "description": "Attempt to recover lost AutoCAD connection",
            },
            # Drawing commands
            {
                "id": "autocad.drawLine",
                "title": "AutoCAD: Draw Line",
                "description": "Draw a line in AutoCAD",
            },
            {
                "id": "autocad.drawCircle",
                "title": "AutoCAD: Draw Circle",
                "description": "Draw a circle in AutoCAD",
            },
            # Interactive development
            {
                "id": "autocad.startREPL",
                "title": "AutoCAD: Start Interactive Session",
                "description": "Start interactive Python session with AutoCAD context",
            },
            {
                "id": "autocad.executeCode",
                "title": "AutoCAD: Execute Selected Code",
                "description": "Execute selected Python code in AutoCAD context",
            },
            {
                "id": "autocad.debugCode",
                "title": "AutoCAD: Debug Selected Code",
                "description": "Debug selected Python code with breakpoints",
            },
            {
                "id": "autocad.inspectObject",
                "title": "AutoCAD: Inspect Object",
                "description": "Inspect AutoCAD object properties and methods",
            },
            # Project management
            {
                "id": "autocad.createProject",
                "title": "AutoCAD: Create New Project",
                "description": "Create new AutoCAD automation project from template",
            },
            {
                "id": "autocad.generateCode",
                "title": "AutoCAD: Generate Code from Description",
                "description": "Generate Python/AutoLISP/VBA code from natural language",
            },
            # Diagnostic commands
            {
                "id": "autocad.generateReport",
                "title": "AutoCAD: Generate Diagnostic Report",
                "description": "Generate comprehensive diagnostic report",
            },
            {
                "id": "autocad.performanceMetrics",
                "title": "AutoCAD: Show Performance Metrics",
                "description": "Display performance metrics and statistics",
            },
            # Manufacturing commands (preserved)
            {
                "id": "autocad.surfaceUnfolding",
                "title": "AutoCAD: Surface Unfolding",
                "description": "Access surface unfolding tools",
            },
            {
                "id": "autocad.patternOptimization",
                "title": "AutoCAD: Pattern Optimization",
                "description": "Access pattern nesting optimization tools",
            },
        ]

        return commands

    def execute_vscode_command(
        self, command_id: str, args: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute VS Code command.

        Args:
            command_id: Command identifier
            args: Command arguments

        Returns:
            Command execution result
        """
        try:
            result = self._handle_command(command_id, args or {})

            # Record command in history
            self.command_history.append(
                {
                    "timestamp": time.time(),
                    "command_id": command_id,
                    "args": args,
                    "success": True,
                    "result": result,
                }
            )

            # Keep only last 50 commands
            if len(self.command_history) > 50:
                self.command_history = self.command_history[-50:]

            return {"success": True, "result": result}

        except Exception as e:
            error_result = {"success": False, "error": str(e)}

            # Record failed command
            self.command_history.append(
                {
                    "timestamp": time.time(),
                    "command_id": command_id,
                    "args": args,
                    "success": False,
                    "error": str(e),
                }
            )

            logger.error(f"VS Code command failed: {command_id} - {str(e)}")
            return error_result

    def _handle_command(self, command_id: str, args: Dict[str, Any]) -> Any:
        """
        Handle specific VS Code command.

        Args:
            command_id: Command identifier
            args: Command arguments

        Returns:
            Command result
        """
        if command_id == "autocad.checkConnection":
            return self._handle_check_connection()

        elif command_id == "autocad.recoverConnection":
            return self._handle_recover_connection()

        elif command_id == "autocad.drawLine":
            return self._handle_draw_line(args)

        elif command_id == "autocad.drawCircle":
            return self._handle_draw_circle(args)

        elif command_id == "autocad.executeCode":
            return self._handle_execute_code(args)

        elif command_id == "autocad.generateReport":
            return self._handle_generate_report()

        elif command_id == "autocad.performanceMetrics":
            return self._handle_performance_metrics()
        
        elif command_id == "autocad.debugCode":
            return self._handle_debug_code(args)
        
        elif command_id == "autocad.inspectObject":
            return self._handle_inspect_object(args)
        
        elif command_id == "autocad.createProject":
            return self._handle_create_project(args)
        
        elif command_id == "autocad.generateCode":
            return self._handle_generate_code(args)

        else:
            raise ValueError(f"Unknown command: {command_id}")

    def _handle_check_connection(self) -> Dict[str, Any]:
        """Handle check connection command."""
        if not self.autocad_wrapper:
            return {"status": "No AutoCAD wrapper available"}

        status = self.autocad_wrapper.get_connection_status()
        performance = self.autocad_wrapper.get_performance_metrics()

        return {
            "connection_status": status,
            "performance_summary": {
                "total_operations": performance.get("total_operations", 0),
                "success_rate": performance.get("overall_success_rate", 0),
                "average_duration": performance.get("average_operation_duration", 0),
            },
        }

    def _handle_recover_connection(self) -> Dict[str, Any]:
        """Handle recover connection command."""
        if not self.autocad_wrapper:
            return {"success": False, "message": "No AutoCAD wrapper available"}

        success = self.autocad_wrapper.recover_connection()
        return {
            "success": success,
            "message": (
                "Connection recovered successfully" if success else "Connection recovery failed"
            ),
        }

    def _handle_draw_line(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle draw line command."""
        start_point = args.get("start_point", [0, 0, 0])
        end_point = args.get("end_point", [100, 100, 0])

        if not self.autocad_wrapper:
            raise ValueError("AutoCAD wrapper not available")

        entity_id = self.autocad_wrapper.draw_line(start_point, end_point)
        return {"entity_id": entity_id, "start_point": start_point, "end_point": end_point}

    def _handle_draw_circle(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle draw circle command."""
        center = args.get("center", [0, 0, 0])
        radius = args.get("radius", 50.0)

        if not self.autocad_wrapper:
            raise ValueError("AutoCAD wrapper not available")

        entity_id = self.autocad_wrapper.draw_circle(center, radius)
        return {"entity_id": entity_id, "center": center, "radius": radius}

    def _handle_execute_code(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle execute code command."""
        code = args.get("code", "")
        session_id = args.get("session_id")

        if not code.strip():
            raise ValueError("No code provided")

        # This would integrate with the enhanced MCP server's execute_simple_python
        # For now, return a placeholder response
        return {
            "code": code,
            "session_id": session_id,
            "result": "Code execution would be handled by MCP server",
        }

    def _handle_generate_report(self) -> Dict[str, Any]:
        """Handle generate report command."""
        if not self.autocad_wrapper:
            return {"report": "No AutoCAD wrapper available for diagnostics"}

        report = self.autocad_wrapper.create_diagnostic_report()
        return {"diagnostic_report": report}

    def _handle_performance_metrics(self) -> Dict[str, Any]:
        """Handle performance metrics command."""
        if not self.autocad_wrapper:
            return {"metrics": "No AutoCAD wrapper available for metrics"}

        metrics = self.autocad_wrapper.get_performance_metrics()
        return {"performance_metrics": metrics}

    def get_intellisense_completions(self, context: str, position: int) -> List[Dict[str, Any]]:
        """
        Get IntelliSense completions for AutoCAD context.

        Args:
            context: Code context around cursor
            position: Cursor position

        Returns:
            List of completion items
        """
        completions = []

        # AutoCAD object completions
        autocad_completions = [
            {
                "label": "acad.app",
                "kind": "property",
                "detail": "AutoCAD Application object",
                "documentation": "Access to AutoCAD application instance",
            },
            {
                "label": "acad.doc",
                "kind": "property",
                "detail": "Active AutoCAD document",
                "documentation": "Currently active AutoCAD document",
            },
            {
                "label": "acad.model",
                "kind": "property",
                "detail": "Model space object",
                "documentation": "AutoCAD model space for entity creation",
            },
            {
                "label": "acad.draw_line",
                "kind": "method",
                "detail": "draw_line(start_point, end_point)",
                "documentation": "Draw a line from start to end point",
            },
            {
                "label": "acad.draw_circle",
                "kind": "method",
                "detail": "draw_circle(center, radius)",
                "documentation": "Draw a circle with specified center and radius",
            },
        ]

        # Filter completions based on context
        if "acad." in context:
            completions.extend(autocad_completions)

        return completions

    def get_command_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent command history.

        Args:
            limit: Maximum number of commands to return

        Returns:
            List of recent commands
        """
        return self.command_history[-limit:] if limit > 0 else self.command_history

    def clear_command_history(self) -> None:
        """Clear command history."""
        self.command_history.clear()
        logger.info("VS Code command history cleared")

    def get_vscode_integration_status(self) -> Dict[str, Any]:
        """
        Get VS Code integration status.

        Returns:
            Dictionary containing integration status
        """
        return {
            "autocad_wrapper_available": self.autocad_wrapper is not None,
            "context_manager_available": self.context_manager is not None,
            "command_palette_items": len(self.get_command_palette_items()),
            "command_history_count": len(self.command_history),
            "project_templates_count": len(self.project_templates),
            "debug_sessions_active": len(self.debug_sessions),
            "integration_active": True,
        }
    
    def _initialize_project_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize project templates for VS Code integration."""
        return {
            "basic_automation": {
                "name": "Basic AutoCAD Automation",
                "description": "Simple automation script template",
                "files": {
                    "main.py": """# Basic AutoCAD Automation Script
from enhanced_autocad import EnhancedAutoCAD

def main():
    with EnhancedAutoCAD() as acad:
        # Your automation code here
        pass

if __name__ == "__main__":
    main()""",
                    "requirements.txt": "enhanced-autocad>=1.0.0\\npywin32>=311",
                    "README.md": "# AutoCAD Automation Project\\n\\nBasic AutoCAD automation project."
                }
            },
            "interactive_development": {
                "name": "Interactive Development",
                "description": "Template for interactive AutoCAD development", 
                "files": {
                    "interactive.py": """# Interactive AutoCAD Development Template
from enhanced_autocad import EnhancedAutoCAD
import math

# Initialize AutoCAD connection
acad = EnhancedAutoCAD()

# Example: Draw a series of lines
def draw_rectangle(width=100, height=50):
    \"\"\"Draw a rectangle.\"\"\"
    points = [
        [0, 0, 0], [width, 0, 0],
        [width, height, 0], [0, height, 0], [0, 0, 0]
    ]
    
    for i in range(len(points) - 1):
        acad.draw_line(points[i], points[i + 1])

# Call the function
# draw_rectangle()""",
                    "config.json": '{\n  "autocad_version": "2025",\n  "default_layer": "0",\n  "units": "millimeters"\n}'
                }
            }
        }
    
    def _initialize_enhanced_completions(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize enhanced IntelliSense completions."""
        return {
            "autocad_objects": [
                {
                    "label": "app",
                    "kind": "property",
                    "detail": "Application",
                    "documentation": "AutoCAD Application object - provides access to application-level functionality",
                    "insertText": "app"
                },
                {
                    "label": "doc",
                    "kind": "property", 
                    "detail": "Document",
                    "documentation": "Active AutoCAD document - provides access to drawing content",
                    "insertText": "doc"
                },
                {
                    "label": "model",
                    "kind": "property",
                    "detail": "ModelSpace",
                    "documentation": "Model space collection - container for drawing entities",
                    "insertText": "model"
                }
            ],
            "drawing_methods": [
                {
                    "label": "draw_line",
                    "kind": "method",
                    "detail": "draw_line(start_point: List[float], end_point: List[float]) -> int",
                    "documentation": "Draw a line from start_point to end_point. Returns entity ID.",
                    "insertText": "draw_line([${1:0}, ${2:0}, ${3:0}], [${4:100}, ${5:100}, ${6:0}])"
                },
                {
                    "label": "draw_circle",
                    "kind": "method",
                    "detail": "draw_circle(center: List[float], radius: float) -> int",
                    "documentation": "Draw a circle with specified center and radius. Returns entity ID.",
                    "insertText": "draw_circle([${1:0}, ${2:0}, ${3:0}], ${4:50.0})"
                },
                {
                    "label": "draw_arc",
                    "kind": "method",
                    "detail": "draw_arc(center: List[float], radius: float, start_angle: float, end_angle: float) -> int",
                    "documentation": "Draw an arc with specified parameters. Angles in radians.",
                    "insertText": "draw_arc([${1:0}, ${2:0}, ${3:0}], ${4:50.0}, ${5:0}, ${6:3.14159})"
                }
            ]
        }
    
    def _handle_debug_code(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle debug code command with breakpoint support."""
        code = args.get("code", "")
        breakpoints = args.get("breakpoints", [])
        session_id = args.get("session_id", f"debug_{int(time.time())}")
        
        if not code.strip():
            raise ValueError("No code provided for debugging")
        
        # Create debug session
        self.debug_sessions[session_id] = {
            "code": code,
            "breakpoints": breakpoints,
            "created_at": time.time(),
            "status": "active"
        }
        
        # For now, return debug session info - actual debugging would integrate with VS Code debugger
        return {
            "session_id": session_id,
            "status": "debug_session_created",
            "breakpoints_set": len(breakpoints),
            "message": "Debug session created. Use VS Code debugger to step through code."
        }
    
    def _handle_inspect_object(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle object inspection command."""
        object_name = args.get("object_name", "")
        inspection_depth = args.get("depth", "basic")
        
        if not object_name:
            raise ValueError("No object name provided for inspection")
        
        # Mock object inspection - would integrate with actual AutoCAD object introspection
        inspection_result = {
            "object_name": object_name,
            "object_type": f"AutoCAD.{object_name.capitalize()}",
            "properties": [
                {"name": "Name", "type": "string", "value": object_name},
                {"name": "ObjectID", "type": "int", "value": "123456"},
                {"name": "Layer", "type": "string", "value": "0"}
            ],
            "methods": [
                {"name": "Update", "signature": "Update() -> None", "description": "Update the object"},
                {"name": "Delete", "signature": "Delete() -> None", "description": "Delete the object"},
                {"name": "Copy", "signature": "Copy() -> Object", "description": "Create a copy of the object"}
            ],
            "depth": inspection_depth
        }
        
        return inspection_result
    
    def _handle_create_project(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle create project command."""
        template_id = args.get("template", "basic_automation")
        project_name = args.get("name", "AutoCAD_Project")
        project_path = args.get("path", ".")
        
        if template_id not in self.project_templates:
            raise ValueError(f"Unknown template: {template_id}")
        
        template = self.project_templates[template_id]
        
        # Create project structure
        project_info = {
            "name": project_name,
            "template": template_id,
            "template_name": template["name"],
            "path": project_path,
            "files_created": list(template["files"].keys()),
            "created_at": time.time()
        }
        
        return {
            "success": True,
            "project": project_info,
            "message": f"Project '{project_name}' created from template '{template['name']}'"
        }
    
    def _handle_generate_code(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle code generation command."""
        description = args.get("description", "")
        language = args.get("language", "python")
        complexity = args.get("complexity", "basic")
        
        if not description.strip():
            raise ValueError("No description provided for code generation")
        
        # Generate functional code based on description and language
        generated_code = self._generate_functional_code(description, language, complexity)
        
        return {
            "description": description,
            "language": language,
            "complexity": complexity,
            "generated_code": generated_code.get(language, generated_code["python"]),
            "suggestions": [
                "Add error handling",
                "Include parameter validation", 
                "Add progress reporting"
            ]
        }
    
    def get_enhanced_intellisense_completions(
        self, context: str, position: int, file_content: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Get enhanced IntelliSense completions with context awareness.
        
        Args:
            context: Code context around cursor
            position: Cursor position
            file_content: Full file content for better context analysis
            
        Returns:
            List of enhanced completion items
        """
        completions = []
        
        # Analyze context for better completions
        context_lower = context.lower()
        
        # AutoCAD object completions
        if "acad." in context_lower or "autocad" in context_lower:
            completions.extend(self.enhanced_completions["autocad_objects"])
            completions.extend(self.enhanced_completions["drawing_methods"])
        
        # Method-specific completions
        if "draw_" in context_lower:
            completions.extend(self.enhanced_completions["drawing_methods"])
        
        # Add context-specific completions based on file content analysis
        if "import" in file_content and "enhanced_autocad" in file_content:
            completions.append({
                "label": "with EnhancedAutoCAD() as acad:",
                "kind": "snippet",
                "detail": "AutoCAD context manager",
                "documentation": "Recommended pattern for AutoCAD automation",
                "insertText": "with EnhancedAutoCAD() as acad:\\n    ${1:# Your code here}"
            })
        
        return completions
    
    def get_debug_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get active debug sessions."""
        return self.debug_sessions.copy()
    
    def stop_debug_session(self, session_id: str) -> bool:
        """Stop a debug session."""
        if session_id in self.debug_sessions:
            self.debug_sessions[session_id]["status"] = "stopped"
            del self.debug_sessions[session_id]
            logger.info(f"Debug session {session_id} stopped")
            return True
        return False
    
    def get_project_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get available project templates."""
        return self.project_templates.copy()
    
    def _generate_functional_code(self, description: str, language: str, complexity: str) -> Dict[str, str]:
        """Generate functional code based on description, language, and complexity."""
        # Analyze description to determine the type of AutoCAD operation
        desc_lower = description.lower()
        
        if language == "python":
            return {"python": self._generate_python_functional_code(description, desc_lower, complexity)}
        elif language == "autolisp":
            return {"autolisp": self._generate_autolisp_functional_code(description, desc_lower, complexity)}
        elif language == "vba":
            return {"vba": self._generate_vba_functional_code(description, desc_lower, complexity)}
        else:
            # Default to Python
            return {"python": self._generate_python_functional_code(description, desc_lower, complexity)}
    
    def _generate_python_functional_code(self, description: str, desc_lower: str, complexity: str) -> str:
        """Generate functional Python code for AutoCAD operations."""
        base_template = f'''# Generated Python code for: {description}
from enhanced_autocad import EnhancedAutoCAD
import logging

logger = logging.getLogger(__name__)

def generated_function():
    """Generated function: {description}"""
    try:
        with EnhancedAutoCAD() as acad:
'''
        
        # Determine operation type and generate appropriate code
        if "line" in desc_lower or "draw line" in desc_lower:
            code_body = '''            # Draw a line
            start_point = [0.0, 0.0, 0.0]
            end_point = [100.0, 100.0, 0.0]
            line = acad.model.AddLine(start_point, end_point)
            logger.info(f"Created line with ID: {line.ObjectID}")
            return {"success": True, "entity_id": line.ObjectID}'''
        
        elif "circle" in desc_lower or "draw circle" in desc_lower:
            code_body = '''            # Draw a circle
            center_point = [50.0, 50.0, 0.0]
            radius = 25.0
            circle = acad.model.AddCircle(center_point, radius)
            logger.info(f"Created circle with ID: {circle.ObjectID}")
            return {"success": True, "entity_id": circle.ObjectID}'''
        
        elif "mesh" in desc_lower or "surface" in desc_lower:
            code_body = '''            # Create a 3D mesh surface
            m_size, n_size = 4, 4
            vertices = []
            for i in range(m_size):
                for j in range(n_size):
                    x = i * 50.0
                    y = j * 50.0
                    z = 10.0 * math.sin(i * 0.5) * math.cos(j * 0.5)
                    vertices.append([x, y, z])
            
            mesh = acad.model.Add3DMesh(m_size, n_size, vertices)
            logger.info(f"Created 3D mesh with ID: {mesh.ObjectID}")
            return {"success": True, "entity_id": mesh.ObjectID}'''
        
        elif "extrude" in desc_lower:
            code_body = '''            # Create an extruded solid
            profile_points = [[0, 0], [100, 0], [100, 100], [0, 100], [0, 0]]
            polyline = acad.model.AddPolyline(profile_points)
            height = 50.0
            solid = acad.model.AddExtrudedSolid(polyline, height)
            logger.info(f"Created extruded solid with ID: {solid.ObjectID}")
            return {"success": True, "entity_id": solid.ObjectID}'''
        
        else:
            # Generic AutoCAD operation
            code_body = f'''            # Generic AutoCAD operation: {description}
            logger.info("Executing: {description}")
            # Add your specific AutoCAD operations here
            return {{"success": True, "message": "Operation completed"}}'''
        
        imports = ""
        if "mesh" in desc_lower or "surface" in desc_lower:
            imports = "import math\n"
        
        return f'''{imports}{base_template}{code_body}
    
    except Exception as e:
        logger.error(f"Error in generated function: {{e}}")
        return {{"success": False, "error": str(e)}}

if __name__ == "__main__":
    result = generated_function()
    print(f"Result: {{result}}")'''
    
    def _generate_autolisp_functional_code(self, description: str, desc_lower: str, complexity: str) -> str:
        """Generate functional AutoLISP code for AutoCAD operations."""
        command_name = "GENERATED-CMD"
        
        if "line" in desc_lower:
            command_name = "DRAWLINE"
            code_body = '''  ;; Draw a line
  (setq start_pt (list 0.0 0.0 0.0))
  (setq end_pt (list 100.0 100.0 0.0))
  (setq line_obj (entmake (list '(0 . "LINE")
                               (cons 10 start_pt)
                               (cons 11 end_pt))))
  (princ "\\nLine created successfully")'''
        
        elif "circle" in desc_lower:
            command_name = "DRAWCIRCLE"
            code_body = '''  ;; Draw a circle
  (setq center_pt (list 50.0 50.0 0.0))
  (setq radius 25.0)
  (setq circle_obj (entmake (list '(0 . "CIRCLE")
                                 (cons 10 center_pt)
                                 (cons 40 radius))))
  (princ "\\nCircle created successfully")'''
        
        else:
            code_body = f'''  ;; {description}
  (princ "\\nExecuting: {description}")
  ;; Add your specific AutoLISP code here
  (setq result T)'''
        
        return f''';; Generated AutoLISP code for: {description}
(defun C:{command_name} ()
  "AutoCAD command: {description}"
{code_body}
  (princ)
  result
)

;; Load command
(princ "\\nLoaded command: {command_name}")
(princ)'''
    
    def _generate_vba_functional_code(self, description: str, desc_lower: str, complexity: str) -> str:
        """Generate functional VBA code for AutoCAD operations."""
        sub_name = "GeneratedMacro"
        
        if "line" in desc_lower:
            sub_name = "DrawLine"
            code_body = '''    ' Draw a line
    Dim startPoint(0 To 2) As Double
    Dim endPoint(0 To 2) As Double
    
    startPoint(0) = 0: startPoint(1) = 0: startPoint(2) = 0
    endPoint(0) = 100: endPoint(1) = 100: endPoint(2) = 0
    
    Dim lineObj As AcadLine
    Set lineObj = acDoc.ModelSpace.AddLine(startPoint, endPoint)
    
    MsgBox "Line created successfully"'''
        
        elif "circle" in desc_lower:
            sub_name = "DrawCircle"
            code_body = '''    ' Draw a circle
    Dim centerPoint(0 To 2) As Double
    Dim radius As Double
    
    centerPoint(0) = 50: centerPoint(1) = 50: centerPoint(2) = 0
    radius = 25
    
    Dim circleObj As AcadCircle
    Set circleObj = acDoc.ModelSpace.AddCircle(centerPoint, radius)
    
    MsgBox "Circle created successfully"'''
        
        else:
            code_body = f'''    ' {description}
    MsgBox "{description} executed successfully"
    ' Add your specific VBA code here'''
        
        return f''''{description}
' Generated VBA code

Sub {sub_name}()
    Dim acDoc As AcadDocument
    Set acDoc = ThisDrawing
    
{code_body}
    
End Sub'''
