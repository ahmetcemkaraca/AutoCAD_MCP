"""
API Documentation Generator for AutoCAD Projects.

Generates comprehensive API documentation with cross-references,
examples, and interactive elements.
"""

import ast
import inspect
import logging
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class APIElement:
    """Represents an API element (function, class, method)."""
    name: str
    type: str  # 'function', 'class', 'method', 'property'
    signature: str
    docstring: str
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    returns: Optional[str] = None
    raises: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    see_also: List[str] = field(default_factory=list)
    since_version: Optional[str] = None
    deprecated: bool = False
    source_file: str = ""
    line_number: int = 0
    parent: Optional[str] = None


@dataclass
class APIModule:
    """Represents a complete API module."""
    name: str
    description: str
    elements: List[APIElement] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    version: str = "1.0.0"


class APIDocumenter:
    """Advanced API documentation generator."""
    
    def __init__(self):
        self.modules: Dict[str, APIModule] = {}
        self.cross_references: Dict[str, Set[str]] = {}
        self.autocad_api_map = self._initialize_autocad_api_mapping()
    
    def _initialize_autocad_api_mapping(self) -> Dict[str, Dict[str, Any]]:
        """Initialize AutoCAD API mapping for enhanced documentation."""
        return {
            "AddLine": {
                "category": "Drawing",
                "description": "Creates a line entity in AutoCAD",
                "autocad_command": "LINE",
                "related": ["AddPolyline", "AddCircle"],
                "complexity": "basic"
            },
            "AddCircle": {
                "category": "Drawing", 
                "description": "Creates a circle entity in AutoCAD",
                "autocad_command": "CIRCLE",
                "related": ["AddArc", "AddEllipse"],
                "complexity": "basic"
            },
            "AddExtrudedSolid": {
                "category": "3D Modeling",
                "description": "Creates a 3D solid by extruding a profile",
                "autocad_command": "EXTRUDE",
                "related": ["AddRevolvedSolid", "Union"],
                "complexity": "advanced"
            }
        }
    
    def analyze_project_api(self, project_path: str) -> Dict[str, APIModule]:
        """Analyze entire project and extract API documentation."""
        project_path = Path(project_path)
        
        # Find all Python files
        python_files = list(project_path.glob("src/**/*.py"))
        
        for py_file in python_files:
            try:
                module = self._analyze_module(py_file, project_path)
                if module:
                    self.modules[module.name] = module
            except Exception as e:
                logger.warning(f"Failed to analyze {py_file}: {e}")
        
        # Build cross-references
        self._build_cross_references()
        
        return self.modules
    
    def _analyze_module(self, file_path: Path, project_root: Path) -> Optional[APIModule]:
        """Analyze a single Python module."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source)
            
            # Get module name
            relative_path = file_path.relative_to(project_root)
            module_name = str(relative_path).replace('\\', '.').replace('/', '.').replace('.py', '')
            
            # Extract module docstring
            module_docstring = ast.get_docstring(tree) or ""
            
            module = APIModule(
                name=module_name,
                description=module_docstring
            )
            
            # Analyze AST nodes
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
                    element = self._extract_function_element(node, str(file_path))
                    module.elements.append(element)
                
                elif isinstance(node, ast.ClassDef):
                    class_element = self._extract_class_element(node, str(file_path))
                    module.elements.append(class_element)
                    
                    # Extract methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and not item.name.startswith('_'):
                            method_element = self._extract_function_element(item, str(file_path))
                            method_element.type = "method"
                            method_element.parent = node.name
                            module.elements.append(method_element)
                
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    import_str = self._extract_import_string(node)
                    if import_str:
                        module.imports.append(import_str)
            
            return module
            
        except Exception as e:
            logger.error(f"Error analyzing module {file_path}: {e}")
            return None
    
    def _extract_function_element(self, node: ast.FunctionDef, source_file: str) -> APIElement:
        """Extract API element from function AST node."""
        # Build signature
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {ast.unparse(arg.annotation)}"
            args.append(arg_str)
        
        # Add defaults
        defaults = node.args.defaults
        if defaults:
            num_defaults = len(defaults)
            for i, default in enumerate(defaults):
                arg_index = len(args) - num_defaults + i
                if arg_index >= 0:
                    args[arg_index] += f" = {ast.unparse(default)}"
        
        signature = f"{node.name}({', '.join(args)})"
        
        # Add return annotation
        if node.returns:
            signature += f" -> {ast.unparse(node.returns)}"
        
        # Extract docstring and parse it
        docstring = ast.get_docstring(node) or ""
        parsed_doc = self._parse_enhanced_docstring(docstring)
        
        return APIElement(
            name=node.name,
            type="function",
            signature=signature,
            docstring=docstring,
            parameters=parsed_doc["parameters"],
            returns=parsed_doc["returns"],
            raises=parsed_doc["raises"],
            examples=parsed_doc["examples"],
            see_also=parsed_doc["see_also"],
            since_version=parsed_doc.get("since_version"),
            deprecated=parsed_doc.get("deprecated", False),
            source_file=source_file,
            line_number=node.lineno
        )
    
    def _extract_class_element(self, node: ast.ClassDef, source_file: str) -> APIElement:
        """Extract API element from class AST node."""
        docstring = ast.get_docstring(node) or ""
        parsed_doc = self._parse_enhanced_docstring(docstring)
        
        # Get inheritance
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(f"{ast.unparse(base)}")
        
        signature = f"class {node.name}"
        if bases:
            signature += f"({', '.join(bases)})"
        
        return APIElement(
            name=node.name,
            type="class",
            signature=signature,
            docstring=docstring,
            parameters=parsed_doc["parameters"],
            examples=parsed_doc["examples"],
            see_also=parsed_doc["see_also"],
            since_version=parsed_doc.get("since_version"),
            deprecated=parsed_doc.get("deprecated", False),
            source_file=source_file,
            line_number=node.lineno
        )
    
    def _extract_import_string(self, node) -> Optional[str]:
        """Extract import statement as string."""
        try:
            if isinstance(node, ast.Import):
                return f"import {', '.join(alias.name for alias in node.names)}"
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = ', '.join(alias.name for alias in node.names)
                return f"from {module} import {names}"
        except:
            pass
        return None
    
    def _parse_enhanced_docstring(self, docstring: str) -> Dict[str, Any]:
        """Parse enhanced docstring with multiple sections."""
        result = {
            "parameters": [],
            "returns": None,
            "raises": [],
            "examples": [],
            "see_also": [],
            "since_version": None,
            "deprecated": False
        }
        
        if not docstring:
            return result
        
        lines = docstring.split('\\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            # Section headers
            if line.lower().startswith(('args:', 'arguments:', 'parameters:')):
                current_section = 'parameters'
                continue
            elif line.lower().startswith('returns:'):
                current_section = 'returns'
                continue
            elif line.lower().startswith('raises:'):
                current_section = 'raises'
                continue
            elif line.lower().startswith(('example:', 'examples:')):
                current_section = 'examples'
                continue
            elif line.lower().startswith('see also:'):
                current_section = 'see_also'
                continue
            elif line.lower().startswith('since:'):
                current_section = 'since'
                continue
            elif line.lower().startswith('deprecated'):
                result["deprecated"] = True
                continue
            
            # Parse content based on current section
            if current_section == 'parameters' and ':' in line:
                param_parts = line.split(':', 1)
                if len(param_parts) == 2:
                    param_name = param_parts[0].strip()
                    param_desc = param_parts[1].strip()
                    
                    # Extract type information
                    param_type = None
                    if '(' in param_name and ')' in param_name:
                        type_start = param_name.find('(')
                        type_end = param_name.find(')')
                        param_type = param_name[type_start+1:type_end]
                        param_name = param_name[:type_start].strip()
                    
                    result["parameters"].append({
                        'name': param_name,
                        'type': param_type,
                        'description': param_desc
                    })
            
            elif current_section == 'returns' and line:
                result["returns"] = line
            
            elif current_section == 'raises' and line:
                result["raises"].append(line)
            
            elif current_section == 'examples' and line:
                result["examples"].append(line)
            
            elif current_section == 'see_also' and line:
                # Split comma-separated references
                refs = [ref.strip() for ref in line.split(',')]
                result["see_also"].extend(refs)
            
            elif current_section == 'since' and line:
                result["since_version"] = line
        
        return result
    
    def _build_cross_references(self):
        """Build cross-reference mapping between API elements."""
        self.cross_references = {}
        
        # Collect all element names
        all_elements = {}
        for module in self.modules.values():
            for element in module.elements:
                full_name = f"{module.name}.{element.name}"
                all_elements[element.name] = full_name
                all_elements[full_name] = full_name
        
        # Build references
        for module in self.modules.values():
            for element in module.elements:
                refs = set()
                
                # References from see_also
                refs.update(element.see_also)
                
                # References from docstring
                docstring_lower = element.docstring.lower()
                for name, full_name in all_elements.items():
                    if name != element.name and name.lower() in docstring_lower:
                        refs.add(full_name)
                
                # AutoCAD API references
                for autocad_func in self.autocad_api_map:
                    if autocad_func.lower() in element.name.lower():
                        refs.update(self.autocad_api_map[autocad_func].get("related", []))
                
                if refs:
                    full_element_name = f"{module.name}.{element.name}"
                    self.cross_references[full_element_name] = refs
    
    def generate_comprehensive_documentation(self, output_dir: str, 
                                           formats: List[str] = None) -> Dict[str, str]:
        """Generate comprehensive API documentation in multiple formats."""
        if formats is None:
            formats = ["html", "markdown", "json"]
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        generated_files = {}
        
        for format_type in formats:
            if format_type == "html":
                file_path = self._generate_html_documentation(output_path)
                generated_files["html"] = file_path
            elif format_type == "markdown":
                file_path = self._generate_markdown_documentation(output_path)
                generated_files["markdown"] = file_path
            elif format_type == "json":
                file_path = self._generate_json_documentation(output_path)
                generated_files["json"] = file_path
        
        # Generate index file
        self._generate_index_file(output_path, generated_files)
        
        return generated_files
    
    def _generate_html_documentation(self, output_path: Path) -> str:
        """Generate HTML documentation with interactive features."""
        html_file = output_path / "api_documentation.html"
        
        # Group elements by category
        categories = self._categorize_elements()
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AutoCAD API Documentation</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #2c3e50; color: white; padding: 20px 0; margin-bottom: 30px; }}
        .nav {{ background: #34495e; padding: 10px 0; position: sticky; top: 0; }}
        .nav ul {{ list-style: none; margin: 0; padding: 0; display: flex; }}
        .nav li {{ margin-right: 20px; }}
        .nav a {{ color: white; text-decoration: none; padding: 8px 16px; border-radius: 4px; }}
        .nav a:hover {{ background: #2c3e50; }}
        .category {{ margin-bottom: 40px; }}
        .category h2 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        .element {{ margin-bottom: 30px; border-left: 4px solid #3498db; padding-left: 20px; }}
        .signature {{ background: #f8f9fa; padding: 10px; border-radius: 4px; font-family: monospace; }}
        .deprecated {{ border-left-color: #e74c3c; background: #fdf2f2; }}
        .parameters {{ margin-top: 15px; }}
        .parameter {{ margin: 8px 0; }}
        .cross-refs {{ margin-top: 15px; }}
        .cross-refs a {{ color: #3498db; text-decoration: none; margin-right: 10px; }}
        .search-box {{ margin-bottom: 20px; }}
        .search-box input {{ width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }}
        .example {{ background: #f1f8ff; border-left: 4px solid #0969da; padding: 10px; margin: 10px 0; }}
    </style>
    <script>
        function filterElements(searchTerm) {{
            const elements = document.querySelectorAll('.element');
            elements.forEach(element => {{
                const text = element.textContent.toLowerCase();
                element.style.display = text.includes(searchTerm.toLowerCase()) ? 'block' : 'none';
            }});
        }}
        
        function scrollToCategory(category) {{
            document.getElementById('category-' + category).scrollIntoView({{ behavior: 'smooth' }});
        }}
    </script>
</head>
<body>
    <div class="header">
        <div class="container">
            <h1>AutoCAD API Documentation</h1>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
    
    <div class="nav">
        <div class="container">
            <ul>
                {self._generate_nav_links(categories)}
            </ul>
        </div>
    </div>
    
    <div class="container">
        <div class="search-box">
            <input type="text" placeholder="Search API..." onkeyup="filterElements(this.value)">
        </div>
        
        {self._generate_html_categories(categories)}
    </div>
</body>
</html>"""
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Generated HTML documentation: {html_file}")
        return str(html_file)
    
    def _categorize_elements(self) -> Dict[str, List[APIElement]]:
        """Categorize API elements by functionality."""
        categories = {
            "Drawing": [],
            "3D Modeling": [],
            "Utilities": [],
            "Testing": [],
            "Project Management": [],
            "Other": []
        }
        
        for module in self.modules.values():
            for element in module.elements:
                category = "Other"
                
                # Categorize based on name patterns
                name_lower = element.name.lower()
                if any(keyword in name_lower for keyword in ['draw', 'add', 'create', 'line', 'circle']):
                    category = "Drawing"
                elif any(keyword in name_lower for keyword in ['extrude', 'revolve', 'union', 'subtract', '3d']):
                    category = "3D Modeling"
                elif any(keyword in name_lower for keyword in ['test', 'mock', 'assert']):
                    category = "Testing"
                elif any(keyword in name_lower for keyword in ['project', 'template', 'scaffold']):
                    category = "Project Management"
                elif any(keyword in name_lower for keyword in ['util', 'helper', 'manager']):
                    category = "Utilities"
                
                # Check AutoCAD API mapping
                for autocad_func, info in self.autocad_api_map.items():
                    if autocad_func.lower() in name_lower:
                        category = info["category"]
                        break
                
                categories[category].append(element)
        
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}
    
    def _generate_nav_links(self, categories: Dict[str, List[APIElement]]) -> str:
        """Generate navigation links for HTML."""
        links = []
        for category in categories.keys():
            links.append(f'<li><a href="#category-{category.lower().replace(" ", "-")}">{category}</a></li>')
        return '\\n'.join(links)
    
    def _generate_html_categories(self, categories: Dict[str, List[APIElement]]) -> str:
        """Generate HTML for all categories."""
        html_parts = []
        
        for category, elements in categories.items():
            category_id = category.lower().replace(' ', '-')
            html_parts.append(f'<div class="category" id="category-{category_id}">')
            html_parts.append(f'<h2>{category} ({len(elements)} items)</h2>')
            
            for element in elements:
                deprecated_class = " deprecated" if element.deprecated else ""
                html_parts.append(f'<div class="element{deprecated_class}">')
                html_parts.append(f'<h3>{element.name}</h3>')
                html_parts.append(f'<div class="signature"><code>{element.signature}</code></div>')
                
                if element.docstring:
                    html_parts.append(f'<p>{element.docstring}</p>')
                
                if element.parameters:
                    html_parts.append('<div class="parameters"><h4>Parameters:</h4>')
                    for param in element.parameters:
                        param_type = f" ({param['type']})" if param.get('type') else ""
                        html_parts.append(f'<div class="parameter"><code>{param["name"]}</code>{param_type}: {param["description"]}</div>')
                    html_parts.append('</div>')
                
                if element.returns:
                    html_parts.append(f'<p><strong>Returns:</strong> {element.returns}</p>')
                
                if element.examples:
                    html_parts.append('<h4>Examples:</h4>')
                    for example in element.examples:
                        html_parts.append(f'<div class="example"><pre><code>{example}</code></pre></div>')
                
                # Cross-references
                full_name = f"{element.parent or 'module'}.{element.name}"
                if full_name in self.cross_references:
                    refs = self.cross_references[full_name]
                    if refs:
                        html_parts.append('<div class="cross-refs"><strong>See also:</strong> ')
                        ref_links = [f'<a href="#{ref.replace(".", "-")}">{ref}</a>' for ref in refs]
                        html_parts.append(' '.join(ref_links))
                        html_parts.append('</div>')
                
                html_parts.append('</div>')
            
            html_parts.append('</div>')
        
        return '\\n'.join(html_parts)
    
    def _generate_markdown_documentation(self, output_path: Path) -> str:
        """Generate Markdown documentation."""
        md_file = output_path / "api_documentation.md"
        
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write("# AutoCAD API Documentation\\n\\n")
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n\\n")
            
            # Table of contents
            f.write("## Table of Contents\\n\\n")
            categories = self._categorize_elements()
            for category in categories.keys():
                anchor = category.lower().replace(' ', '-')
                f.write(f"- [{category}](#{anchor})\\n")
            f.write("\\n")
            
            # Generate content for each category
            for category, elements in categories.items():
                anchor = category.lower().replace(' ', '-')
                f.write(f"## {category}\\n\\n")
                
                for element in elements:
                    f.write(f"### `{element.name}`\\n\\n")
                    
                    if element.deprecated:
                        f.write("**⚠️ DEPRECATED**\\n\\n")
                    
                    f.write(f"```python\\n{element.signature}\\n```\\n\\n")
                    
                    if element.docstring:
                        f.write(f"{element.docstring}\\n\\n")
                    
                    if element.parameters:
                        f.write("**Parameters:**\\n\\n")
                        for param in element.parameters:
                            param_type = f" ({param['type']})" if param.get('type') else ""
                            f.write(f"- `{param['name']}`{param_type}: {param['description']}\\n")
                        f.write("\\n")
                    
                    if element.returns:
                        f.write(f"**Returns:** {element.returns}\\n\\n")
                    
                    if element.examples:
                        f.write("**Examples:**\\n\\n")
                        for example in element.examples:
                            f.write(f"```python\\n{example}\\n```\\n\\n")
                    
                    f.write("---\\n\\n")
        
        logger.info(f"Generated Markdown documentation: {md_file}")
        return str(md_file)
    
    def _generate_json_documentation(self, output_path: Path) -> str:
        """Generate JSON documentation for programmatic access."""
        json_file = output_path / "api_documentation.json"
        
        api_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_modules": len(self.modules),
                "total_elements": sum(len(module.elements) for module in self.modules.values())
            },
            "modules": {},
            "cross_references": {k: list(v) for k, v in self.cross_references.items()},
            "autocad_mapping": self.autocad_api_map
        }
        
        for module_name, module in self.modules.items():
            api_data["modules"][module_name] = {
                "name": module.name,
                "description": module.description,
                "elements": [
                    {
                        "name": element.name,
                        "type": element.type,
                        "signature": element.signature,
                        "docstring": element.docstring,
                        "parameters": element.parameters,
                        "returns": element.returns,
                        "raises": element.raises,
                        "examples": element.examples,
                        "see_also": element.see_also,
                        "since_version": element.since_version,
                        "deprecated": element.deprecated,
                        "source_file": element.source_file,
                        "line_number": element.line_number,
                        "parent": element.parent
                    }
                    for element in module.elements
                ]
            }
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(api_data, f, indent=2)
        
        logger.info(f"Generated JSON documentation: {json_file}")
        return str(json_file)
    
    def _generate_index_file(self, output_path: Path, generated_files: Dict[str, str]):
        """Generate index file with links to all documentation."""
        index_file = output_path / "index.html"
        
        index_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>AutoCAD API Documentation</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }}
        .card {{ border: 1px solid #ddd; padding: 20px; margin: 20px 0; border-radius: 8px; }}
        .card h3 {{ color: #2c3e50; margin-top: 0; }}
        .card a {{ color: #3498db; text-decoration: none; }}
        .card a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>AutoCAD API Documentation</h1>
    <p>Choose your preferred documentation format:</p>
    
    <div class="card">
        <h3>📖 HTML Documentation</h3>
        <p>Interactive documentation with search and navigation</p>
        <a href="api_documentation.html">View HTML Documentation</a>
    </div>
    
    <div class="card">
        <h3>📝 Markdown Documentation</h3>
        <p>Readable documentation for GitHub and text editors</p>
        <a href="api_documentation.md">View Markdown Documentation</a>
    </div>
    
    <div class="card">
        <h3>🔧 JSON API</h3>
        <p>Machine-readable API data for tools and scripts</p>
        <a href="api_documentation.json">Download JSON Data</a>
    </div>
    
    <hr>
    <p><small>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small></p>
</body>
</html>"""
        
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(index_content)
        
        logger.info(f"Generated documentation index: {index_file}")
    
    def generate_api_diff(self, old_api_data: Dict[str, Any], new_api_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate API diff between two versions."""
        diff = {
            "added": [],
            "removed": [],
            "modified": [],
            "deprecated": [],
            "summary": {}
        }
        
        old_elements = set()
        new_elements = set()
        
        # Collect element names
        for module_data in old_api_data.get("modules", {}).values():
            for element in module_data.get("elements", []):
                old_elements.add(f"{module_data['name']}.{element['name']}")
        
        for module_data in new_api_data.get("modules", {}).values():
            for element in module_data.get("elements", []):
                new_elements.add(f"{module_data['name']}.{element['name']}")
        
        # Find differences
        diff["added"] = list(new_elements - old_elements)
        diff["removed"] = list(old_elements - new_elements)
        
        # Summary
        diff["summary"] = {
            "total_added": len(diff["added"]),
            "total_removed": len(diff["removed"]),
            "total_modified": len(diff["modified"]),
            "breaking_changes": len(diff["removed"]) > 0
        }
        
        return diff