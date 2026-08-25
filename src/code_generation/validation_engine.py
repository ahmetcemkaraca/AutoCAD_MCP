"""
Validation Engine for Master AutoCAD Coder.

Validates generated code for syntax, best practices, and AutoCAD compatibility.
Provides comprehensive analysis and suggestions for improvement.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import re
import ast
import subprocess
import tempfile
from pathlib import Path
import logging


@dataclass
class ValidationIssue:
    """Represents a validation issue."""
    severity: str  # error, warning, info
    category: str  # syntax, style, performance, security, compatibility
    message: str
    line_number: Optional[int] = None
    column: Optional[int] = None
    suggestion: Optional[str] = None
    code_snippet: Optional[str] = None


@dataclass
class ValidationResult:
    """Results of code validation."""
    valid: bool
    language: str
    issues: List[ValidationIssue]
    quality_score: float  # 0-100
    summary: Dict[str, Any]
    suggestions: List[str]


class ValidationEngine:
    """Validates generated code across multiple languages."""
    
    def __init__(self):
        self.python_validators = self._initialize_python_validators()
        self.autolisp_validators = self._initialize_autolisp_validators()
        self.vba_validators = self._initialize_vba_validators()
        self.common_patterns = self._initialize_common_patterns()
    
    def _initialize_python_validators(self) -> Dict[str, Any]:
        """Initialize Python-specific validators."""
        return {
            "required_imports": [
                "from src.enhanced_autocad.compatibility_layer import Autocad",
                "import logging"
            ],
            "forbidden_patterns": [
                r"\beval\s*\(",  # Dangerous eval usage
                r"\bexec\s*\(",  # Dangerous exec usage
                r"__import__",   # Dynamic imports
                r"os\.system",   # System calls
            ],
            "required_patterns": [
                r"if\s+__name__\s*==\s*['\"]__main__['\"]:",  # Main guard
                r"def\s+main\s*\(",  # Main function
                r"try:",  # Error handling
                r"except\s+\w*Exception"  # Exception handling
            ],
            "style_checks": {
                "line_length": 120,
                "function_naming": r"^[a-z_][a-z0-9_]*$",
                "class_naming": r"^[A-Z][a-zA-Z0-9]*$",
                "constant_naming": r"^[A-Z][A-Z0-9_]*$"
            }
        }
    
    def _initialize_autolisp_validators(self) -> Dict[str, Any]:
        """Initialize AutoLISP-specific validators."""
        return {
            "required_patterns": [
                r"\(defun\s+c:",  # Command function
                r"\(princ\)",     # Princ at end
            ],
            "balanced_parens": True,
            "function_conventions": {
                "command_prefix": "c:",
                "local_vars": r"\/\s*[\w\s]*\)",
                "comments": r";;.*"
            },
            "forbidden_patterns": [
                r"\(vl-load-com\)\s*\(vlax",  # Unsafe COM loading without checks
            ],
            "autocad_functions": [
                "getpoint", "getdist", "getstring", "getint", "getreal",
                "ssget", "entsel", "entget", "entmod", "entmake",
                "command", "princ", "print", "prompt"
            ]
        }
    
    def _initialize_vba_validators(self) -> Dict[str, Any]:
        """Initialize VBA-specific validators."""
        return {
            "required_patterns": [
                r"Option\s+Explicit",  # Option Explicit
                r"On\s+Error\s+GoTo",  # Error handling
                r"Dim\s+\w+\s+As\s+",  # Variable declarations
            ],
            "autocad_objects": [
                "AcadApplication", "AcadDocument", "AcadEntity",
                "AcadLine", "AcadCircle", "AcadPolyline"
            ],
            "error_handling": [
                r"On\s+Error\s+GoTo\s+\w+",
                r"ErrorHandler:",
                r"Exit\s+(Sub|Function)"
            ],
            "cleanup_patterns": [
                r"Set\s+\w+\s*=\s*Nothing",  # Object cleanup
                r"\.Quit",  # Application cleanup
            ]
        }
    
    def _initialize_common_patterns(self) -> Dict[str, Any]:
        """Initialize common validation patterns."""
        return {
            "security_risks": [
                r"password\s*=\s*['\"][^'\"]*['\"]",  # Hardcoded passwords
                r"api_key\s*=\s*['\"][^'\"]*['\"]",   # API keys
                r"secret\s*=\s*['\"][^'\"]*['\"]",   # Secrets
            ],
            "performance_issues": [
                r"for\s+.*\s+in\s+range\(len\(",  # Python inefficient loops
                r"while\s+True:",  # Potential infinite loops
            ],
            "compatibility_issues": [
                r"\\\\",  # Windows path separators
                r"C:\\\\",  # Hardcoded paths
            ]
        }
    
    def validate_code(self, code: str, language: str, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate code in the specified language."""
        if language.lower() == "python":
            return self._validate_python_code(code, context)
        elif language.lower() == "autolisp":
            return self._validate_autolisp_code(code, context)
        elif language.lower() == "vba":
            return self._validate_vba_code(code, context)
        else:
            return ValidationResult(
                valid=False,
                language=language,
                issues=[ValidationIssue("error", "validation", f"Unsupported language: {language}")],
                quality_score=0,
                summary={"error": "Unsupported language"},
                suggestions=[]
            )
    
    def _validate_python_code(self, code: str, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate Python code."""
        issues = []
        
        # Syntax validation
        syntax_issues = self._check_python_syntax(code)
        issues.extend(syntax_issues)
        
        # Import validation
        import_issues = self._check_python_imports(code)
        issues.extend(import_issues)
        
        # Security validation
        security_issues = self._check_security_issues(code, "python")
        issues.extend(security_issues)
        
        # Style validation
        style_issues = self._check_python_style(code)
        issues.extend(style_issues)
        
        # AutoCAD integration validation
        autocad_issues = self._check_python_autocad_integration(code)
        issues.extend(autocad_issues)
        
        # Calculate quality score
        quality_score = self._calculate_quality_score(issues)
        
        # Generate suggestions
        suggestions = self._generate_python_suggestions(issues, code)
        
        return ValidationResult(
            valid=not any(issue.severity == "error" for issue in issues),
            language="python",
            issues=issues,
            quality_score=quality_score,
            summary=self._create_summary(issues),
            suggestions=suggestions
        )
    
    def _check_python_syntax(self, code: str) -> List[ValidationIssue]:
        """Check Python syntax."""
        issues = []
        
        try:
            ast.parse(code)
        except SyntaxError as e:
            issues.append(ValidationIssue(
                severity="error",
                category="syntax",
                message=f"Syntax error: {str(e)}",
                line_number=e.lineno,
                column=e.offset,
                suggestion="Fix the syntax error before running the code"
            ))
        except Exception as e:
            issues.append(ValidationIssue(
                severity="error",
                category="syntax",
                message=f"Parse error: {str(e)}",
                suggestion="Check for invalid Python constructs"
            ))
        
        return issues
    
    def _check_python_imports(self, code: str) -> List[ValidationIssue]:
        """Check Python imports."""
        issues = []
        validators = self.python_validators
        
        # Check for required imports
        for required_import in validators["required_imports"]:
            if required_import not in code:
                issues.append(ValidationIssue(
                    severity="warning",
                    category="style",
                    message=f"Missing recommended import: {required_import}",
                    suggestion=f"Add: {required_import}"
                ))
        
        # Check for forbidden patterns
        for pattern in validators["forbidden_patterns"]:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                issues.append(ValidationIssue(
                    severity="error",
                    category="security",
                    message=f"Dangerous pattern detected: {match.group()}",
                    line_number=line_num,
                    suggestion="Replace with safer alternative"
                ))
        
        return issues
    
    def _check_python_style(self, code: str) -> List[ValidationIssue]:
        """Check Python style guidelines."""
        issues = []
        lines = code.split('\n')
        
        # Check line length
        max_length = self.python_validators["style_checks"]["line_length"]
        for i, line in enumerate(lines, 1):
            if len(line) > max_length:
                issues.append(ValidationIssue(
                    severity="info",
                    category="style",
                    message=f"Line too long ({len(line)} > {max_length} characters)",
                    line_number=i,
                    suggestion="Break long lines for better readability"
                ))
        
        # Check function naming
        function_pattern = self.python_validators["style_checks"]["function_naming"]
        function_matches = re.finditer(r'def\s+(\w+)\s*\(', code)
        for match in function_matches:
            func_name = match.group(1)
            if not re.match(function_pattern, func_name):
                line_num = code[:match.start()].count('\n') + 1
                issues.append(ValidationIssue(
                    severity="info",
                    category="style",
                    message=f"Function name '{func_name}' doesn't follow snake_case convention",
                    line_number=line_num,
                    suggestion="Use snake_case for function names"
                ))
        
        return issues
    
    def _check_python_autocad_integration(self, code: str) -> List[ValidationIssue]:
        """Check AutoCAD integration patterns."""
        issues = []
        
        # Check for AutoCAD connection
        if "Autocad()" in code:
            if "get_connection_status" not in code:
                issues.append(ValidationIssue(
                    severity="warning",
                    category="compatibility",
                    message="AutoCAD connection not verified",
                    suggestion="Add connection status check: acad.get_connection_status()['connected']"
                ))
        
        # Check for error handling around AutoCAD operations
        autocad_operations = ["AddLine", "AddCircle", "AddPolyline", "model"]
        for operation in autocad_operations:
            if operation in code and "try:" not in code:
                issues.append(ValidationIssue(
                    severity="warning",
                    category="compatibility",
                    message=f"AutoCAD operation '{operation}' without error handling",
                    suggestion="Wrap AutoCAD operations in try/except blocks"
                ))
        
        return issues
    
    def _validate_autolisp_code(self, code: str, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate AutoLISP code."""
        issues = []
        
        # Syntax validation
        syntax_issues = self._check_autolisp_syntax(code)
        issues.extend(syntax_issues)
        
        # Structure validation
        structure_issues = self._check_autolisp_structure(code)
        issues.extend(structure_issues)
        
        # Function validation
        function_issues = self._check_autolisp_functions(code)
        issues.extend(function_issues)
        
        # Security validation
        security_issues = self._check_security_issues(code, "autolisp")
        issues.extend(security_issues)
        
        quality_score = self._calculate_quality_score(issues)
        suggestions = self._generate_autolisp_suggestions(issues, code)
        
        return ValidationResult(
            valid=not any(issue.severity == "error" for issue in issues),
            language="autolisp",
            issues=issues,
            quality_score=quality_score,
            summary=self._create_summary(issues),
            suggestions=suggestions
        )
    
    def _check_autolisp_syntax(self, code: str) -> List[ValidationIssue]:
        """Check AutoLISP syntax."""
        issues = []
        
        # Check parentheses balance
        open_parens = code.count('(')
        close_parens = code.count(')')
        
        if open_parens != close_parens:
            issues.append(ValidationIssue(
                severity="error",
                category="syntax",
                message=f"Unbalanced parentheses: {open_parens} open, {close_parens} close",
                suggestion="Ensure all parentheses are properly balanced"
            ))
        
        # Check for double quotes balance
        quote_count = code.count('"')
        if quote_count % 2 != 0:
            issues.append(ValidationIssue(
                severity="error",
                category="syntax",
                message="Unbalanced double quotes",
                suggestion="Ensure all strings are properly quoted"
            ))
        
        return issues
    
    def _check_autolisp_structure(self, code: str) -> List[ValidationIssue]:
        """Check AutoLISP code structure."""
        issues = []
        validators = self.autolisp_validators
        
        # Check for required patterns
        for pattern in validators["required_patterns"]:
            if not re.search(pattern, code):
                pattern_name = pattern.replace(r"\\", "").replace("(", "").replace(")", "")
                issues.append(ValidationIssue(
                    severity="warning",
                    category="style",
                    message=f"Missing recommended pattern: {pattern_name}",
                    suggestion=f"Consider adding {pattern_name} for proper AutoLISP structure"
                ))
        
        # Check command function structure
        command_matches = re.finditer(r'\(defun\s+(c:\w+)', code)
        for match in command_matches:
            cmd_name = match.group(1)
            # Look for princ at the end of the function
            func_start = match.start()
            paren_count = 0
            func_end = func_start
            
            for i, char in enumerate(code[func_start:], func_start):
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                    if paren_count == 0:
                        func_end = i
                        break
            
            func_code = code[func_start:func_end+1]
            if not re.search(r'\(princ\)', func_code):
                line_num = code[:match.start()].count('\n') + 1
                issues.append(ValidationIssue(
                    severity="warning",
                    category="style",
                    message=f"Command function {cmd_name} missing (princ) at end",
                    line_number=line_num,
                    suggestion="Add (princ) at the end of command functions"
                ))
        
        return issues
    
    def _check_autolisp_functions(self, code: str) -> List[ValidationIssue]:
        """Check AutoLISP function usage."""
        issues = []
        
        # Check for common AutoCAD function usage
        autocad_functions = self.autolisp_validators["autocad_functions"]
        used_functions = []
        
        for func in autocad_functions:
            if re.search(rf'\({func}\b', code):
                used_functions.append(func)
        
        # Provide suggestions for commonly missed functions
        if "getpoint" not in used_functions and "command" in used_functions:
            issues.append(ValidationIssue(
                severity="info",
                category="style",
                message="Consider using (getpoint) for user input instead of hardcoded coordinates",
                suggestion="Use (getpoint \"Specify point: \") for interactive point selection"
            ))
        
        return issues
    
    def _validate_vba_code(self, code: str, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate VBA code."""
        issues = []
        
        # Structure validation
        structure_issues = self._check_vba_structure(code)
        issues.extend(structure_issues)
        
        # Error handling validation
        error_issues = self._check_vba_error_handling(code)
        issues.extend(error_issues)
        
        # Object cleanup validation
        cleanup_issues = self._check_vba_cleanup(code)
        issues.extend(cleanup_issues)
        
        # AutoCAD integration validation
        autocad_issues = self._check_vba_autocad_integration(code)
        issues.extend(autocad_issues)
        
        # Security validation
        security_issues = self._check_security_issues(code, "vba")
        issues.extend(security_issues)
        
        quality_score = self._calculate_quality_score(issues)
        suggestions = self._generate_vba_suggestions(issues, code)
        
        return ValidationResult(
            valid=not any(issue.severity == "error" for issue in issues),
            language="vba",
            issues=issues,
            quality_score=quality_score,
            summary=self._create_summary(issues),
            suggestions=suggestions
        )
    
    def _check_vba_structure(self, code: str) -> List[ValidationIssue]:
        """Check VBA code structure."""
        issues = []
        validators = self.vba_validators
        
        # Check for required patterns
        for pattern in validators["required_patterns"]:
            if not re.search(pattern, code, re.IGNORECASE):
                if "Option Explicit" in pattern:
                    issues.append(ValidationIssue(
                        severity="warning",
                        category="style",
                        message="Missing 'Option Explicit' declaration",
                        suggestion="Add 'Option Explicit' at the top of the module"
                    ))
                elif "On Error GoTo" in pattern:
                    issues.append(ValidationIssue(
                        severity="warning",
                        category="style",
                        message="Missing error handling",
                        suggestion="Add 'On Error GoTo ErrorHandler' for proper error handling"
                    ))
        
        return issues
    
    def _check_vba_error_handling(self, code: str) -> List[ValidationIssue]:
        """Check VBA error handling patterns."""
        issues = []
        
        # Check for error handlers
        error_patterns = self.vba_validators["error_handling"]
        has_error_goto = any(re.search(pattern, code, re.IGNORECASE) for pattern in error_patterns)
        
        if "Sub " in code or "Function " in code:
            if not has_error_goto:
                issues.append(ValidationIssue(
                    severity="warning",
                    category="style",
                    message="Missing error handling in procedure",
                    suggestion="Add 'On Error GoTo ErrorHandler' and create error handling section"
                ))
        
        # Check for proper exit statements
        if "On Error GoTo" in code:
            if not re.search(r'Exit\s+(Sub|Function)', code, re.IGNORECASE):
                issues.append(ValidationIssue(
                    severity="warning",
                    category="style",
                    message="Missing Exit statement before error handler",
                    suggestion="Add 'Exit Sub' or 'Exit Function' before ErrorHandler label"
                ))
        
        return issues
    
    def _check_vba_cleanup(self, code: str) -> List[ValidationIssue]:
        """Check VBA object cleanup."""
        issues = []
        
        # Find object declarations
        object_declarations = re.finditer(r'Set\s+(\w+)\s*=\s*(GetObject|CreateObject)', code, re.IGNORECASE)
        declared_objects = [match.group(1) for match in object_declarations]
        
        # Check if objects are cleaned up
        for obj_name in declared_objects:
            cleanup_pattern = rf'Set\s+{obj_name}\s*=\s*Nothing'
            if not re.search(cleanup_pattern, code, re.IGNORECASE):
                issues.append(ValidationIssue(
                    severity="warning",
                    category="style",
                    message=f"Object '{obj_name}' not properly cleaned up",
                    suggestion=f"Add 'Set {obj_name} = Nothing' before procedure exit"
                ))
        
        return issues
    
    def _check_vba_autocad_integration(self, code: str) -> List[ValidationIssue]:
        """Check VBA AutoCAD integration."""
        issues = []
        
        # Check for AutoCAD object usage
        autocad_objects = self.vba_validators["autocad_objects"]
        used_objects = [obj for obj in autocad_objects if obj in code]
        
        if used_objects:
            # Check for AutoCAD Type Library reference hint
            if "GetObject" in code and "AutoCAD.Application" in code:
                if "Add reference to AutoCAD Type Library" not in code:
                    issues.append(ValidationIssue(
                        severity="info",
                        category="compatibility",
                        message="AutoCAD integration detected",
                        suggestion="Ensure AutoCAD Type Library reference is added in VBA Editor"
                    ))
        
        return issues
    
    def _check_security_issues(self, code: str, language: str) -> List[ValidationIssue]:
        """Check for security issues."""
        issues = []
        
        # Check common security patterns
        for pattern in self.common_patterns["security_risks"]:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                issues.append(ValidationIssue(
                    severity="error",
                    category="security",
                    message=f"Potential security risk: hardcoded sensitive data",
                    line_number=line_num,
                    suggestion="Move sensitive data to environment variables or configuration files"
                ))
        
        return issues
    
    def _calculate_quality_score(self, issues: List[ValidationIssue]) -> float:
        """Calculate overall quality score."""
        if not issues:
            return 100.0
        
        error_penalty = sum(20 for issue in issues if issue.severity == "error")
        warning_penalty = sum(10 for issue in issues if issue.severity == "warning")
        info_penalty = sum(2 for issue in issues if issue.severity == "info")
        
        total_penalty = error_penalty + warning_penalty + info_penalty
        score = max(0, 100 - total_penalty)
        
        return score
    
    def _create_summary(self, issues: List[ValidationIssue]) -> Dict[str, Any]:
        """Create validation summary."""
        summary = {
            "total_issues": len(issues),
            "errors": sum(1 for issue in issues if issue.severity == "error"),
            "warnings": sum(1 for issue in issues if issue.severity == "warning"),
            "info": sum(1 for issue in issues if issue.severity == "info"),
            "categories": {}
        }
        
        # Count by category
        for issue in issues:
            summary["categories"][issue.category] = summary["categories"].get(issue.category, 0) + 1
        
        return summary
    
    def _generate_python_suggestions(self, issues: List[ValidationIssue], code: str) -> List[str]:
        """Generate Python-specific suggestions."""
        suggestions = []
        
        if not any("import logging" in str(issue) for issue in issues):
            if "logging" not in code:
                suggestions.append("Add logging for better debugging and monitoring")
        
        if "def main():" not in code:
            suggestions.append("Create a main() function for better code organization")
        
        if not any("try:" in line for line in code.split('\n')):
            suggestions.append("Add error handling with try/except blocks")
        
        return suggestions
    
    def _generate_autolisp_suggestions(self, issues: List[ValidationIssue], code: str) -> List[str]:
        """Generate AutoLISP-specific suggestions."""
        suggestions = []
        
        if not re.search(r';; .*', code):
            suggestions.append("Add comments to explain the code functionality")
        
        if "getpoint" not in code and "command" in code:
            suggestions.append("Consider using interactive input functions like (getpoint)")
        
        if not re.search(r'\(princ\)', code):
            suggestions.append("End command functions with (princ) to suppress return values")
        
        return suggestions
    
    def _generate_vba_suggestions(self, issues: List[ValidationIssue], code: str) -> List[str]:
        """Generate VBA-specific suggestions."""
        suggestions = []
        
        if "Option Explicit" not in code:
            suggestions.append("Add 'Option Explicit' to catch variable declaration errors")
        
        if "On Error GoTo" not in code:
            suggestions.append("Implement proper error handling with 'On Error GoTo ErrorHandler'")
        
        if "CreateObject" in code or "GetObject" in code:
            suggestions.append("Ensure proper object cleanup with 'Set object = Nothing'")
        
        return suggestions
    
    def validate_multiple_files(self, files: Dict[str, str]) -> Dict[str, ValidationResult]:
        """Validate multiple code files."""
        results = {}
        
        for filename, code in files.items():
            # Determine language from file extension
            extension = Path(filename).suffix.lower()
            if extension == ".py":
                language = "python"
            elif extension in [".lsp", ".lisp"]:
                language = "autolisp"
            elif extension in [".bas", ".cls", ".frm"]:
                language = "vba"
            else:
                # Try to detect from content
                language = self._detect_language(code)
            
            results[filename] = self.validate_code(code, language)
        
        return results
    
    def _detect_language(self, code: str) -> str:
        """Detect programming language from code content."""
        # Simple heuristics for language detection
        if re.search(r'def\s+\w+\s*\(', code) and "import" in code:
            return "python"
        elif re.search(r'\(defun\s+', code) and code.count('(') > code.count('{'):
            return "autolisp"
        elif re.search(r'Sub\s+\w+\s*\(', code, re.IGNORECASE) or "Option Explicit" in code:
            return "vba"
        else:
            return "unknown"
    
    def generate_validation_report(self, results: Dict[str, ValidationResult]) -> str:
        """Generate a comprehensive validation report."""
        report_lines = [
            "=" * 60,
            "CODE VALIDATION REPORT",
            "=" * 60,
            f"Generated: {logging.Formatter().formatTime(logging.makeLogRecord({}), None)}",
            ""
        ]
        
        # Overall summary
        total_files = len(results)
        valid_files = sum(1 for result in results.values() if result.valid)
        avg_quality = sum(result.quality_score for result in results.values()) / total_files if total_files > 0 else 0
        
        report_lines.extend([
            "OVERALL SUMMARY",
            "-" * 20,
            f"Files Analyzed: {total_files}",
            f"Valid Files: {valid_files}",
            f"Files with Issues: {total_files - valid_files}",
            f"Average Quality Score: {avg_quality:.1f}/100",
            ""
        ])
        
        # Individual file results
        for filename, result in results.items():
            report_lines.extend([
                f"FILE: {filename}",
                "-" * 40,
                f"Language: {result.language}",
                f"Valid: {'Yes' if result.valid else 'No'}",
                f"Quality Score: {result.quality_score:.1f}/100",
                f"Issues: {len(result.issues)} (Errors: {result.summary['errors']}, "
                f"Warnings: {result.summary['warnings']}, Info: {result.summary['info']})",
                ""
            ])
            
            # List issues
            if result.issues:
                report_lines.append("Issues:")
                for issue in result.issues:
                    location = f" (Line {issue.line_number})" if issue.line_number else ""
                    report_lines.append(f"  [{issue.severity.upper()}] {issue.message}{location}")
                    if issue.suggestion:
                        report_lines.append(f"    Suggestion: {issue.suggestion}")
                report_lines.append("")
            
            # List suggestions
            if result.suggestions:
                report_lines.append("Suggestions:")
                for suggestion in result.suggestions:
                    report_lines.append(f"  - {suggestion}")
                report_lines.append("")
        
        return "\n".join(report_lines)