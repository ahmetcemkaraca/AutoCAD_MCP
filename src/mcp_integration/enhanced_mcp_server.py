"""
Enhanced MCP Server for Master AutoCAD Coder
==========================================

Extended MCP server that combines existing manufacturing functionality
with new interactive development tools for VS Code integration.
Maintains 100% backward compatibility while adding enhanced capabilities.
"""

import logging
import asyncio
import time
import json
from typing import Any, Dict, List, Optional
from mcp.server import FastMCP
from mcp import McpError
from mcp.types import Tool

# Import enhanced AutoCAD functionality and local modules
from ..enhanced_autocad.compatibility_layer import Autocad
from .context_manager import ContextManager
from .security_manager import SecurityManager
from ..inspection.object_inspector import ObjectInspector, InspectionDepth
from ..inspection.property_analyzer import PropertyAnalyzer
from ..inspection.method_discoverer import MethodDiscoverer
from ..inspection.intellisense_provider import IntelliSenseProvider

logger = logging.getLogger(__name__)


class EnhancedMCPServer:
    """
    Enhanced MCP server combining manufacturing and development capabilities.
    """

    def __init__(self):
        """Initialize enhanced MCP server."""
        self.mcp = FastMCP("AutoCAD Master Coder")
        self.context_manager = ContextManager()
        self.security_manager = SecurityManager()
        self.autocad_wrapper = None
        
        # Initialize interactive components (lazy import to avoid circular dependency)
        self.python_repl = None
        self.execution_engine = None

        # Initialize inspection components
        self.object_inspector = ObjectInspector(self.autocad_wrapper)
        self.property_analyzer = PropertyAnalyzer()
        self.method_discoverer = MethodDiscoverer()
        self.intellisense_provider = IntelliSenseProvider(self.autocad_wrapper)
        
        # Initialize Week 5 advanced components (lazy init)
        self.debugger = None
        self.error_diagnostics = None
        self.performance_analyzer = None
        
        # Initialize Phase 3 code generation components (lazy init)
        self.autolisp_generator = None
        self.python_generator = None
        self.vba_generator = None
        self.template_manager = None
        self.language_coordinator = None
        self.validation_engine = None
        
        # Initialize Phase 4 testing and project tools (lazy init)
        self.test_framework = None
        self.test_generator = None
        self.performance_tester = None
        self.project_scaffolder = None
        self.dependency_manager = None
        self.documentation_generator = None

        # Register all MCP tools
        self._register_manufacturing_tools()
        self._register_development_tools()
        self._register_interactive_tools()
        self._register_inspection_tools()
        self._register_debugging_tools()
        self._register_diagnostics_tools()
        self._register_performance_tools()
        self._register_code_generation_tools()
        self._register_testing_tools()
        self._register_project_tools()

        logger.info("Enhanced MCP Server initialized with interactive capabilities")

    def _get_autocad_wrapper(self) -> Autocad:
        """Get AutoCAD wrapper instance with caching."""
        if not self.autocad_wrapper:
            self.autocad_wrapper = Autocad()
        return self.autocad_wrapper

    def _get_python_repl(self):
        """Get Python REPL instance with lazy initialization."""
        if not self.python_repl:
            from ..interactive.python_repl import PythonREPL
            self.python_repl = PythonREPL(
                autocad_wrapper=self.autocad_wrapper,
                security_manager=self.security_manager,
                context_manager=self.context_manager
            )
        return self.python_repl

    def _get_execution_engine(self):
        """Get execution engine instance with lazy initialization."""
        if not self.execution_engine:
            from ..interactive.execution_engine import ExecutionEngine
            self.execution_engine = ExecutionEngine(
                security_manager=self.security_manager
            )
        return self.execution_engine

    def _get_debugger(self):
        """Get debugger instance with lazy initialization."""
        if not self.debugger:
            from ..interactive.debugger import AutoCADDebugger
            self.debugger = AutoCADDebugger(
                object_inspector=self.object_inspector,
                error_handler=None  # Will be initialized if needed
            )
        return self.debugger

    def _get_error_diagnostics(self):
        """Get error diagnostics instance with lazy initialization."""
        if not self.error_diagnostics:
            from ..interactive.error_diagnostics import ErrorDiagnostics
            self.error_diagnostics = ErrorDiagnostics(
                object_inspector=self.object_inspector,
                error_handler=None
            )
        return self.error_diagnostics

    def _get_performance_analyzer(self):
        """Get performance analyzer instance with lazy initialization."""
        if not self.performance_analyzer:
            from ..interactive.performance_analyzer import PerformanceAnalyzer
            self.performance_analyzer = PerformanceAnalyzer(
                object_inspector=self.object_inspector
            )
        return self.performance_analyzer

    def _get_autolisp_generator(self):
        """Get AutoLISP generator instance with lazy initialization."""
        if not self.autolisp_generator:
            from ..code_generation.autolisp_generator import AutoLISPGenerator
            self.autolisp_generator = AutoLISPGenerator()
        return self.autolisp_generator

    def _get_python_generator(self):
        """Get Python generator instance with lazy initialization."""
        if not self.python_generator:
            from ..code_generation.python_generator import PythonGenerator
            self.python_generator = PythonGenerator()
        return self.python_generator

    def _get_vba_generator(self):
        """Get VBA generator instance with lazy initialization."""
        if not self.vba_generator:
            from ..code_generation.vba_generator import VBAGenerator
            self.vba_generator = VBAGenerator()
        return self.vba_generator

    def _get_template_manager(self):
        """Get template manager instance with lazy initialization."""
        if not self.template_manager:
            from ..code_generation.template_manager import TemplateManager
            self.template_manager = TemplateManager()
        return self.template_manager

    def _get_language_coordinator(self):
        """Get language coordinator instance with lazy initialization."""
        if not self.language_coordinator:
            from ..code_generation.language_coordinator import LanguageCoordinator
            self.language_coordinator = LanguageCoordinator()
        return self.language_coordinator

    def _get_validation_engine(self):
        """Get validation engine instance with lazy initialization."""
        if not self.validation_engine:
            from ..code_generation.validation_engine import ValidationEngine
            self.validation_engine = ValidationEngine()
        return self.validation_engine
    
    def _get_test_framework(self):
        """Get test framework instance with lazy initialization."""
        if not self.test_framework:
            from ..testing.autocad_test_framework import AutoCADTestFramework
            self.test_framework = AutoCADTestFramework(mock_mode=True)
        return self.test_framework
    
    def _get_test_generator(self):
        """Get test generator instance with lazy initialization."""
        if not self.test_generator:
            from ..testing.test_generators import TestGenerator
            self.test_generator = TestGenerator()
        return self.test_generator
    
    def _get_performance_tester(self):
        """Get performance tester instance with lazy initialization."""
        if not self.performance_tester:
            from ..testing.performance_tester import PerformanceTester
            self.performance_tester = PerformanceTester()
        return self.performance_tester
    
    def _get_project_scaffolder(self):
        """Get project scaffolder instance with lazy initialization."""
        if not self.project_scaffolder:
            from ..project_templates.project_scaffolder import ProjectScaffolder
            self.project_scaffolder = ProjectScaffolder()
        return self.project_scaffolder
    
    def _get_dependency_manager(self):
        """Get dependency manager instance with lazy initialization."""
        if not self.dependency_manager:
            from ..project_templates.dependency_manager import DependencyManager
            self.dependency_manager = DependencyManager()
        return self.dependency_manager
    
    def _get_documentation_generator(self):
        """Get documentation generator instance with lazy initialization."""
        if not self.documentation_generator:
            from ..project_templates.documentation_generator import DocumentationGenerator
            self.documentation_generator = DocumentationGenerator()
        return self.documentation_generator

    def _register_manufacturing_tools(self):
        """Register existing manufacturing MCP tools (preserved functionality)."""

        @self.mcp.tool()
        def draw_line(start_point: List[float], end_point: List[float]) -> str:
            """
            Draw a line in AutoCAD from start point to end point.

            Args:
                start_point: [x, y, z] coordinates for line start
                end_point: [x, y, z] coordinates for line end

            Returns:
                Success message with entity information
            """
            try:
                acad = self._get_autocad_wrapper()
                entity_id = acad.draw_line(start_point, end_point)
                return f"Line created successfully with entity ID: {entity_id}"
            except Exception as e:
                logger.error(f"Error drawing line: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to draw line: {str(e)}")

        @self.mcp.tool()
        def draw_circle(center: List[float], radius: float) -> str:
            """
            Draw a circle in AutoCAD.

            Args:
                center: [x, y, z] coordinates for circle center
                radius: Circle radius

            Returns:
                Success message with entity information
            """
            try:
                acad = self._get_autocad_wrapper()
                entity_id = acad.draw_circle(center, radius)
                return f"Circle created successfully with entity ID: {entity_id}"
            except Exception as e:
                logger.error(f"Error drawing circle: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to draw circle: {str(e)}")

        @self.mcp.tool()
        def get_autocad_status() -> str:
            """
            Get AutoCAD connection status and basic information.

            Returns:
                JSON string with AutoCAD status information
            """
            try:
                acad = self._get_autocad_wrapper()
                status = acad.get_connection_status()

                if status["connected"]:
                    return f"AutoCAD Status: Connected\nVersion: {status.get('autocad_version', 'Unknown')}\nDocuments: {status.get('documents_count', 0)}"
                else:
                    return "AutoCAD Status: Not Connected\nPlease ensure AutoCAD 2025 is running with an open document"
            except Exception as e:
                logger.error(f"Error getting AutoCAD status: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to get AutoCAD status: {str(e)}")

        # Add more manufacturing tools as needed (surface unfolding, pattern optimization, etc.)
        # These would be migrated from the existing mcp_server.py

    def _register_development_tools(self):
        """Register new development-focused MCP tools."""

        @self.mcp.tool()
        def get_enhanced_connection_status() -> str:
            """
            Get enhanced AutoCAD connection status with diagnostics.

            Returns:
                Detailed connection status with performance metrics
            """
            try:
                acad = self._get_autocad_wrapper()
                status = acad.get_connection_status()
                performance = acad.get_performance_metrics()
                errors = acad.get_error_statistics()

                report_lines = [
                    "=== Enhanced AutoCAD Connection Status ===",
                    f"Connected: {'Yes' if status['connected'] else 'No'}",
                    f"AutoCAD Version: {status.get('autocad_version', 'Unknown')}",
                    f"Documents Open: {status.get('documents_count', 0)}",
                    f"Connection Age: {status.get('connection_age_seconds', 0):.1f} seconds",
                    "",
                    "=== Performance Metrics ===",
                    f"Total Operations: {performance.get('total_operations', 0)}",
                    f"Success Rate: {performance.get('overall_success_rate', 0):.1%}",
                    f"Average Duration: {performance.get('average_operation_duration', 0):.3f}s",
                    f"Operations/Second: {performance.get('operations_per_second', 0):.2f}",
                    "",
                    "=== Error Statistics ===",
                    f"Total Errors: {errors.get('total_errors', 0)}",
                    f"Recent Errors (1h): {errors.get('errors_last_hour', 0)}",
                ]

                if performance.get("performance_warnings"):
                    report_lines.append("\n=== Performance Warnings ===")
                    for warning in performance["performance_warnings"]:
                        report_lines.append(f"⚠️ {warning}")

                return "\n".join(report_lines)

            except Exception as e:
                logger.error(f"Error getting enhanced status: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to get enhanced status: {str(e)}")

        @self.mcp.tool()
        def test_enhanced_wrapper() -> str:
            """
            Test enhanced wrapper functionality and performance.

            Returns:
                Test results and performance comparison
            """
            try:
                acad = self._get_autocad_wrapper()

                # Run basic functionality tests
                test_results = []

                # Test 1: Connection test
                try:
                    status = acad.get_connection_status()
                    test_results.append(
                        f"✅ Connection Test: {'Connected' if status['connected'] else 'Failed'}"
                    )
                except Exception as e:
                    test_results.append(f"❌ Connection Test: Failed - {str(e)}")

                # Test 2: Basic drawing test
                try:
                    entity_id = acad.draw_line([0, 0, 0], [10, 10, 0])
                    test_results.append(f"✅ Drawing Test: Line created (ID: {entity_id})")
                except Exception as e:
                    test_results.append(f"❌ Drawing Test: Failed - {str(e)}")

                # Test 3: Performance metrics test
                try:
                    metrics = acad.get_performance_metrics()
                    test_results.append(
                        f"✅ Performance Metrics: {metrics.get('total_operations', 0)} operations tracked"
                    )
                except Exception as e:
                    test_results.append(f"❌ Performance Metrics: Failed - {str(e)}")

                # Test 4: Error handling test
                try:
                    errors = acad.get_error_statistics()
                    test_results.append(
                        f"✅ Error Handling: {errors.get('total_errors', 0)} errors logged"
                    )
                except Exception as e:
                    test_results.append(f"❌ Error Handling: Failed - {str(e)}")

                return "Enhanced Wrapper Test Results:\n" + "\n".join(test_results)

            except Exception as e:
                logger.error(f"Error testing enhanced wrapper: {e}")
                raise McpError("INTERNAL_ERROR", f"Enhanced wrapper test failed: {str(e)}")

        @self.mcp.tool()
        def execute_simple_python(code: str, session_id: Optional[str] = None) -> str:
            """
            Execute simple Python code in AutoCAD context (secure).

            Args:
                code: Python code to execute
                session_id: Optional session ID for context persistence

            Returns:
                Execution result or error message
            """
            try:
                # Security validation
                if not self.security_manager.validate_python_code(code):
                    raise McpError("SECURITY_ERROR", "Code contains potentially unsafe operations")

                # Get or create session context
                context = self.context_manager.get_session_context(session_id)

                # Prepare execution environment
                acad = self._get_autocad_wrapper()
                exec_globals = {
                    "acad": acad,
                    "app": acad.app,
                    "doc": acad.doc,
                    "model": acad.model,
                    "__builtins__": self.security_manager.get_safe_builtins(),
                }
                exec_globals.update(context.get("variables", {}))

                # Execute code
                result = None
                try:
                    # Try as expression first
                    result = eval(code, exec_globals)
                except SyntaxError:
                    # Execute as statement
                    exec(code, exec_globals)
                    result = "Code executed successfully"

                # Update session context
                context["variables"] = {
                    k: v
                    for k, v in exec_globals.items()
                    if not k.startswith("__") and k not in ["acad", "app", "doc", "model"]
                }
                self.context_manager.update_session_context(session_id, context)

                return f"Result: {result}"

            except Exception as e:
                logger.error(f"Error executing Python code: {e}")
                raise McpError("EXECUTION_ERROR", f"Code execution failed: {str(e)}")

    def _register_interactive_tools(self):
        """Register interactive development MCP tools for REPL and advanced execution."""

        @self.mcp.tool()
        def start_autocad_repl(session_id: Optional[str] = None) -> str:
            """
            Start interactive Python REPL with AutoCAD context.
            
            Args:
                session_id: Optional session identifier (auto-generated if None)
            
            Returns:
                Session startup information and available objects
            """
            try:
                result = self.python_repl.start_repl_session(session_id)
                
                if result["success"]:
                    return f"""REPL Session Started Successfully!
Session ID: {result['session_id']}
Available Objects: {', '.join(result['available_objects'])}
AutoCAD Status: {result['autocad_status']['message']}

Startup Output:
{result['startup_output']}

Ready for interactive Python development with AutoCAD!
Type your Python code and press Enter to execute."""
                else:
                    raise McpError("REPL_ERROR", result["error"])
                    
            except Exception as e:
                logger.error(f"Error starting REPL: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to start REPL: {str(e)}")

        @self.mcp.tool()
        def execute_python_in_autocad(code: str, session_id: Optional[str] = None) -> str:
            """
            Execute Python code in AutoCAD context with persistence.
            
            Args:
                code: Python code to execute
                session_id: REPL session identifier (None for default session)
            
            Returns:
                Execution result with output and timing information
            """
            try:
                # If no session specified, try to create one
                if session_id is None:
                    session_id = "default_session"
                    if session_id not in self.python_repl.active_sessions:
                        self.python_repl.start_repl_session(session_id)
                
                result = self.python_repl.execute_code(code, session_id)
                
                if result["success"]:
                    output_lines = [
                        f"Command #{result.get('command_number', 1)} executed successfully",
                        f"Execution time: {result['execution_time']:.3f}s"
                    ]
                    
                    if result["output"]:
                        output_lines.append(f"Output:\n{result['output']}")
                    
                    if result.get("continuation"):
                        output_lines.append(f"\nWaiting for more input...")
                        output_lines.append(f"Prompt: {result.get('prompt', '...')}")
                    
                    return "\n".join(output_lines)
                else:
                    return f"Execution Error:\n{result.get('error', 'Unknown error')}\n\nExecution time: {result['execution_time']:.3f}s"
                    
            except Exception as e:
                logger.error(f"Error executing Python in REPL: {e}")
                raise McpError("EXECUTION_ERROR", f"REPL execution failed: {str(e)}")

        @self.mcp.tool()
        def get_repl_history(session_id: str, limit: int = 10) -> str:
            """
            Retrieve REPL command history.
            
            Args:
                session_id: REPL session identifier
                limit: Maximum number of history entries to return
            
            Returns:
                Formatted command history
            """
            try:
                result = self.python_repl.get_session_history(session_id, limit)
                
                if result["success"]:
                    if not result["history"]:
                        return f"No command history for session {session_id}"
                    
                    history_lines = [
                        f"Command History for Session: {session_id}",
                        f"Total Commands: {result['total_commands']}",
                        f"Session Age: {result['session_age']:.1f} seconds",
                        f"Showing last {len(result['history'])} commands:",
                        "=" * 50
                    ]
                    
                    for entry in result["history"]:
                        cmd_num = entry["command_number"]
                        timestamp = time.strftime("%H:%M:%S", time.localtime(entry["timestamp"]))
                        code = entry["code"].replace("\n", "\\n")[:100]
                        status = "✅" if entry["success"] else "❌"
                        exec_time = entry["execution_time"]
                        
                        history_lines.append(f"[{cmd_num}] {timestamp} ({exec_time:.3f}s) {status}")
                        history_lines.append(f"    {code}")
                        
                        if entry.get("output"):
                            output = entry["output"][:200].replace("\n", "\\n")
                            history_lines.append(f"    → {output}")
                        history_lines.append("")
                    
                    return "\n".join(history_lines)
                else:
                    return f"Error retrieving history: {result['error']}"
                    
            except Exception as e:
                logger.error(f"Error getting REPL history: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to get REPL history: {str(e)}")

        @self.mcp.tool()
        def clear_repl_session(session_id: str) -> str:
            """
            Clear REPL session and free resources.
            
            Args:
                session_id: REPL session identifier
            
            Returns:
                Clear operation result
            """
            try:
                result = self.python_repl.clear_session(session_id)
                
                if result["success"]:
                    return f"Session {session_id} cleared successfully.\nAutoCAD context reloaded and ready for new commands."
                else:
                    return f"Error clearing session: {result.get('error', 'Unknown error')}"
                    
            except Exception as e:
                logger.error(f"Error clearing REPL session: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to clear REPL session: {str(e)}")

        @self.mcp.tool()
        def stop_repl_session(session_id: str) -> str:
            """
            Stop and remove REPL session.
            
            Args:
                session_id: REPL session identifier
            
            Returns:
                Stop operation result
            """
            try:
                result = self.python_repl.stop_session(session_id)
                
                if result["success"]:
                    return f"REPL session {session_id} stopped and resources freed."
                else:
                    return f"Error stopping session: {result.get('error', 'Session not found')}"
                    
            except Exception as e:
                logger.error(f"Error stopping REPL session: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to stop REPL session: {str(e)}")

    def _register_inspection_tools(self):
        """Register AutoCAD object inspection MCP tools."""

        @self.mcp.tool()
        def inspect_autocad_object(object_name: str, depth: str = "basic") -> str:
            """
            Inspect AutoCAD object with specified depth.
            
            Args:
                object_name: Name of object to inspect ('app', 'doc', 'model', 'acad')
                depth: Inspection depth ('basic', 'detailed', 'comprehensive', 'hierarchical')
            
            Returns:
                Detailed object inspection report
            """
            try:
                # Validate depth parameter
                valid_depths = {"basic": InspectionDepth.BASIC, 
                               "detailed": InspectionDepth.DETAILED,
                               "comprehensive": InspectionDepth.COMPREHENSIVE,
                               "hierarchical": InspectionDepth.HIERARCHICAL}
                
                if depth not in valid_depths:
                    raise McpError("INVALID_PARAMS", f"Invalid depth '{depth}'. Valid options: {list(valid_depths.keys())}")
                
                # Perform inspection
                result = self.object_inspector.inspect_by_name(object_name, valid_depths[depth])
                
                # Format result
                report_lines = [
                    f"=== AutoCAD Object Inspection: {result.object_name} ===",
                    f"Object Type: {result.object_type}",
                    f"Object ID: {result.object_id}",
                    f"Inspection Depth: {result.depth.value}",
                    f"Inspection Time: {result.inspection_time:.3f}s",
                    f"Properties Found: {len(result.properties)}",
                    f"Methods Found: {len(result.methods)}",
                    ""
                ]
                
                # Add properties section
                if result.properties:
                    report_lines.append("=== Properties ===")
                    for prop in result.properties[:20]:  # Limit to first 20
                        access_info = ""
                        if not prop.is_writable:
                            access_info = " (read-only)"
                        elif not prop.is_readable:
                            access_info = " (write-only)"
                        
                        value_str = str(prop.value)[:100] if prop.value is not None else "None"
                        report_lines.append(f"  {prop.name}: {prop.type_name}{access_info} = {value_str}")
                        
                        if prop.description and depth in ["detailed", "comprehensive"]:
                            report_lines.append(f"    Description: {prop.description[:200]}")
                    
                    if len(result.properties) > 20:
                        report_lines.append(f"  ... and {len(result.properties) - 20} more properties")
                    report_lines.append("")
                
                # Add methods section
                if result.methods:
                    report_lines.append("=== Methods ===")
                    for method in result.methods[:15]:  # Limit to first 15
                        report_lines.append(f"  {method.signature}")
                        if method.description and depth in ["detailed", "comprehensive"]:
                            desc = method.description.split('\n')[0][:150]  # First line, truncated
                            report_lines.append(f"    {desc}")
                    
                    if len(result.methods) > 15:
                        report_lines.append(f"  ... and {len(result.methods) - 15} more methods")
                    report_lines.append("")
                
                # Add hierarchy if available
                if result.hierarchy and depth in ["comprehensive", "hierarchical"]:
                    report_lines.append("=== Object Hierarchy ===")
                    report_lines.append(f"  Type: {result.hierarchy.get('type', 'Unknown')}")
                    report_lines.append(f"  Module: {result.hierarchy.get('module', 'Unknown')}")
                    if result.hierarchy.get('mro'):
                        report_lines.append(f"  MRO: {' -> '.join(result.hierarchy['mro'])}")
                    if result.hierarchy.get('com_type'):
                        report_lines.append(f"  COM Type: {result.hierarchy['com_type']}")
                        report_lines.append(f"  COM Class: {result.hierarchy.get('com_class', 'Unknown')}")
                    report_lines.append("")
                
                # Add metadata
                if result.metadata:
                    report_lines.append("=== Metadata ===")
                    for key, value in result.metadata.items():
                        if key != "error":
                            report_lines.append(f"  {key}: {value}")
                
                return "\n".join(report_lines)
                
            except ValueError as e:
                raise McpError("INVALID_PARAMS", str(e))
            except Exception as e:
                logger.error(f"Error inspecting object {object_name}: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to inspect object: {str(e)}")

        @self.mcp.tool()
        def discover_object_methods(object_name: str, search_pattern: str = "") -> str:
            """
            Discover methods for AutoCAD object with optional filtering.
            
            Args:
                object_name: Name of object to analyze ('app', 'doc', 'model', 'acad')
                search_pattern: Optional pattern to filter methods (regex supported)
            
            Returns:
                Detailed method discovery report
            """
            try:
                # Get the object
                result = self.object_inspector.inspect_by_name(object_name, InspectionDepth.BASIC)
                obj = self.object_inspector._get_object_by_name(object_name)
                
                if obj is None:
                    raise ValueError(f"Object '{object_name}' not found")
                
                # Discover all methods
                if search_pattern:
                    methods = self.method_discoverer.find_methods_by_pattern(obj, search_pattern, "name")
                else:
                    methods = self.method_discoverer.discover_all_methods(obj, include_inherited=False)
                
                # Format report
                report_lines = [
                    f"=== Method Discovery: {object_name} ===",
                    f"Search Pattern: '{search_pattern}' (empty = all methods)" if search_pattern else "Showing all methods",
                    f"Methods Found: {len(methods)}",
                    ""
                ]
                
                for method in methods[:25]:  # Limit to first 25
                    report_lines.append(f"Method: {method.name}")
                    report_lines.append(f"  Signature: {method.signature}")
                    report_lines.append(f"  Type: {method.method_type.value}")
                    
                    if method.parameters:
                        param_names = [p.name for p in method.parameters if p.name not in ['self', 'cls']]
                        if param_names:
                            report_lines.append(f"  Parameters: {', '.join(param_names)}")
                    
                    if method.documentation and method.documentation.description:
                        desc = method.documentation.description[:200]
                        report_lines.append(f"  Description: {desc}")
                    
                    if method.is_inherited:
                        report_lines.append(f"  Inherited from: {method.source_class}")
                    
                    report_lines.append("")
                
                if len(methods) > 25:
                    report_lines.append(f"... and {len(methods) - 25} more methods")
                
                return "\n".join(report_lines)
                
            except ValueError as e:
                raise McpError("INVALID_PARAMS", str(e))
            except Exception as e:
                logger.error(f"Error discovering methods for {object_name}: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to discover methods: {str(e)}")

        @self.mcp.tool()
        def analyze_object_property(object_name: str, property_name: str) -> str:
            """
            Analyze specific property of AutoCAD object.
            
            Args:
                object_name: Name of object containing the property
                property_name: Name of property to analyze
            
            Returns:
                Detailed property analysis report
            """
            try:
                # Get the object
                obj = self.object_inspector._get_object_by_name(object_name)
                if obj is None:
                    raise ValueError(f"Object '{object_name}' not found")
                
                # Analyze the property
                prop_info = self.property_analyzer.analyze_property(obj, property_name)
                
                # Format report
                report_lines = [
                    f"=== Property Analysis: {object_name}.{property_name} ===",
                    f"Property Name: {prop_info.name}",
                    f"Data Type: {prop_info.data_type}",
                    f"Property Type: {prop_info.property_type.value}",
                    f"Access Level: {prop_info.access_level.value}",
                    f"Current Value: {prop_info.current_value}",
                    ""
                ]
                
                # Add constraints if any
                if prop_info.constraints:
                    report_lines.append("=== Constraints ===")
                    for constraint in prop_info.constraints:
                        report_lines.append(f"  Type: {constraint.constraint_type}")
                        if constraint.min_value is not None:
                            report_lines.append(f"    Min Value: {constraint.min_value}")
                        if constraint.max_value is not None:
                            report_lines.append(f"    Max Value: {constraint.max_value}")
                        if constraint.allowed_values:
                            report_lines.append(f"    Allowed Values: {constraint.allowed_values}")
                        if constraint.description:
                            report_lines.append(f"    Description: {constraint.description}")
                        report_lines.append("")
                
                # Add documentation if available
                if prop_info.documentation:
                    doc = prop_info.documentation
                    report_lines.append("=== Documentation ===")
                    report_lines.append(f"  Description: {doc.description}")
                    
                    if doc.usage_examples:
                        report_lines.append("  Usage Examples:")
                        for example in doc.usage_examples[:3]:
                            report_lines.append(f"    {example}")
                    
                    if doc.related_properties:
                        report_lines.append(f"  Related Properties: {', '.join(doc.related_properties)}")
                    
                    if doc.warnings:
                        report_lines.append("  Warnings:")
                        for warning in doc.warnings:
                            report_lines.append(f"    ⚠️ {warning}")
                    
                    report_lines.append("")
                
                # Add inheritance info
                if prop_info.is_inherited:
                    report_lines.append(f"Inherited from: {prop_info.source_class}")
                
                # Add metadata
                if prop_info.metadata:
                    report_lines.append("=== Metadata ===")
                    for key, value in prop_info.metadata.items():
                        if key != "error":
                            report_lines.append(f"  {key}: {value}")
                
                # Generate code examples
                report_lines.append("=== Code Examples ===")
                get_code = self.property_analyzer.generate_property_code(obj, property_name, "get")
                report_lines.append(f"Get Value: {get_code}")
                
                if prop_info.access_level in ["read_write", "write_only"]:
                    set_code = self.property_analyzer.generate_property_code(obj, property_name, "set")
                    report_lines.append(f"Set Value: {set_code}")
                
                return "\n".join(report_lines)
                
            except ValueError as e:
                raise McpError("INVALID_PARAMS", str(e))
            except Exception as e:
                logger.error(f"Error analyzing property {property_name}: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to analyze property: {str(e)}")

        @self.mcp.tool()
        def search_autocad_api(search_term: str, object_scope: str = "all") -> str:
            """
            Search AutoCAD API for properties and methods.
            
            Args:
                search_term: Term to search for in properties/methods
                object_scope: Scope to search ('app', 'doc', 'model', 'all')
            
            Returns:
                Search results with matching properties and methods
            """
            try:
                if object_scope == "all":
                    # Search across all main objects
                    all_results = []
                    for obj_name in ["app", "doc", "model", "acad"]:
                        try:
                            results = self.object_inspector.search_objects(search_term, "all")
                            all_results.extend(results)
                        except:
                            continue
                    results = all_results
                else:
                    # Search specific object
                    results = self.object_inspector.search_objects(search_term, "all")
                
                # Format results
                report_lines = [
                    f"=== AutoCAD API Search Results ===",
                    f"Search Term: '{search_term}'",
                    f"Scope: {object_scope}",
                    f"Results Found: {len(results)}",
                    ""
                ]
                
                # Group results by type
                properties = [r for r in results if r.get("type") == "property"]
                methods = [r for r in results if r.get("type") == "method"]
                
                if properties:
                    report_lines.append("=== Properties ===")
                    for prop in properties[:15]:
                        score = prop.get("match_score", 0)
                        report_lines.append(f"  {prop['object']}.{prop['name']} ({prop['value_type']}) - Score: {score:.2f}")
                    
                    if len(properties) > 15:
                        report_lines.append(f"  ... and {len(properties) - 15} more properties")
                    report_lines.append("")
                
                if methods:
                    report_lines.append("=== Methods ===")
                    for method in methods[:15]:
                        score = method.get("match_score", 0)
                        signature = method.get("signature", method['name'] + "(...)")
                        report_lines.append(f"  {method['object']}.{signature} - Score: {score:.2f}")
                    
                    if len(methods) > 15:
                        report_lines.append(f"  ... and {len(methods) - 15} more methods")
                    report_lines.append("")
                
                if not results:
                    report_lines.append("No matches found. Try a different search term or check object availability.")
                
                return "\n".join(report_lines)
                
            except Exception as e:
                logger.error(f"Error searching AutoCAD API: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to search API: {str(e)}")

        @self.mcp.tool()
        def get_intellisense_completions(context: str, position: int = 0) -> str:
            """
            Get IntelliSense completions for AutoCAD development.
            
            Args:
                context: Code context for completion (e.g., "acad.app.")
                position: Cursor position in context
            
            Returns:
                Available completions with descriptions
            """
            try:
                # Simulate document and position for IntelliSense provider
                document_text = context
                position_info = {"line": 0, "character": position or len(context)}
                
                # Get completions
                completions = self.intellisense_provider.get_completions(document_text, position_info)
                
                # Format results
                report_lines = [
                    f"=== IntelliSense Completions ===",
                    f"Context: '{context}'",
                    f"Position: {position}",
                    f"Completions Found: {len(completions)}",
                    ""
                ]
                
                for completion in completions[:20]:  # Limit to first 20
                    kind_name = completion.kind.name if hasattr(completion.kind, 'name') else str(completion.kind)
                    report_lines.append(f"  {completion.label} ({kind_name})")
                    
                    if completion.detail:
                        report_lines.append(f"    Type: {completion.detail}")
                    
                    if completion.documentation:
                        doc = completion.documentation[:100]
                        report_lines.append(f"    Description: {doc}")
                    
                    if completion.insert_text and completion.insert_text != completion.label:
                        report_lines.append(f"    Insert: {completion.insert_text}")
                    
                    report_lines.append("")
                
                if len(completions) > 20:
                    report_lines.append(f"... and {len(completions) - 20} more completions")
                
                return "\n".join(report_lines)
                
            except Exception as e:
                logger.error(f"Error getting IntelliSense completions: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to get completions: {str(e)}")

        @self.mcp.tool()
        def clear_inspection_cache() -> str:
            """
            Clear object inspection cache to force fresh analysis.
            
            Returns:
                Cache clear confirmation
            """
            try:
                self.object_inspector.clear_cache()
                return "✅ Object inspection cache cleared successfully. Next inspections will use fresh analysis."
            except Exception as e:
                logger.error(f"Error clearing inspection cache: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to clear cache: {str(e)}")

        @self.mcp.tool()
        def list_active_repl_sessions() -> str:
            """
            List all active REPL sessions.
            
            Returns:
                Information about active REPL sessions
            """
            try:
                sessions_info = self.python_repl.get_active_sessions()
                
                if not sessions_info["active_sessions"]:
                    return "No active REPL sessions."
                
                info_lines = [
                    f"Active REPL Sessions: {sessions_info['total_sessions']}",
                    "=" * 40
                ]
                
                for session_id, info in sessions_info["active_sessions"].items():
                    age = info["age_seconds"]
                    last_used = time.strftime("%H:%M:%S", time.localtime(info["last_executed"]))
                    
                    info_lines.append(f"Session: {session_id}")
                    info_lines.append(f"  Commands: {info['command_count']}")
                    info_lines.append(f"  Age: {age:.1f}s")
                    info_lines.append(f"  Last Used: {last_used}")
                    info_lines.append(f"  Status: {info['status']}")
                    info_lines.append("")
                
                return "\n".join(info_lines)
                
            except Exception as e:
                logger.error(f"Error listing REPL sessions: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to list REPL sessions: {str(e)}")

    def _register_diagnostic_tools(self):
        """Register diagnostic and maintenance tools."""

        @self.mcp.tool()
        def create_diagnostic_report() -> str:
            """
            Create comprehensive diagnostic report for troubleshooting.

            Returns:
                Detailed diagnostic report
            """
            try:
                acad = self._get_autocad_wrapper()
                report = acad.create_diagnostic_report()

                # Format report
                lines = [
                    "=== AutoCAD Master Coder Diagnostic Report ===",
                    f"Generated: {time.ctime()}",
                    "",
                    "=== Connection Status ===",
                    f"Connected: {report['connection_status']['connected']}",
                    f"Version: {report['connection_status'].get('autocad_version', 'Unknown')}",
                    f"Documents: {report['connection_status'].get('documents_count', 0)}",
                    "",
                    "=== Performance Summary ===",
                    f"Total Operations: {report['performance_metrics']['total_operations']}",
                    f"Success Rate: {report['performance_metrics']['overall_success_rate']:.1%}",
                    f"Average Duration: {report['performance_metrics']['average_operation_duration']:.3f}s",
                    "",
                    "=== Error Summary ===",
                    f"Total Errors: {report['error_statistics']['total_errors']}",
                    f"Recent Errors: {report['error_statistics'].get('errors_last_hour', 0)}",
                ]

                if report["error_statistics"].get("most_common_category"):
                    lines.append(
                        f"Most Common Error: {report['error_statistics']['most_common_category']}"
                    )

                return "\n".join(lines)

            except Exception as e:
                logger.error(f"Error creating diagnostic report: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to create diagnostic report: {str(e)}")

        @self.mcp.tool()
        def recover_autocad_connection() -> str:
            """
            Manually recover AutoCAD connection.

            Returns:
                Recovery result message
            """
            try:
                acad = self._get_autocad_wrapper()
                success = acad.recover_connection()

                if success:
                    return "✅ AutoCAD connection recovered successfully"
                else:
                    return "❌ AutoCAD connection recovery failed"

            except Exception as e:
                logger.error(f"Error recovering connection: {e}")
                raise McpError("INTERNAL_ERROR", f"Connection recovery failed: {str(e)}")

    def _register_debugging_tools(self):
        """Register debugging MCP tools for Week 5 features."""

        @self.mcp.tool()
        def start_debug_session(session_id: Optional[str] = None) -> str:
            """
            Start a new AutoCAD debugging session with object inspection.
            
            Args:
                session_id: Optional session identifier
                
            Returns:
                Debug session information
            """
            try:
                debugger = self._get_debugger()
                session_id = debugger.start_debug_session(session_id)
                return f"✅ Debug session started: {session_id}"
            except Exception as e:
                logger.error(f"Error starting debug session: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to start debug session: {str(e)}")

        @self.mcp.tool()
        def stop_debug_session() -> str:
            """
            Stop the current debugging session and get summary.
            
            Returns:
                Debug session summary
            """
            try:
                summary = self._get_debugger().stop_debug_session()
                if "message" in summary:
                    return summary["message"]
                
                return f"✅ Debug session stopped. Total operations: {summary.get('total_trace_entries', 0)}, Breakpoints hit: {summary.get('breakpoints_hit', 0)}"
            except Exception as e:
                logger.error(f"Error stopping debug session: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to stop debug session: {str(e)}")

        @self.mcp.tool()
        def add_breakpoint(breakpoint_type: str, 
                          filename: Optional[str] = None,
                          line_number: Optional[int] = None,
                          function_name: Optional[str] = None,
                          variable_name: Optional[str] = None,
                          condition: Optional[str] = None) -> str:
            """
            Add a debugging breakpoint.
            
            Args:
                breakpoint_type: Type of breakpoint ('line', 'function', 'variable', 'object_access')
                filename: Source filename for line breakpoints
                line_number: Line number for line breakpoints
                function_name: Function name for function breakpoints
                variable_name: Variable name for variable breakpoints
                condition: Optional condition for conditional breakpoints
                
            Returns:
                Breakpoint ID and confirmation
            """
            try:
                breakpoint_id = self._get_debugger().add_breakpoint(
                    breakpoint_type=breakpoint_type,
                    filename=filename,
                    line_number=line_number,
                    function_name=function_name,
                    variable_name=variable_name,
                    condition=condition
                )
                return f"✅ Breakpoint added: {breakpoint_id} ({breakpoint_type})"
            except Exception as e:
                logger.error(f"Error adding breakpoint: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to add breakpoint: {str(e)}")

        @self.mcp.tool()
        def inspect_debug_context(depth: str = "detailed") -> str:
            """
            Inspect current debugging context with detailed object analysis.
            
            Args:
                depth: Inspection depth ('basic', 'detailed', 'comprehensive')
                
            Returns:
                Comprehensive debugging context report
            """
            try:
                context = self._get_debugger().inspect_current_context(depth)
                
                if "error" in context:
                    return f"❌ {context['error']}"
                
                # Format context report
                report_lines = [
                    "=== Debug Context Inspection ===",
                    f"Current Frame: {context['frame_info']['function_name']} at line {context['frame_info']['line_number']}",
                    f"File: {context['frame_info']['filename']}",
                    "",
                    f"Call Stack Depth: {len(context['call_stack'])}",
                    f"Local Variables: {len(context['local_variables'])}",
                    f"AutoCAD Objects: {len(context['autocad_objects'])}",
                    f"Variable Watches: {len(context['variable_watches'])}",
                    ""
                ]
                
                # Add local variables summary
                if context['local_variables']:
                    report_lines.append("=== Key Local Variables ===")
                    for var_name, var_info in list(context['local_variables'].items())[:10]:
                        report_lines.append(f"  {var_name}: {var_info['type']} = {var_info['value'][:50]}")
                    report_lines.append("")
                
                # Add AutoCAD objects summary  
                if context['autocad_objects']:
                    report_lines.append("=== AutoCAD Objects ===")
                    for obj_name, obj_info in list(context['autocad_objects'].items())[:5]:
                        if isinstance(obj_info, dict) and 'object_info' in obj_info:
                            report_lines.append(f"  {obj_name}: {obj_info['object_info'].get('type', 'Unknown')}")
                        else:
                            report_lines.append(f"  {obj_name}: AutoCAD Object")
                    report_lines.append("")
                
                return "\n".join(report_lines)
                
            except Exception as e:
                logger.error(f"Error inspecting debug context: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to inspect context: {str(e)}")

        @self.mcp.tool()
        def evaluate_debug_expression(expression: str) -> str:
            """
            Evaluate Python expression in current debug context.
            
            Args:
                expression: Python expression to evaluate
                
            Returns:
                Expression evaluation result
            """
            try:
                result = self._get_debugger().evaluate_expression(expression)
                
                if result["success"]:
                    output = f"✅ Expression: {expression}\n"
                    output += f"Result: {result['value']} ({result['type']})\n"
                    
                    if "autocad_inspection" in result:
                        output += "AutoCAD Object Analysis Available ✓"
                    
                    return output
                else:
                    return f"❌ Expression failed: {result['error']} ({result.get('error_type', 'Unknown')})"
                    
            except Exception as e:
                logger.error(f"Error evaluating expression: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to evaluate expression: {str(e)}")

    def _register_diagnostics_tools(self):
        """Register error diagnostics MCP tools for Week 5 features."""

        @self.mcp.tool()
        def analyze_error(error_message: str, 
                         code: Optional[str] = None,
                         context: Optional[str] = None) -> str:
            """
            Perform comprehensive error analysis with diagnostic recommendations.
            
            Args:
                error_message: Error message or exception details
                code: Source code that caused the error (optional)
                context: Additional context information (optional)
                
            Returns:
                Detailed diagnostic analysis and recommendations
            """
            try:
                # Create a mock exception for analysis
                class MockException(Exception):
                    pass
                
                mock_error = MockException(error_message)
                
                # Parse context if provided
                context_dict = {}
                if context:
                    try:
                        import json
                        context_dict = json.loads(context)
                    except:
                        context_dict = {"raw_context": context}
                
                # Analyze the error
                diagnostic = self._get_error_diagnostics().analyze_error(
                    error=mock_error,
                    context=context_dict,
                    code=code
                )
                
                # Format diagnostic report
                report_lines = [
                    f"=== Error Diagnostic Analysis ===",
                    f"Severity: {diagnostic.severity.value.upper()}",
                    f"Category: {diagnostic.category.value}",
                    f"Title: {diagnostic.title}",
                    f"Confidence: {diagnostic.confidence_score:.1%}",
                    "",
                    f"Description: {diagnostic.description}",
                    ""
                ]
                
                if diagnostic.resolution_steps:
                    report_lines.append("=== Resolution Steps ===")
                    for i, step in enumerate(diagnostic.resolution_steps, 1):
                        report_lines.append(f"{i}. {step}")
                    report_lines.append("")
                
                if diagnostic.code_suggestions:
                    report_lines.append("=== Code Examples ===")
                    for suggestion in diagnostic.code_suggestions[:2]:
                        report_lines.append(suggestion)
                        report_lines.append("")
                
                return "\n".join(report_lines)
                
            except Exception as e:
                logger.error(f"Error analyzing error: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to analyze error: {str(e)}")

        @self.mcp.tool()
        def analyze_code_issues(code: str) -> str:
            """
            Analyze code for potential issues without execution.
            
            Args:
                code: Python code to analyze for issues
                
            Returns:
                List of potential issues and recommendations
            """
            try:
                issues = self._get_error_diagnostics().analyze_code_issues(code)
                
                if not issues:
                    return "✅ No issues detected in code analysis"
                
                report_lines = [
                    f"=== Code Analysis Report ===",
                    f"Issues Found: {len(issues)}",
                    ""
                ]
                
                for i, issue in enumerate(issues, 1):
                    report_lines.append(f"Issue #{i}: {issue.title}")
                    report_lines.append(f"  Severity: {issue.severity.value}")
                    report_lines.append(f"  Category: {issue.category.value}")
                    report_lines.append(f"  Description: {issue.description}")
                    
                    if issue.resolution_steps:
                        report_lines.append("  Recommendations:")
                        for step in issue.resolution_steps[:2]:
                            report_lines.append(f"    • {step}")
                    report_lines.append("")
                
                return "\n".join(report_lines)
                
            except Exception as e:
                logger.error(f"Error analyzing code: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to analyze code: {str(e)}")

        @self.mcp.tool()
        def search_error_solutions(query: str, limit: int = 5) -> str:
            """
            Search for solutions based on error description or pattern.
            
            Args:
                query: Search query for error or issue
                limit: Maximum number of results to return
                
            Returns:
                Relevant solutions and documentation
            """
            try:
                solutions = self._get_error_diagnostics().search_solutions(query, limit)
                
                if not solutions:
                    return f"No solutions found for query: '{query}'"
                
                report_lines = [
                    f"=== Solutions for: '{query}' ===",
                    f"Found {len(solutions)} relevant solutions:",
                    ""
                ]
                
                for i, solution in enumerate(solutions, 1):
                    report_lines.append(f"{i}. {solution['title']} (Relevance: {solution['relevance_score']:.1%})")
                    report_lines.append(f"   Category: {solution['category']}")
                    report_lines.append(f"   {solution['description']}")
                    
                    if solution['resolution_steps']:
                        report_lines.append("   Steps:")
                        for step in solution['resolution_steps'][:3]:
                            report_lines.append(f"     • {step}")
                    
                    if solution['code_examples']:
                        report_lines.append("   Example:")
                        report_lines.append(f"     {solution['code_examples'][0][:100]}...")
                    
                    report_lines.append("")
                
                return "\n".join(report_lines)
                
            except Exception as e:
                logger.error(f"Error searching solutions: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to search solutions: {str(e)}")

    def _register_performance_tools(self):
        """Register performance analysis MCP tools for Week 5 features."""

        @self.mcp.tool()
        def start_performance_analysis(session_id: Optional[str] = None) -> str:
            """
            Start performance analysis session with real-time monitoring.
            
            Args:
                session_id: Optional session identifier
                
            Returns:
                Performance analysis session information
            """
            try:
                session_id = self._get_performance_analyzer().start_analysis_session(session_id)
                return f"✅ Performance analysis started: {session_id}"
            except Exception as e:
                logger.error(f"Error starting performance analysis: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to start performance analysis: {str(e)}")

        @self.mcp.tool()
        def stop_performance_analysis() -> str:
            """
            Stop performance analysis session and get summary.
            
            Returns:
                Performance analysis summary
            """
            try:
                summary = self._get_performance_analyzer().stop_analysis_session()
                
                if "message" in summary:
                    return summary["message"]
                
                return f"✅ Performance analysis stopped. Operations: {summary.get('total_operations', 0)}, Score: {summary.get('performance_score', 0):.1f}/100"
            except Exception as e:
                logger.error(f"Error stopping performance analysis: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to stop performance analysis: {str(e)}")

        @self.mcp.tool()
        def analyze_performance_bottlenecks(top_n: int = 5) -> str:
            """
            Analyze performance bottlenecks and identify optimization opportunities.
            
            Args:
                top_n: Number of top bottlenecks to analyze
                
            Returns:
                Bottleneck analysis with optimization recommendations
            """
            try:
                bottlenecks = self._get_performance_analyzer().analyze_bottlenecks(top_n)
                
                if not bottlenecks:
                    return "✅ No performance bottlenecks detected"
                
                report_lines = [
                    f"=== Performance Bottleneck Analysis ===",
                    f"Top {len(bottlenecks)} Performance Issues:",
                    ""
                ]
                
                for i, bottleneck in enumerate(bottlenecks, 1):
                    report_lines.append(f"{i}. {bottleneck.operation_name}")
                    report_lines.append(f"   Impact: {bottleneck.percentage_of_total:.1f}% of total time")
                    report_lines.append(f"   Calls: {bottleneck.call_count}")
                    report_lines.append(f"   Avg Time: {bottleneck.average_time:.3f}s")
                    report_lines.append(f"   Max Time: {bottleneck.max_time:.3f}s")
                    
                    if bottleneck.suggestions:
                        report_lines.append("   Optimization Suggestions:")
                        for suggestion in bottleneck.suggestions[:2]:
                            report_lines.append(f"     • {suggestion}")
                    
                    report_lines.append("")
                
                return "\n".join(report_lines)
                
            except Exception as e:
                logger.error(f"Error analyzing bottlenecks: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to analyze bottlenecks: {str(e)}")

        @self.mcp.tool()
        def get_real_time_performance() -> str:
            """
            Get current real-time performance metrics.
            
            Returns:
                Current performance metrics and system status
            """
            try:
                metrics = self._get_performance_analyzer().get_real_time_metrics()
                
                if "message" in metrics:
                    return metrics["message"]
                
                report_lines = [
                    f"=== Real-Time Performance Metrics ===",
                    f"Session: {metrics.get('session_id', 'N/A')}",
                    f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}",
                    ""
                ]
                
                # System metrics
                system_metrics = metrics.get('system_metrics', {})
                if system_metrics:
                    report_lines.append("=== System Metrics ===")
                    report_lines.append(f"CPU Usage: {system_metrics.get('cpu_percent', 0):.1f}%")
                    report_lines.append(f"Memory Usage: {system_metrics.get('memory_percent', 0):.1f}%")
                    report_lines.append(f"Active Threads: {system_metrics.get('active_threads', 0)}")
                    report_lines.append("")
                
                # Operation metrics
                operation_metrics = metrics.get('operation_metrics', {})
                if operation_metrics:
                    report_lines.append("=== Operation Metrics ===")
                    for op_name, op_data in list(operation_metrics.items())[:5]:
                        report_lines.append(f"{op_name}:")
                        report_lines.append(f"  Calls: {op_data.get('call_count', 0)}")
                        report_lines.append(f"  Avg Time: {op_data.get('average_time', 0):.3f}s")
                        report_lines.append(f"  Recent: {op_data.get('recent_calls', 0)} calls/min")
                    report_lines.append("")
                
                # Memory analysis
                memory_metrics = metrics.get('memory_usage', {})
                if memory_metrics:
                    report_lines.append("=== Memory Analysis ===")
                    process_mb = memory_metrics.get('process_memory', 0) / (1024*1024)
                    report_lines.append(f"Process Memory: {process_mb:.1f} MB")
                    report_lines.append(f"Memory %: {memory_metrics.get('process_percent', 0):.1f}%")
                    report_lines.append("")
                
                # Alerts
                active_alerts = metrics.get('active_alerts', 0)
                if active_alerts:
                    report_lines.append(f"⚠️ Active Performance Alerts: {active_alerts}")
                else:
                    report_lines.append("✅ No active performance alerts")
                
                return "\n".join(report_lines)
                
            except Exception as e:
                logger.error(f"Error getting real-time performance: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to get performance metrics: {str(e)}")

        @self.mcp.tool()
        def get_optimization_report() -> str:
            """
            Generate comprehensive optimization report with actionable recommendations.
            
            Returns:
                Detailed optimization report with recommendations
            """
            try:
                report = self._get_performance_analyzer().get_optimization_report()
                
                report_lines = [
                    f"=== Performance Optimization Report ===",
                    f"Session: {report.get('session_id', 'N/A')}",
                    f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
                    "",
                    f"Executive Summary: {report.get('executive_summary', 'No summary available')}",
                    ""
                ]
                
                # System health
                health = report.get('system_health', 'unknown')
                health_emoji = {
                    'healthy': '✅',
                    'warning': '⚠️',
                    'degraded': '🔶',
                    'critical': '🔴'
                }.get(health, '❓')
                report_lines.append(f"System Health: {health_emoji} {health.upper()}")
                
                # AutoCAD performance
                autocad_perf = report.get('autocad_performance', 'unknown')
                perf_emoji = {
                    'fast': '🚀',
                    'moderate': '⚡',
                    'slow': '🐌',
                    'no_data': '❓'
                }.get(autocad_perf, '❓')
                report_lines.append(f"AutoCAD Performance: {perf_emoji} {autocad_perf.upper()}")
                report_lines.append("")
                
                # Top bottlenecks
                top_bottlenecks = report.get('top_bottlenecks', [])
                if top_bottlenecks:
                    report_lines.append("=== Top Performance Issues ===")
                    for bottleneck in top_bottlenecks[:3]:
                        report_lines.append(f"• {bottleneck['operation']} - {bottleneck['impact']} impact")
                        report_lines.append(f"  Avg: {bottleneck['average_time']}, Calls: {bottleneck['call_count']}")
                        if bottleneck['suggestions']:
                            report_lines.append(f"  Fix: {bottleneck['suggestions'][0]}")
                        report_lines.append("")
                
                # Active alerts
                active_alerts = report.get('active_alerts', [])
                if active_alerts:
                    report_lines.append("=== Active Alerts ===")
                    for alert in active_alerts[:3]:
                        severity_emoji = {
                            'critical': '🔴',
                            'warning': '⚠️',
                            'info': 'ℹ️'
                        }.get(alert['severity'], '❓')
                        report_lines.append(f"{severity_emoji} {alert['title']}")
                        report_lines.append(f"  {alert['description']}")
                        if alert['recommendations']:
                            report_lines.append(f"  Action: {alert['recommendations'][0]}")
                        report_lines.append("")
                
                # Top recommendations
                recommendations = report.get('recommendations', [])
                if recommendations:
                    report_lines.append("=== Top Recommendations ===")
                    for i, rec in enumerate(recommendations[:5], 1):
                        report_lines.append(f"{i}. {rec}")
                    report_lines.append("")
                
                return "\n".join(report_lines)
                
            except Exception as e:
                logger.error(f"Error generating optimization report: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to generate optimization report: {str(e)}")

    def _register_code_generation_tools(self):
        """Register Phase 3 code generation MCP tools."""

        @self.mcp.tool()
        def generate_autolisp_script(task_description: str, complexity: str = "basic") -> str:
            """
            Generate AutoLISP code from natural language description.
            
            Args:
                task_description: Natural language description of the task
                complexity: Code complexity level ('basic', 'intermediate', 'advanced')
            
            Returns:
                Generated AutoLISP code with usage instructions
            """
            try:
                generator = self._get_autolisp_generator()
                result = generator.generate_code(task_description, complexity)
                
                if "error" in result:
                    raise McpError("INVALID_PARAMS", result["error"])
                
                # Format response with code and instructions
                response = {
                    "code": result["code"],
                    "language": result["language"],
                    "command_name": result.get("command_name", ""),
                    "description": result["description"],
                    "usage_example": result.get("usage_example", ""),
                    "notes": result.get("notes", [])
                }
                
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"Error generating AutoLISP script: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to generate AutoLISP script: {str(e)}")

        @self.mcp.tool()
        def generate_python_autocad_script(task_description: str, complexity: str = "basic", template_type: str = None) -> str:
            """
            Generate Python AutoCAD script with best practices.
            
            Args:
                task_description: Natural language description of the task
                complexity: Code complexity level ('basic', 'intermediate', 'advanced')
                template_type: Specific template type ('basic_drawing', 'data_processing', 'batch_processing', 'advanced_automation')
            
            Returns:
                Generated Python code with usage instructions
            """
            try:
                generator = self._get_python_generator()
                result = generator.generate_code(task_description, complexity, template_type)
                
                if "error" in result:
                    raise McpError("INVALID_PARAMS", result["error"])
                
                # Format response with code and metadata
                response = {
                    "code": result["code"],
                    "language": result["language"],
                    "template_type": result.get("template_type", "custom"),
                    "description": result["description"],
                    "usage_example": result.get("usage_example", ""),
                    "complexity": result.get("complexity", complexity),
                    "requirements": result.get("requirements", []),
                    "notes": result.get("notes", [])
                }
                
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"Error generating Python script: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to generate Python script: {str(e)}")

        @self.mcp.tool()
        def generate_vba_macro(task_description: str, complexity: str = "basic", target_host: str = "autocad") -> str:
            """
            Generate VBA macro code for AutoCAD or Excel integration.
            
            Args:
                task_description: Natural language description of the task
                complexity: Code complexity level ('basic', 'intermediate', 'advanced')
                target_host: Target application ('autocad', 'excel')
            
            Returns:
                Generated VBA code with usage instructions
            """
            try:
                generator = self._get_vba_generator()
                result = generator.generate_code(task_description, complexity, target_host)
                
                if "error" in result:
                    raise McpError("INVALID_PARAMS", result["error"])
                
                # Format response with code and metadata
                response = {
                    "code": result["code"],
                    "language": result["language"],
                    "macro_name": result.get("macro_name", ""),
                    "module_type": result.get("module_type", "standard"),
                    "description": result["description"],
                    "target_host": result.get("target_host", target_host),
                    "dependencies": result.get("dependencies", []),
                    "usage_instructions": result.get("usage_instructions", [])
                }
                
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"Error generating VBA macro: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to generate VBA macro: {str(e)}")

        @self.mcp.tool()
        def suggest_optimal_language(task_description: str) -> str:
            """
            Recommend the best programming language for a specific AutoCAD automation task.
            
            Args:
                task_description: Natural language description of the task
            
            Returns:
                Language recommendation with reasoning and analysis
            """
            try:
                coordinator = self._get_language_coordinator()
                result = coordinator.suggest_optimal_approach(task_description)
                
                # Format comprehensive response
                response = {
                    "task_analysis": result["task_analysis"],
                    "language_recommendations": result["language_recommendations"],
                    "hybrid_solution": result["hybrid_solution"],
                    "final_recommendation": result["final_recommendation"],
                    "reasoning": "Analysis based on task complexity, integration needs, and performance requirements"
                }
                
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"Error suggesting optimal language: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to suggest optimal language: {str(e)}")

        @self.mcp.tool()
        def create_hybrid_solution(requirements: Dict[str, Any]) -> str:
            """
            Create a hybrid solution using multiple programming languages optimally.
            
            Args:
                requirements: Dictionary with task requirements including description, operations, integration_needs
            
            Returns:
                Hybrid solution plan with implementation strategy
            """
            try:
                coordinator = self._get_language_coordinator()
                
                # Parse requirements if passed as string
                if isinstance(requirements, str):
                    # Try to parse as JSON or treat as description
                    try:
                        import json
                        requirements = json.loads(requirements)
                    except:
                        requirements = {"description": requirements}
                
                # Use the requirements to get hybrid solution
                task_req = coordinator.parse_requirements(requirements.get("description", ""))
                
                # Update task requirements with provided details
                if "operations" in requirements:
                    task_req.operations.extend(requirements["operations"])
                if "integration_needs" in requirements:
                    task_req.integration_needs.extend(requirements["integration_needs"])
                if "performance_critical" in requirements:
                    task_req.performance_critical = requirements["performance_critical"]
                
                hybrid_result = coordinator.create_hybrid_solution(task_req)
                
                # Format response
                response = {
                    "hybrid_recommended": hybrid_result["hybrid_recommended"],
                    "primary_language": hybrid_result.get("primary_language", ""),
                    "secondary_language": hybrid_result.get("secondary_language", ""),
                    "workflow_description": hybrid_result.get("workflow_description", ""),
                    "implementation_approach": hybrid_result.get("implementation_approach", ""),
                    "reason": hybrid_result.get("reason", ""),
                    "task_analysis": {
                        "complexity": task_req.complexity,
                        "operations": task_req.operations,
                        "integration_needs": task_req.integration_needs,
                        "performance_critical": task_req.performance_critical
                    }
                }
                
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"Error creating hybrid solution: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to create hybrid solution: {str(e)}")

        @self.mcp.tool()
        def validate_generated_code(code: str, language: str) -> str:
            """
            Validate generated code for syntax, best practices, and AutoCAD compatibility.
            
            Args:
                code: Code to validate
                language: Programming language ('python', 'autolisp', 'vba')
            
            Returns:
                Validation results with issues, suggestions, and quality score
            """
            try:
                validator = self._get_validation_engine()
                result = validator.validate_code(code, language)
                
                # Format validation response
                response = {
                    "valid": result.valid,
                    "language": result.language,
                    "quality_score": result.quality_score,
                    "summary": result.summary,
                    "issues": [
                        {
                            "severity": issue.severity,
                            "category": issue.category,
                            "message": issue.message,
                            "line_number": issue.line_number,
                            "suggestion": issue.suggestion
                        }
                        for issue in result.issues
                    ],
                    "suggestions": result.suggestions
                }
                
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"Error validating code: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to validate code: {str(e)}")

    def _register_testing_tools(self):
        """Register Phase 4 testing framework MCP tools."""

        @self.mcp.tool()
        def run_autocad_tests(test_suite: str = "all", mock_mode: bool = True) -> str:
            """
            Run comprehensive AutoCAD automation tests.
            
            Args:
                test_suite: Test suite to run ('all', 'unit', 'integration', 'performance')
                mock_mode: Use mock AutoCAD for testing (recommended for CI)
            
            Returns:
                Test execution results with detailed report
            """
            try:
                framework = self._get_test_framework()
                framework.mock_mode = mock_mode
                
                if test_suite == "all":
                    results = framework.run_all_suites()
                else:
                    if test_suite in framework.test_suites:
                        results = {test_suite: framework.run_suite(test_suite)}
                    else:
                        raise McpError("INVALID_PARAMS", f"Test suite '{test_suite}' not found")
                
                # Generate report
                report = framework.generate_report("text")
                
                response = {
                    "test_results": results,
                    "report": report,
                    "mock_mode": mock_mode,
                    "total_suites": len(results)
                }
                
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"Error running tests: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to run tests: {str(e)}")

        @self.mcp.tool()
        def generate_project_tests(project_path: str, output_dir: str = "tests/generated") -> str:
            """
            Generate comprehensive test suite for AutoCAD project.
            
            Args:
                project_path: Path to the project source code
                output_dir: Directory to save generated tests
            
            Returns:
                Information about generated test files and coverage
            """
            try:
                generator = self._get_test_generator()
                
                # Generate tests for the entire project
                result = generator.generate_project_tests(project_path)
                
                response = {
                    "message": result,
                    "output_directory": output_dir,
                    "project_path": project_path,
                    "test_types": ["unit", "integration", "performance", "error_handling"]
                }
                
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"Error generating tests: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to generate tests: {str(e)}")

        @self.mcp.tool()
        def benchmark_autocad_performance(operations: List[str] = None, iterations: int = 50, mock_mode: bool = True) -> str:
            """
            Benchmark AutoCAD operations for performance analysis.
            
            Args:
                operations: List of operations to benchmark (None for all)
                iterations: Number of iterations per operation
                mock_mode: Use mock AutoCAD for consistent benchmarking
            
            Returns:
                Performance benchmark results with metrics and analysis
            """
            try:
                tester = self._get_performance_tester()
                
                if operations is None:
                    # Benchmark common operations
                    results = tester.benchmark_autocad_operations(mock_mode=mock_mode)
                else:
                    # Benchmark specific operations
                    results = {}
                    # This would require implementation of specific operation benchmarks
                
                # Generate performance report
                report = tester.generate_performance_report()
                
                response = {
                    "benchmark_results": {
                        name: {
                            "average_time": bench.average_time,
                            "min_time": bench.min_time,
                            "max_time": bench.max_time,
                            "iterations": bench.iterations
                        }
                        for name, bench in results.items()
                    },
                    "performance_report": report,
                    "mock_mode": mock_mode
                }
                
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"Error benchmarking performance: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to benchmark performance: {str(e)}")

        @self.mcp.tool()
        def setup_ci_integration(project_path: str, ci_provider: str = "github") -> str:
            """
            Setup CI/CD integration for AutoCAD project.
            
            Args:
                project_path: Path to the project
                ci_provider: CI/CD provider ('github', 'azure', 'jenkins')
            
            Returns:
                Information about CI/CD setup and configuration files created
            """
            try:
                from ..testing.ci_integration import CIIntegration, CIConfiguration
                
                ci_integration = CIIntegration()
                ci_config = CIConfiguration(
                    provider=ci_provider,
                    project_path=project_path,
                    test_commands=[
                        "python -m pytest tests/ --cov=src --cov-report=xml",
                        "python -m pytest tests/generated/ --html=test-report.html"
                    ],
                    mock_mode=True
                )
                
                config_file = ci_integration.setup_ci_integration(project_path, ci_provider, ci_config)
                validation = ci_integration.validate_ci_setup(project_path, ci_provider)
                
                response = {
                    "ci_provider": ci_provider,
                    "config_file": config_file,
                    "validation": validation,
                    "setup_complete": validation["valid"]
                }
                
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"Error setting up CI integration: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to setup CI integration: {str(e)}")

    def _register_project_tools(self):
        """Register Phase 4 project template and management MCP tools."""

        @self.mcp.tool()
        def create_autocad_project(project_name: str, project_type: str = "basic_autocad", 
                                 output_directory: str = ".", author_name: str = "Developer") -> str:
            """
            Create new AutoCAD automation project from template.
            
            Args:
                project_name: Name of the new project
                project_type: Type of project ('basic_autocad', 'advanced_mcp', 'manufacturing_cad')
                output_directory: Directory to create the project in
                author_name: Author name for the project
            
            Returns:
                Information about the created project and next steps
            """
            try:
                from ..project_templates.project_scaffolder import ProjectScaffoldConfig
                
                scaffolder = self._get_project_scaffolder()
                
                config = ProjectScaffoldConfig(
                    project_name=project_name,
                    project_type=project_type,
                    output_directory=output_directory,
                    author_name=author_name,
                    initialize_git=True,
                    install_dependencies=False,  # Don't install in MCP context
                    create_venv=False,
                    setup_ci=False
                )
                
                project_path = scaffolder.create_project(config)
                validation = scaffolder.validate_project_structure(project_path)
                report = scaffolder.generate_project_report(project_path)
                
                response = {
                    "project_path": project_path,
                    "project_type": project_type,
                    "validation": validation,
                    "report": report,
                    "next_steps": [
                        "Navigate to the project directory",
                        "Install dependencies: poetry install",
                        "Review README.md for project-specific instructions",
                        "Start developing in the src/ directory"
                    ]
                }
                
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"Error creating project: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to create project: {str(e)}")

        @self.mcp.tool()
        def get_available_project_templates() -> str:
            """
            Get list of available AutoCAD project templates.
            
            Returns:
                List of available project templates with descriptions
            """
            try:
                scaffolder = self._get_project_scaffolder()
                templates = scaffolder.get_available_project_types()
                
                response = {
                    "available_templates": templates,
                    "total_templates": len(templates),
                    "description": "Available project templates for AutoCAD automation"
                }
                
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"Error getting templates: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to get available templates: {str(e)}")

        @self.mcp.tool()
        def manage_project_dependencies(project_path: str, action: str = "check", 
                                      dependency_name: str = None, version: str = None) -> str:
            """
            Manage dependencies for AutoCAD project.
            
            Args:
                project_path: Path to the project
                action: Action to perform ('check', 'add', 'remove', 'update', 'install')
                dependency_name: Name of dependency (for add/remove actions)
                version: Version specification (for add action)
            
            Returns:
                Dependency management results and recommendations
            """
            try:
                manager = self._get_dependency_manager()
                
                if action == "check":
                    compatibility = manager.check_dependency_compatibility(project_path)
                    report = manager.generate_dependency_report(project_path)
                    
                    response = {
                        "action": action,
                        "compatibility": compatibility,
                        "report": report
                    }
                
                elif action == "add" and dependency_name:
                    success = manager.add_dependency(project_path, dependency_name, version)
                    response = {
                        "action": action,
                        "dependency": dependency_name,
                        "version": version,
                        "success": success
                    }
                
                elif action == "remove" and dependency_name:
                    success = manager.remove_dependency(project_path, dependency_name)
                    response = {
                        "action": action,
                        "dependency": dependency_name,
                        "success": success
                    }
                
                elif action == "update":
                    results = manager.update_dependencies(project_path)
                    response = {
                        "action": action,
                        "update_results": results
                    }
                
                elif action == "install":
                    success = manager.install_dependencies(project_path)
                    response = {
                        "action": action,
                        "success": success
                    }
                
                else:
                    raise McpError("INVALID_PARAMS", f"Invalid action: {action}")
                
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"Error managing dependencies: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to manage dependencies: {str(e)}")

        @self.mcp.tool()
        def generate_project_documentation(project_path: str, output_dir: str = "docs/generated") -> str:
            """
            Generate comprehensive documentation for AutoCAD project.
            
            Args:
                project_path: Path to the project source code
                output_dir: Directory to save generated documentation
            
            Returns:
                Information about generated documentation files
            """
            try:
                generator = self._get_documentation_generator()
                
                # Generate complete project documentation
                docs_path = generator.generate_project_documentation(project_path, output_dir)
                
                # Generate additional documentation files
                changelog_path = generator.generate_changelog(project_path)
                contrib_path = generator.generate_contributing_guide(project_path)
                
                response = {
                    "documentation_path": docs_path,
                    "generated_files": [
                        f"{output_dir}/api.md",
                        f"{output_dir}/user_guide.md", 
                        f"{output_dir}/tutorial.md",
                        "CHANGELOG.md",
                        "CONTRIBUTING.md"
                    ],
                    "project_path": project_path,
                    "documentation_complete": True
                }
                
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"Error generating documentation: {e}")
                raise McpError("INTERNAL_ERROR", f"Failed to generate documentation: {str(e)}")

    # Phase 4: Testing Framework Tools
    
    @mcp.tool("generate_tests_for_file")
    async def generate_tests_for_file(
        self,
        file_path: str,
        test_types: Optional[str] = "unit,integration"
    ) -> str:
        """
        Generate automated tests for a Python file.
        
        Args:
            file_path: Path to the Python file to generate tests for
            test_types: Comma-separated list of test types (unit,integration,performance)
            
        Returns:
            JSON string with test generation results
        """
        try:
            test_generator = self._get_test_generator()
            
            # Parse test types
            types_list = test_types.split(',') if test_types else ['unit', 'integration']
            types_list = [t.strip() for t in types_list]
            
            # Generate tests
            tests = test_generator.generate_tests_for_file(file_path, types_list)
            
            # Save generated tests
            output_file = file_path.replace('.py', '_test.py')
            if tests:
                test_generator.save_generated_tests(tests, output_file)
            
            response = {
                "file_path": file_path,
                "output_file": output_file,
                "tests_generated": len(tests),
                "test_types": types_list,
                "tests": [
                    {
                        "name": test.name,
                        "type": test.test_type,
                        "target_function": test.target_function,
                        "mock_requirements": test.mock_requirements
                    }
                    for test in tests
                ]
            }
            
            return json.dumps(response, indent=2)
            
        except Exception as e:
            logger.error(f"Error generating tests: {e}")
            raise McpError("INTERNAL_ERROR", f"Failed to generate tests: {str(e)}")
    
    @mcp.tool("run_autocad_tests")
    async def run_autocad_tests(
        self,
        test_path: str,
        mock_mode: bool = True,
        timeout: int = 300
    ) -> str:
        """
        Run AutoCAD automation tests.
        
        Args:
            test_path: Path to test file or directory
            mock_mode: Whether to run in mock mode (no real AutoCAD needed)
            timeout: Test timeout in seconds
            
        Returns:
            JSON string with test execution results
        """
        try:
            test_framework = self._get_test_framework()
            
            # Create test suite
            suite_name = f"autocad_tests_{int(time.time())}"
            test_framework.create_test_suite(suite_name, mock_mode=mock_mode)
            
            # Run tests (simplified - would need actual test discovery)
            results = []
            
            response = {
                "test_path": test_path,
                "suite_name": suite_name,
                "mock_mode": mock_mode,
                "timeout": timeout,
                "tests_run": len(results),
                "results": results
            }
            
            return json.dumps(response, indent=2)
            
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            raise McpError("INTERNAL_ERROR", f"Failed to run tests: {str(e)}")
    
    @mcp.tool("create_project_from_template")
    async def create_project_from_template(
        self,
        template_name: str,
        project_name: str,
        output_dir: str,
        parameters: Optional[str] = None
    ) -> str:
        """
        Create a new AutoCAD automation project from a template.
        
        Args:
            template_name: Name of the template to use
            project_name: Name for the new project
            output_dir: Directory to create the project in
            parameters: JSON string with template parameters
            
        Returns:
            JSON string with project creation results
        """
        try:
            scaffolder = self._get_project_scaffolder()
            
            # Parse parameters
            params = {}
            if parameters:
                try:
                    params = json.loads(parameters)
                except:
                    logger.warning(f"Invalid parameters JSON: {parameters}")
            
            # Set basic parameters
            params.update({
                "project_name": project_name,
                "project_slug": project_name.lower().replace(' ', '_')
            })
            
            # Create project
            project_path = scaffolder.create_project(
                template_name=template_name,
                project_path=output_dir,
                parameters=params
            )
            
            response = {
                "template_name": template_name,
                "project_name": project_name,
                "project_path": project_path,
                "parameters": params,
                "created": True
            }
            
            return json.dumps(response, indent=2)
            
        except Exception as e:
            logger.error(f"Error creating project: {e}")
            raise McpError("INTERNAL_ERROR", f"Failed to create project: {str(e)}")
    
    @mcp.tool("generate_ci_config")
    async def generate_ci_config(
        self,
        provider: str,
        project_path: str,
        test_commands: Optional[str] = None
    ) -> str:
        """
        Generate CI/CD configuration for AutoCAD project.
        
        Args:
            provider: CI provider (github, azure, jenkins)
            project_path: Path to the project
            test_commands: Comma-separated test commands
            
        Returns:
            JSON string with CI configuration results
        """
        try:
            ci_integration = self._get_ci_integration()
            
            # Parse test commands
            commands = test_commands.split(',') if test_commands else None
            
            # Generate CI configuration
            config_file = ci_integration.generate_ci_config(
                provider=provider,
                project_path=project_path,
                test_commands=commands
            )
            
            response = {
                "provider": provider,
                "project_path": project_path,
                "config_file": config_file,
                "test_commands": commands,
                "generated": True
            }
            
            return json.dumps(response, indent=2)
            
        except Exception as e:
            logger.error(f"Error generating CI config: {e}")
            raise McpError("INTERNAL_ERROR", f"Failed to generate CI config: {str(e)}")

    # Helper methods for Phase 4 components (lazy loading)
    
    def _get_test_generator(self):
        """Get test generator instance with lazy loading."""
        if not hasattr(self, '_test_generator'):
            from ..testing.test_generators import TestGenerator
            self._test_generator = TestGenerator()
        return self._test_generator
    
    def _get_test_framework(self):
        """Get test framework instance with lazy loading."""
        if not hasattr(self, '_test_framework'):
            from ..testing.autocad_test_framework import AutoCADTestFramework
            self._test_framework = AutoCADTestFramework(mock_mode=True)
        return self._test_framework
    
    def _get_project_scaffolder(self):
        """Get project scaffolder instance with lazy loading."""
        if not hasattr(self, '_project_scaffolder'):
            from ..project_templates.project_scaffolder import ProjectScaffolder
            self._project_scaffolder = ProjectScaffolder()
        return self._project_scaffolder
    
    def _get_ci_integration(self):
        """Get CI integration instance with lazy loading."""
        if not hasattr(self, '_ci_integration'):
            from ..testing.ci_integration import CIIntegration
            self._ci_integration = CIIntegration()
        return self._ci_integration
    
    def _get_documentation_generator(self):
        """Get documentation generator instance with lazy loading."""
        if not hasattr(self, '_documentation_generator'):
            from ..project_templates.documentation_generator import DocumentationGenerator
            self._documentation_generator = DocumentationGenerator()
        return self._documentation_generator

    def get_mcp_server(self) -> FastMCP:
        """
        Get the MCP server instance.

        Returns:
            FastMCP server instance
        """
        return self.mcp

    async def run_server(self, host: str = "localhost", port: int = 5002):
        """
        Run the enhanced MCP server.

        Args:
            host: Server host
            port: Server port
        """
        logger.info(f"Starting Enhanced MCP Server on {host}:{port}")
        await self.mcp.run(host=host, port=port)
