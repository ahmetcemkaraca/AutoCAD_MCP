"""
AutoLISP Code Generator for Master AutoCAD Coder.

Generates AutoLISP code from natural language descriptions and structured requirements.
Leverages templates and best practices for professional AutoCAD automation.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import re
import json


@dataclass
class AutoLISPFunction:
    """Represents an AutoLISP function definition."""
    name: str
    parameters: List[str]
    description: str
    code_template: str
    examples: List[str]


class AutoLISPGenerator:
    """Generates AutoLISP code for AutoCAD automation tasks."""
    
    def __init__(self):
        self.functions = self._initialize_functions()
        self.templates = self._initialize_templates()
        self.patterns = self._initialize_patterns()
    
    def _initialize_functions(self) -> Dict[str, AutoLISPFunction]:
        """Initialize common AutoLISP function templates."""
        return {
            "draw_line": AutoLISPFunction(
                name="draw-line",
                parameters=["pt1", "pt2"],
                description="Draw a line between two points",
                code_template="""(defun c:draw-line (pt1 pt2 / )
  (command "LINE" pt1 pt2 "")
  (princ)
)""",
                examples=["(c:draw-line '(0 0 0) '(100 100 0))"]
            ),
            
            "draw_circle": AutoLISPFunction(
                name="draw-circle", 
                parameters=["center", "radius"],
                description="Draw a circle at center point with given radius",
                code_template="""(defun c:draw-circle (center radius / )
  (command "CIRCLE" center radius)
  (princ)
)""",
                examples=["(c:draw-circle '(50 50 0) 25)"]
            ),
            
            "draw_rectangle": AutoLISPFunction(
                name="draw-rectangle",
                parameters=["corner1", "corner2"],
                description="Draw a rectangle using two corner points",
                code_template="""(defun c:draw-rectangle (corner1 corner2 / )
  (command "RECTANGLE" corner1 corner2)
  (princ)
)""",
                examples=["(c:draw-rectangle '(0 0 0) '(100 50 0))"]
            ),
            
            "draw_polyline": AutoLISPFunction(
                name="draw-polyline",
                parameters=["points"],
                description="Draw a polyline through multiple points",
                code_template="""(defun c:draw-polyline (points / pt)
  (command "PLINE")
  (foreach pt points
    (command pt)
  )
  (command "")
  (princ)
)""",
                examples=["(c:draw-polyline '((0 0 0) (50 0 0) (50 50 0) (0 50 0)))"]
            ),
            
            "select_all": AutoLISPFunction(
                name="select-all",
                parameters=["entity-type"],
                description="Select all entities of specified type",
                code_template="""(defun c:select-all (entity-type / ss)
  (setq ss (ssget "X" (list (cons 0 entity-type))))
  (if ss
    (progn
      (princ (strcat "Selected " (itoa (sslength ss)) " " entity-type " entities."))
      ss
    )
    (progn
      (princ (strcat "No " entity-type " entities found."))
      nil
    )
  )
)""",
                examples=["(c:select-all \"LINE\")", "(c:select-all \"CIRCLE\")"]
            ),
            
            "get_entity_info": AutoLISPFunction(
                name="get-entity-info",
                parameters=["entity"],
                description="Get detailed information about an entity",
                code_template="""(defun c:get-entity-info (entity / ent-data)
  (setq ent-data (entget entity))
  (if ent-data
    (progn
      (princ "\\nEntity Information:")
      (princ (strcat "\\nType: " (cdr (assoc 0 ent-data))))
      (princ (strcat "\\nLayer: " (cdr (assoc 8 ent-data))))
      ent-data
    )
    (princ "\\nInvalid entity.")
  )
)""",
                examples=["(c:get-entity-info (car (entsel \"Select entity: \")))"]
            ),
            
            "batch_process": AutoLISPFunction(
                name="batch-process",
                parameters=["selection-set", "operation"],
                description="Process multiple entities with the same operation",
                code_template="""(defun c:batch-process (ss operation / i ent)
  (setq i 0)
  (repeat (sslength ss)
    (setq ent (ssname ss i))
    (apply operation (list ent))
    (setq i (1+ i))
  )
  (princ (strcat "Processed " (itoa (sslength ss)) " entities."))
)""",
                examples=["(c:batch-process (ssget) 'erase-entity)"]
            )
        }
    
    def _initialize_templates(self) -> Dict[str, str]:
        """Initialize code templates for common patterns."""
        return {
            "basic_command": """(defun c:{command_name} ( / {local_vars})
  ;; {description}
  {code_body}
  (princ)
)""",
            
            "parametric_command": """(defun c:{command_name} ({parameters} / {local_vars})
  ;; {description}
  ;; Parameters: {param_descriptions}
  {code_body}
  (princ)
)""",
            
            "selection_command": """(defun c:{command_name} ( / ss i ent {local_vars})
  ;; {description}
  (setq ss (ssget))
  (if ss
    (progn
      (setq i 0)
      (repeat (sslength ss)
        (setq ent (ssname ss i))
        {entity_processing}
        (setq i (1+ i))
      )
      (princ (strcat "Processed " (itoa (sslength ss)) " entities."))
    )
    (princ "No entities selected.")
  )
  (princ)
)""",
            
            "user_input_command": """(defun c:{command_name} ( / {input_vars} {local_vars})
  ;; {description}
  {input_prompts}
  (if (and {validation_checks})
    (progn
      {code_body}
      (princ "Command completed successfully.")
    )
    (princ "Invalid input. Command cancelled.")
  )
  (princ)
)""",
            
            "error_handling": """(defun c:{command_name} ( / {local_vars})
  ;; {description}
  (if (not (and {preconditions}))
    (progn
      (princ "Error: Prerequisites not met.")
      (exit)
    )
  )
  
  ;; Main operation with error handling
  (if (vl-catch-all-error-p
        (setq result (vl-catch-all-apply '{operation} {parameters})))
    (progn
      (princ (strcat "Error occurred: " (vl-catch-all-error-message result)))
      nil
    )
    (progn
      {success_code}
      result
    )
  )
  (princ)
)"""
        }
    
    def _initialize_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize pattern recognition for code generation."""
        return {
            "drawing_operations": {
                "keywords": ["draw", "create", "make"],
                "entities": {
                    "line": {"function": "draw_line", "params": ["start_point", "end_point"]},
                    "circle": {"function": "draw_circle", "params": ["center", "radius"]},
                    "rectangle": {"function": "draw_rectangle", "params": ["corner1", "corner2"]},
                    "polyline": {"function": "draw_polyline", "params": ["points"]}
                }
            },
            "selection_operations": {
                "keywords": ["select", "find", "get"],
                "patterns": {
                    "all": "select_all",
                    "by_type": "select_by_type", 
                    "by_layer": "select_by_layer"
                }
            },
            "modification_operations": {
                "keywords": ["move", "copy", "rotate", "scale", "modify"],
                "commands": {
                    "move": "MOVE",
                    "copy": "COPY",
                    "rotate": "ROTATE", 
                    "scale": "SCALE"
                }
            },
            "batch_operations": {
                "keywords": ["batch", "multiple", "all", "process"],
                "template": "selection_command"
            }
        }
    
    def generate_code(self, description: str, complexity: str = "basic") -> Dict[str, Any]:
        """Generate AutoLISP code from natural language description."""
        # Parse the description
        parsed = self._parse_description(description)
        
        # Determine the appropriate template and approach
        if parsed["operation_type"] == "drawing":
            return self._generate_drawing_code(parsed, complexity)
        elif parsed["operation_type"] == "selection":
            return self._generate_selection_code(parsed, complexity)
        elif parsed["operation_type"] == "modification":
            return self._generate_modification_code(parsed, complexity)
        elif parsed["operation_type"] == "batch":
            return self._generate_batch_code(parsed, complexity)
        else:
            return self._generate_generic_code(parsed, complexity)
    
    def _parse_description(self, description: str) -> Dict[str, Any]:
        """Parse natural language description into structured data."""
        desc_lower = description.lower()
        
        # Identify operation type
        operation_type = "generic"
        for pattern_name, pattern_info in self.patterns.items():
            if any(keyword in desc_lower for keyword in pattern_info["keywords"]):
                operation_type = pattern_name.replace("_operations", "")
                break
        
        # Extract entities mentioned
        entities = []
        entity_keywords = ["line", "circle", "rectangle", "polyline", "arc", "text", "block"]
        for entity in entity_keywords:
            if entity in desc_lower:
                entities.append(entity)
        
        # Extract parameters/values
        numbers = re.findall(r'\b\d+(?:\.\d+)?\b', description)
        coordinates = re.findall(r'\(?\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*(?:,\s*(-?\d+(?:\.\d+)?))?\s*\)?', description)
        
        # Identify command name from description
        command_name = self._extract_command_name(description)
        
        return {
            "operation_type": operation_type,
            "entities": entities,
            "numbers": [float(n) for n in numbers],
            "coordinates": [[float(x) if x else 0 for x in coord] for coord in coordinates],
            "command_name": command_name,
            "description": description
        }
    
    def _extract_command_name(self, description: str) -> str:
        """Extract or generate appropriate command name."""
        # Try to find explicit command name
        cmd_match = re.search(r'command\s+(?:called\s+)?["\']?(\w+)["\']?', description.lower())
        if cmd_match:
            return cmd_match.group(1)
        
        # Generate from key actions
        desc_lower = description.lower()
        if "draw line" in desc_lower:
            return "drawline"
        elif "draw circle" in desc_lower:
            return "drawcircle"
        elif "draw rectangle" in desc_lower:
            return "drawrect"
        elif "select all" in desc_lower:
            return "selectall"
        elif "batch" in desc_lower:
            return "batchprocess"
        else:
            # Generate generic name
            words = re.findall(r'\b\w+\b', desc_lower)
            return ''.join(word for word in words[:2] if len(word) > 2)
    
    def _generate_drawing_code(self, parsed: Dict[str, Any], complexity: str) -> Dict[str, Any]:
        """Generate code for drawing operations."""
        if not parsed["entities"]:
            return {"error": "No drawing entities specified"}
        
        entity = parsed["entities"][0]  # Use first entity mentioned
        
        # Map entity names to function names
        entity_mapping = {
            "line": "draw_line",
            "circle": "draw_circle", 
            "rectangle": "draw_rectangle",
            "polyline": "draw_polyline"
        }
        
        func_name = entity_mapping.get(entity, f"draw_{entity}")
        
        if func_name in self.functions:
            func = self.functions[func_name]
            
            # Customize the template based on complexity
            if complexity == "basic":
                code = self._create_basic_drawing_command(entity, parsed)
            else:
                code = self._create_advanced_drawing_command(entity, parsed)
            
            return {
                "code": code,
                "language": "autolisp",
                "command_name": parsed["command_name"],
                "description": f"AutoLISP command to {parsed['description']}",
                "usage_example": f"(c:{parsed['command_name']})",
                "notes": [
                    "Load this code into AutoCAD using APPLOAD command",
                    f"Type '{parsed['command_name']}' at the command prompt to execute"
                ]
            }
        
        return {"error": f"Unsupported entity type: {entity}"}
    
    def _create_basic_drawing_command(self, entity: str, parsed: Dict[str, Any]) -> str:
        """Create basic drawing command code."""
        command_name = parsed["command_name"]
        
        if entity == "line":
            return f"""(defun c:{command_name} ( / pt1 pt2)
  ;; {parsed['description']}
  (setq pt1 (getpoint "Specify first point: "))
  (setq pt2 (getpoint pt1 "Specify second point: "))
  (command "LINE" pt1 pt2 "")
  (princ)
)"""
        
        elif entity == "circle":
            return f"""(defun c:{command_name} ( / center radius)
  ;; {parsed['description']}
  (setq center (getpoint "Specify center point: "))
  (setq radius (getdist center "Specify radius: "))
  (command "CIRCLE" center radius)
  (princ)
)"""
        
        elif entity == "rectangle":
            return f"""(defun c:{command_name} ( / pt1 pt2)
  ;; {parsed['description']}
  (setq pt1 (getpoint "Specify first corner: "))
  (setq pt2 (getcorner pt1 "Specify opposite corner: "))
  (command "RECTANGLE" pt1 pt2)
  (princ)
)"""
        
        else:
            return f"""(defun c:{command_name} ( / )
  ;; {parsed['description']}
  (princ "Drawing {entity}...")
  (command "{entity.upper()}")
  (princ)
)"""
    
    def _create_advanced_drawing_command(self, entity: str, parsed: Dict[str, Any]) -> str:
        """Create advanced drawing command with error handling and validation."""
        command_name = parsed["command_name"]
        
        base_code = self._create_basic_drawing_command(entity, parsed)
        
        # Add error handling wrapper
        return f"""(defun c:{command_name} ( / pt1 pt2 center radius result)
  ;; {parsed['description']} (Advanced version with error handling)
  
  ;; Check if AutoCAD is in correct state
  (if (not (= (getvar "CMDACTIVE") 0))
    (progn
      (princ "\\nError: Another command is active. Please finish current command first.")
      (exit)
    )
  )
  
  ;; Set appropriate layer and properties
  (setvar "CLAYER" "0")  ; Set to layer 0 by default
  
  ;; Execute main operation with error handling
  (if (vl-catch-all-error-p
        (setq result (vl-catch-all-apply
          '(lambda ()
             {self._extract_main_operation(base_code)}
           )
          nil
        ))
      )
    (progn
      (princ "\\nError occurred during drawing operation.")
      (princ (vl-catch-all-error-message result))
    )
    (progn
      (princ "\\nDrawing operation completed successfully.")
    )
  )
  (princ)
)"""
    
    def _extract_main_operation(self, code: str) -> str:
        """Extract main operation from basic code for error handling."""
        # Extract lines between the function definition and (princ)
        lines = code.split('\n')
        main_lines = []
        in_main = False
        
        for line in lines:
            if line.strip().startswith('(setq') or line.strip().startswith('(command'):
                in_main = True
            if in_main and not line.strip() == '(princ)':
                main_lines.append('  ' + line.strip())
            elif line.strip() == '(princ)':
                break
        
        return '\n'.join(main_lines)
    
    def _generate_selection_code(self, parsed: Dict[str, Any], complexity: str) -> Dict[str, Any]:
        """Generate code for selection operations."""
        command_name = parsed["command_name"]
        
        code = f"""(defun c:{command_name} ( / ss i ent count)
  ;; {parsed['description']}
  
  (princ "\\nSelect entities to process: ")
  (setq ss (ssget))
  
  (if ss
    (progn
      (setq count (sslength ss))
      (princ (strcat "\\nSelected " (itoa count) " entities."))
      
      ;; Process each entity
      (setq i 0)
      (repeat count
        (setq ent (ssname ss i))
        ;; Add your processing code here
        (princ (strcat "\\nProcessing entity " (itoa (1+ i)) "..."))
        (setq i (1+ i))
      )
      (princ "\\nSelection processing complete.")
    )
    (princ "\\nNo entities selected.")
  )
  (princ)
)"""
        
        return {
            "code": code,
            "language": "autolisp",
            "command_name": command_name,
            "description": f"AutoLISP command to {parsed['description']}",
            "usage_example": f"(c:{command_name})",
            "notes": [
                "This command prompts for entity selection",
                "Modify the processing section for specific operations",
                "Use (entget ent) to access entity properties"
            ]
        }
    
    def _generate_modification_code(self, parsed: Dict[str, Any], complexity: str) -> Dict[str, Any]:
        """Generate code for modification operations."""
        command_name = parsed["command_name"]
        
        # Determine modification type
        desc_lower = parsed["description"].lower()
        if "move" in desc_lower:
            operation = "MOVE"
        elif "copy" in desc_lower:
            operation = "COPY"
        elif "rotate" in desc_lower:
            operation = "ROTATE"
        elif "scale" in desc_lower:
            operation = "SCALE"
        else:
            operation = "MODIFY"
        
        code = f"""(defun c:{command_name} ( / ss base-pt dest-pt)
  ;; {parsed['description']}
  
  (princ "\\nSelect entities to {operation.lower()}: ")
  (setq ss (ssget))
  
  (if ss
    (progn
      (setq base-pt (getpoint "\\nSpecify base point: "))
      (setq dest-pt (getpoint base-pt "\\nSpecify destination point: "))
      
      (command "{operation}" ss "" base-pt dest-pt)
      (princ (strcat "\\n{operation.capitalize()} operation completed on " 
                     (itoa (sslength ss)) " entities."))
    )
    (princ "\\nNo entities selected.")
  )
  (princ)
)"""
        
        return {
            "code": code,
            "language": "autolisp", 
            "command_name": command_name,
            "description": f"AutoLISP command to {parsed['description']}",
            "usage_example": f"(c:{command_name})",
            "notes": [
                f"Uses AutoCAD's {operation} command",
                "Prompts for entity selection and points",
                "Works with any selectable entities"
            ]
        }
    
    def _generate_batch_code(self, parsed: Dict[str, Any], complexity: str) -> Dict[str, Any]:
        """Generate code for batch operations."""
        command_name = parsed["command_name"]
        
        code = f"""(defun c:{command_name} ( / ss i ent count processed-count)
  ;; {parsed['description']}
  
  (princ "\\nSelect entities for batch processing: ")
  (setq ss (ssget))
  (setq processed-count 0)
  
  (if ss
    (progn
      (setq count (sslength ss))
      (princ (strcat "\\nProcessing " (itoa count) " entities..."))
      
      ;; Process each entity
      (setq i 0)
      (repeat count
        (setq ent (ssname ss i))
        
        ;; Add your batch processing logic here
        (if (batch-process-entity ent)
          (setq processed-count (1+ processed-count))
        )
        
        ;; Progress indicator
        (if (= (rem (1+ i) 10) 0)
          (princ (strcat "\\nProcessed " (itoa (1+ i)) " of " (itoa count) " entities..."))
        )
        
        (setq i (1+ i))
      )
      
      (princ (strcat "\\nBatch processing complete. Successfully processed " 
                     (itoa processed-count) " of " (itoa count) " entities."))
    )
    (princ "\\nNo entities selected.")
  )
  (princ)
)

;; Helper function for processing individual entities
(defun batch-process-entity (ent / ent-data)
  ;; {parsed['description']} - Individual entity processing
  (setq ent-data (entget ent))
  (if ent-data
    (progn
      ;; Add specific processing logic here
      ;; Example: Change layer, color, etc.
      ;; (entmod (subst (cons 8 "NEW-LAYER") (assoc 8 ent-data) ent-data))
      T  ; Return success
    )
    nil  ; Return failure
  )
)"""
        
        return {
            "code": code,
            "language": "autolisp",
            "command_name": command_name, 
            "description": f"AutoLISP command to {parsed['description']}",
            "usage_example": f"(c:{command_name})",
            "notes": [
                "Includes progress indicator for large selections",
                "Modify batch-process-entity function for specific operations",
                "Returns count of successfully processed entities",
                "Handles errors gracefully for individual entities"
            ]
        }
    
    def _generate_generic_code(self, parsed: Dict[str, Any], complexity: str) -> Dict[str, Any]:
        """Generate generic AutoLISP command code."""
        command_name = parsed["command_name"]
        
        code = f"""(defun c:{command_name} ( / )
  ;; {parsed['description']}
  
  (princ "\\nExecuting {command_name} command...")
  
  ;; Add your AutoLISP code here
  ;; Examples:
  ;; (setq pt (getpoint "Pick a point: "))
  ;; (setq ss (ssget "Select entities: "))
  ;; (command "COMMANDNAME" parameters)
  
  (princ "\\nCommand completed.")
  (princ)
)"""
        
        return {
            "code": code,
            "language": "autolisp",
            "command_name": command_name,
            "description": f"AutoLISP command template for {parsed['description']}",
            "usage_example": f"(c:{command_name})",
            "notes": [
                "Template provides basic command structure",
                "Add specific AutoLISP logic in the marked section",
                "Use (getpoint), (ssget), (command) for user interaction"
            ]
        }
    
    def get_function_library(self) -> Dict[str, Any]:
        """Get available AutoLISP function templates."""
        return {
            "functions": {
                name: {
                    "name": func.name,
                    "parameters": func.parameters,
                    "description": func.description,
                    "examples": func.examples
                }
                for name, func in self.functions.items()
            },
            "templates": list(self.templates.keys()),
            "patterns": list(self.patterns.keys())
        }
    
    def validate_syntax(self, code: str) -> Dict[str, Any]:
        """Basic AutoLISP syntax validation."""
        issues = []
        
        # Check parentheses balance
        open_parens = code.count('(')
        close_parens = code.count(')')
        if open_parens != close_parens:
            issues.append(f"Unbalanced parentheses: {open_parens} open, {close_parens} close")
        
        # Check for common issues
        if 'defun' not in code.lower():
            issues.append("No function definition found (missing defun)")
        
        if '(princ)' not in code:
            issues.append("Missing (princ) at end of command function")
        
        # Check for proper command structure
        if re.search(r'defun\s+c:', code):
            if not re.search(r'\(\s*princ\s*\)', code):
                issues.append("Command function should end with (princ)")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "suggestions": [
                "Ensure all parentheses are balanced",
                "Command functions should start with (defun c:commandname",
                "End command functions with (princ)"
            ] if issues else ["Code syntax appears valid"]
        }