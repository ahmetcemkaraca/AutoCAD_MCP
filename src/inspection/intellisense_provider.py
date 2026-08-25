"""
IntelliSense Provider for VS Code Integration
============================================

Provides comprehensive IntelliSense support for AutoCAD development in VS Code.
Integrates with object inspector and method discoverer to provide context-aware
code completion, hover information, and signature help.
"""

import logging
import time
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .object_inspector import ObjectInspector, InspectionDepth
from .property_analyzer import PropertyAnalyzer
from .method_discoverer import MethodDiscoverer

logger = logging.getLogger(__name__)


class CompletionItemKind(Enum):
    """VS Code completion item kinds."""
    TEXT = 1
    METHOD = 2
    FUNCTION = 3
    CONSTRUCTOR = 4
    FIELD = 5
    VARIABLE = 6
    CLASS = 7
    INTERFACE = 8
    MODULE = 9
    PROPERTY = 10
    UNIT = 11
    VALUE = 12
    ENUM = 13
    KEYWORD = 14
    SNIPPET = 15
    COLOR = 16
    FILE = 17
    REFERENCE = 18


@dataclass
class CompletionItem:
    """VS Code completion item."""
    label: str
    kind: CompletionItemKind
    detail: Optional[str] = None
    documentation: Optional[str] = None
    insert_text: Optional[str] = None
    filter_text: Optional[str] = None
    sort_text: Optional[str] = None
    additional_text_edits: List[Dict[str, Any]] = field(default_factory=list)
    command: Optional[Dict[str, Any]] = None


@dataclass
class HoverInfo:
    """VS Code hover information."""
    contents: List[str]
    range: Optional[Dict[str, Any]] = None


@dataclass
class SignatureInformation:
    """Method signature information for VS Code."""
    label: str
    documentation: Optional[str] = None
    parameters: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SignatureHelp:
    """VS Code signature help."""
    signatures: List[SignatureInformation]
    active_signature: int = 0
    active_parameter: int = 0


class IntelliSenseProvider:
    """
    Comprehensive IntelliSense provider for AutoCAD development in VS Code.
    """

    def __init__(self, autocad_wrapper=None):
        """
        Initialize IntelliSense provider.

        Args:
            autocad_wrapper: AutoCAD wrapper for object access
        """
        self.autocad_wrapper = autocad_wrapper
        self.object_inspector = ObjectInspector(autocad_wrapper)
        self.property_analyzer = PropertyAnalyzer()
        self.method_discoverer = MethodDiscoverer()
        
        # Completion cache
        self.completion_cache = {}
        self.cache_timeout = 300  # 5 minutes
        
        # AutoCAD-specific completions
        self.autocad_keywords = self._initialize_autocad_keywords()
        self.code_snippets = self._initialize_code_snippets()
        
        logger.info("IntelliSenseProvider initialized")

    def get_completions(self, document_text: str, position: Dict[str, int], 
                       context: Optional[Dict[str, Any]] = None) -> List[CompletionItem]:
        """
        Get code completions for the current position.

        Args:
            document_text: Full document text
            position: Cursor position {line: int, character: int}
            context: Additional context information

        Returns:
            List of completion items
        """
        try:
            # Extract context around cursor
            line_text, word_at_cursor, prefix = self._extract_context(document_text, position)
            
            # Check cache
            cache_key = f"{hash(line_text)}_{word_at_cursor}_{prefix}"
            if cache_key in self.completion_cache:
                cached_result, cache_time = self.completion_cache[cache_key]
                if time.time() - cache_time < self.cache_timeout:
                    return cached_result

            completions = []

            # Determine completion type based on context
            if '.' in prefix:
                # Member completions (obj.member)
                completions.extend(self._get_member_completions(prefix, line_text))
            else:
                # Top-level completions
                completions.extend(self._get_top_level_completions(prefix, document_text))

            # Add context-specific completions
            completions.extend(self._get_context_completions(line_text, document_text))

            # Sort and filter completions
            completions = self._filter_and_sort_completions(completions, word_at_cursor)

            # Cache results
            self.completion_cache[cache_key] = (completions, time.time())

            logger.debug(f"Generated {len(completions)} completions for context: {prefix}")
            return completions

        except Exception as e:
            logger.error(f"Error getting completions: {str(e)}")
            return []

    def get_hover_info(self, document_text: str, position: Dict[str, int]) -> Optional[HoverInfo]:
        """
        Get hover information for the symbol at position.

        Args:
            document_text: Full document text
            position: Cursor position

        Returns:
            Hover information or None
        """
        try:
            line_text, word_at_cursor, prefix = self._extract_context(document_text, position)
            
            if not word_at_cursor:
                return None

            contents = []

            # Check if it's a member access
            if '.' in prefix:
                obj_path, member_name = prefix.rsplit('.', 1)
                if member_name == word_at_cursor:
                    obj = self._resolve_object_path(obj_path)
                    if obj:
                        # Get member information
                        hover_content = self._get_member_hover_info(obj, member_name)
                        if hover_content:
                            contents.extend(hover_content)
            else:
                # Top-level symbol
                hover_content = self._get_symbol_hover_info(word_at_cursor, document_text)
                if hover_content:
                    contents.extend(hover_content)

            if contents:
                return HoverInfo(contents=contents)

            return None

        except Exception as e:
            logger.error(f"Error getting hover info: {str(e)}")
            return None

    def get_signature_help(self, document_text: str, position: Dict[str, int]) -> Optional[SignatureHelp]:
        """
        Get signature help for method calls.

        Args:
            document_text: Full document text
            position: Cursor position

        Returns:
            Signature help information
        """
        try:
            # Find the method call context
            method_call_info = self._find_method_call_context(document_text, position)
            if not method_call_info:
                return None

            obj_path, method_name, param_index = method_call_info
            
            # Resolve the object
            obj = self._resolve_object_path(obj_path)
            if not obj:
                return None

            # Get method information
            try:
                method_info = self.method_discoverer.discover_method(obj, method_name)
                
                # Create signature information
                signature = SignatureInformation(
                    label=method_info.signature,
                    documentation=method_info.documentation.description if method_info.documentation else None
                )

                # Add parameter information
                for param in method_info.parameters:
                    if param.name in ['self', 'cls']:
                        continue
                    
                    param_doc = ""
                    if method_info.documentation and param.name in method_info.documentation.parameters:
                        param_doc = method_info.documentation.parameters[param.name]
                    
                    signature.parameters.append({
                        "label": param.name,
                        "documentation": param_doc
                    })

                return SignatureHelp(
                    signatures=[signature],
                    active_signature=0,
                    active_parameter=min(param_index, len(signature.parameters) - 1)
                )

            except Exception as e:
                logger.debug(f"Error getting method signature for {method_name}: {str(e)}")
                return None

        except Exception as e:
            logger.error(f"Error getting signature help: {str(e)}")
            return None

    def get_definition_location(self, document_text: str, position: Dict[str, int]) -> Optional[Dict[str, Any]]:
        """
        Get definition location for go-to-definition feature.

        Args:
            document_text: Full document text
            position: Cursor position

        Returns:
            Definition location information
        """
        try:
            line_text, word_at_cursor, prefix = self._extract_context(document_text, position)
            
            if not word_at_cursor:
                return None

            # For AutoCAD objects, we can provide synthetic locations
            # In a real implementation, this would point to documentation or source files
            
            if word_at_cursor in ['acad', 'app', 'doc', 'model']:
                return {
                    "uri": "autocad://documentation/" + word_at_cursor,
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 0, "character": len(word_at_cursor)}
                    }
                }

            return None

        except Exception as e:
            logger.error(f"Error getting definition location: {str(e)}")
            return None

    def get_document_symbols(self, document_text: str) -> List[Dict[str, Any]]:
        """
        Get document symbols for outline and navigation.

        Args:
            document_text: Full document text

        Returns:
            List of document symbols
        """
        symbols = []
        
        try:
            lines = document_text.split('\n')
            
            for line_no, line in enumerate(lines):
                line = line.strip()
                
                # Find function definitions
                if line.startswith('def '):
                    func_match = re.match(r'def\s+(\w+)\s*\(', line)
                    if func_match:
                        symbols.append({
                            "name": func_match.group(1),
                            "kind": CompletionItemKind.FUNCTION.value,
                            "range": {
                                "start": {"line": line_no, "character": 0},
                                "end": {"line": line_no, "character": len(line)}
                            },
                            "selectionRange": {
                                "start": {"line": line_no, "character": line.find(func_match.group(1))},
                                "end": {"line": line_no, "character": line.find(func_match.group(1)) + len(func_match.group(1))}
                            }
                        })
                
                # Find class definitions
                elif line.startswith('class '):
                    class_match = re.match(r'class\s+(\w+)', line)
                    if class_match:
                        symbols.append({
                            "name": class_match.group(1),
                            "kind": CompletionItemKind.CLASS.value,
                            "range": {
                                "start": {"line": line_no, "character": 0},
                                "end": {"line": line_no, "character": len(line)}
                            },
                            "selectionRange": {
                                "start": {"line": line_no, "character": line.find(class_match.group(1))},
                                "end": {"line": line_no, "character": line.find(class_match.group(1)) + len(class_match.group(1))}
                            }
                        })

        except Exception as e:
            logger.error(f"Error getting document symbols: {str(e)}")
        
        return symbols

    def _extract_context(self, document_text: str, position: Dict[str, int]) -> Tuple[str, str, str]:
        """Extract context around cursor position."""
        lines = document_text.split('\n')
        line_no = position['line']
        char_no = position['character']
        
        if line_no >= len(lines):
            return "", "", ""
        
        line_text = lines[line_no]
        
        # Find word at cursor
        start = char_no
        while start > 0 and (line_text[start - 1].isalnum() or line_text[start - 1] in '_'):
            start -= 1
        
        end = char_no
        while end < len(line_text) and (line_text[end].isalnum() or line_text[end] in '_'):
            end += 1
        
        word_at_cursor = line_text[start:end]
        
        # Get prefix (everything before cursor that could be relevant)
        prefix_start = start
        while prefix_start > 0 and line_text[prefix_start - 1] in '._':
            prefix_start -= 1
            # Find start of previous word
            while prefix_start > 0 and (line_text[prefix_start - 1].isalnum() or line_text[prefix_start - 1] in '_'):
                prefix_start -= 1
        
        prefix = line_text[prefix_start:char_no]
        
        return line_text, word_at_cursor, prefix

    def _get_member_completions(self, prefix: str, line_text: str) -> List[CompletionItem]:
        """Get member completions for object.member pattern."""
        completions = []
        
        try:
            # Parse the object path
            parts = prefix.split('.')
            if len(parts) < 2:
                return completions
            
            obj_path = '.'.join(parts[:-1])
            partial_member = parts[-1]
            
            # Resolve the object
            obj = self._resolve_object_path(obj_path)
            if not obj:
                return completions
            
            # Get object properties
            try:
                all_properties = self.property_analyzer.analyze_all_properties(obj, include_inherited=False)
                for prop in all_properties:
                    if partial_member.lower() in prop.name.lower():
                        completions.append(CompletionItem(
                            label=prop.name,
                            kind=CompletionItemKind.PROPERTY,
                            detail=f"{prop.data_type}",
                            documentation=prop.documentation.description if prop.documentation else None,
                            insert_text=prop.name,
                            sort_text=f"1_{prop.name}"  # Properties first
                        ))
            except Exception as e:
                logger.debug(f"Error getting property completions: {str(e)}")
            
            # Get object methods
            try:
                all_methods = self.method_discoverer.discover_all_methods(obj, include_inherited=False)
                for method in all_methods:
                    if partial_member.lower() in method.name.lower():
                        # Create method completion with parameters
                        insert_text = method.name
                        if method.parameters:
                            param_names = [p.name for p in method.parameters if p.name not in ['self', 'cls']]
                            if param_names:
                                param_placeholders = [f"${{{i+1}:{name}}}" for i, name in enumerate(param_names)]
                                insert_text = f"{method.name}({', '.join(param_placeholders)})"
                            else:
                                insert_text = f"{method.name}()"
                        else:
                            insert_text = f"{method.name}()"
                        
                        completions.append(CompletionItem(
                            label=method.name,
                            kind=CompletionItemKind.METHOD,
                            detail=method.signature,
                            documentation=method.documentation.description if method.documentation else None,
                            insert_text=insert_text,
                            sort_text=f"2_{method.name}"  # Methods after properties
                        ))
            except Exception as e:
                logger.debug(f"Error getting method completions: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error getting member completions: {str(e)}")
        
        return completions

    def _get_top_level_completions(self, prefix: str, document_text: str) -> List[CompletionItem]:
        """Get top-level completions."""
        completions = []
        
        # AutoCAD object completions
        autocad_objects = [
            ("acad", "AutoCAD wrapper instance", CompletionItemKind.VARIABLE),
            ("app", "AutoCAD Application object", CompletionItemKind.VARIABLE),
            ("doc", "Active AutoCAD document", CompletionItemKind.VARIABLE),
            ("model", "Model space object", CompletionItemKind.VARIABLE),
        ]
        
        for name, description, kind in autocad_objects:
            if prefix.lower() in name.lower():
                completions.append(CompletionItem(
                    label=name,
                    kind=kind,
                    detail=description,
                    documentation=f"AutoCAD {name} object for automation",
                    insert_text=name,
                    sort_text=f"0_{name}"  # High priority
                ))
        
        # Python keywords and built-ins
        for keyword in self.autocad_keywords:
            if prefix.lower() in keyword.lower():
                completions.append(CompletionItem(
                    label=keyword,
                    kind=CompletionItemKind.KEYWORD,
                    insert_text=keyword,
                    sort_text=f"3_{keyword}"
                ))
        
        return completions

    def _get_context_completions(self, line_text: str, document_text: str) -> List[CompletionItem]:
        """Get context-specific completions based on surrounding code."""
        completions = []
        
        # Check for import context
        if 'import' in line_text:
            # Add AutoCAD-related import suggestions
            autocad_imports = [
                "from enhanced_autocad import EnhancedAutoCAD",
                "import math",
                "import time"
            ]
            
            for import_stmt in autocad_imports:
                completions.append(CompletionItem(
                    label=import_stmt,
                    kind=CompletionItemKind.SNIPPET,
                    insert_text=import_stmt,
                    sort_text=f"0_{import_stmt}"
                ))
        
        # Add code snippets based on context
        for snippet_name, snippet_info in self.code_snippets.items():
            if any(trigger in line_text.lower() for trigger in snippet_info["triggers"]):
                completions.append(CompletionItem(
                    label=snippet_info["label"],
                    kind=CompletionItemKind.SNIPPET,
                    detail=snippet_info["description"],
                    insert_text=snippet_info["body"],
                    sort_text=f"1_{snippet_name}"
                ))
        
        return completions

    def _filter_and_sort_completions(self, completions: List[CompletionItem], word_at_cursor: str) -> List[CompletionItem]:
        """Filter and sort completions based on relevance."""
        if not word_at_cursor:
            return sorted(completions, key=lambda c: c.sort_text or c.label)[:50]
        
        # Score completions based on match quality
        scored_completions = []
        word_lower = word_at_cursor.lower()
        
        for completion in completions:
            label_lower = completion.label.lower()
            
            # Calculate relevance score
            if label_lower == word_lower:
                score = 100
            elif label_lower.startswith(word_lower):
                score = 90
            elif word_lower in label_lower:
                score = 70
            else:
                # Fuzzy matching score
                score = self._calculate_fuzzy_score(word_lower, label_lower)
            
            if score > 30:  # Threshold for inclusion
                scored_completions.append((score, completion))
        
        # Sort by score (descending) then by sort_text
        scored_completions.sort(key=lambda x: (-x[0], x[1].sort_text or x[1].label))
        
        return [completion for _, completion in scored_completions[:50]]

    def _resolve_object_path(self, obj_path: str) -> Optional[Any]:
        """Resolve object path to actual object."""
        if not self.autocad_wrapper:
            return None
        
        try:
            # Handle direct object references
            if obj_path == 'acad':
                return self.autocad_wrapper
            elif obj_path == 'app':
                return getattr(self.autocad_wrapper, 'app', None)
            elif obj_path == 'doc':
                return getattr(self.autocad_wrapper, 'doc', None)
            elif obj_path == 'model':
                return getattr(self.autocad_wrapper, 'model', None)
            
            # Handle chained references like 'acad.app'
            parts = obj_path.split('.')
            obj = self._resolve_object_path(parts[0])
            
            for part in parts[1:]:
                if obj is None:
                    return None
                obj = getattr(obj, part, None)
            
            return obj
            
        except Exception as e:
            logger.debug(f"Error resolving object path '{obj_path}': {str(e)}")
            return None

    def _find_method_call_context(self, document_text: str, position: Dict[str, int]) -> Optional[Tuple[str, str, int]]:
        """Find method call context for signature help."""
        try:
            lines = document_text.split('\n')
            line_no = position['line']
            char_no = position['character']
            
            if line_no >= len(lines):
                return None
            
            # Look backwards from cursor to find method call
            text_before_cursor = ""
            for i in range(line_no, -1, -1):
                line = lines[i]
                if i == line_no:
                    text_before_cursor = line[:char_no] + text_before_cursor
                else:
                    text_before_cursor = line + "\n" + text_before_cursor
                
                # Look for method call pattern
                pattern = r'(\w+(?:\.\w+)*)\s*\.\s*(\w+)\s*\(\s*([^)]*)'
                matches = list(re.finditer(pattern, text_before_cursor))
                
                if matches:
                    last_match = matches[-1]
                    obj_path = last_match.group(1)
                    method_name = last_match.group(2)
                    params_text = last_match.group(3)
                    
                    # Count parameters to determine active parameter
                    param_index = params_text.count(',')
                    
                    return obj_path, method_name, param_index
            
            return None
            
        except Exception as e:
            logger.debug(f"Error finding method call context: {str(e)}")
            return None

    def _get_member_hover_info(self, obj: Any, member_name: str) -> Optional[List[str]]:
        """Get hover information for object member."""
        try:
            # Try as property first
            try:
                prop_info = self.property_analyzer.analyze_property(obj, member_name)
                contents = [
                    f"**Property**: {prop_info.name}",
                    f"**Type**: {prop_info.data_type}",
                    f"**Access**: {prop_info.access_level.value}",
                    f"**Current Value**: {prop_info.current_value}"
                ]
                
                if prop_info.documentation and prop_info.documentation.description:
                    contents.append(f"**Description**: {prop_info.documentation.description}")
                
                return contents
                
            except:
                pass
            
            # Try as method
            try:
                method_info = self.method_discoverer.discover_method(obj, member_name)
                contents = [
                    f"**Method**: {method_info.name}",
                    f"**Signature**: `{method_info.signature}`",
                    f"**Type**: {method_info.method_type.value}"
                ]
                
                if method_info.documentation and method_info.documentation.description:
                    contents.append(f"**Description**: {method_info.documentation.description}")
                
                if method_info.documentation and method_info.documentation.usage_examples:
                    contents.append("**Examples**:")
                    for example in method_info.documentation.usage_examples[:2]:
                        contents.append(f"```python\n{example}\n```")
                
                return contents
                
            except:
                pass
            
            return None
            
        except Exception as e:
            logger.debug(f"Error getting member hover info: {str(e)}")
            return None

    def _get_symbol_hover_info(self, symbol: str, document_text: str) -> Optional[List[str]]:
        """Get hover information for top-level symbol."""
        # AutoCAD object documentation
        autocad_docs = {
            "acad": "AutoCAD wrapper instance providing access to AutoCAD COM interface",
            "app": "AutoCAD Application object - main entry point for application-level operations",
            "doc": "Active AutoCAD document - represents the current drawing",
            "model": "Model space object - container for drawing entities in model space"
        }
        
        if symbol in autocad_docs:
            return [f"**{symbol}**: {autocad_docs[symbol]}"]
        
        return None

    def _calculate_fuzzy_score(self, query: str, target: str) -> float:
        """Calculate fuzzy matching score."""
        if not query or not target:
            return 0
        
        # Simple fuzzy matching based on character overlap
        query_chars = set(query)
        target_chars = set(target)
        
        overlap = len(query_chars & target_chars)
        total_chars = len(query_chars | target_chars)
        
        return (overlap / total_chars) * 100 if total_chars > 0 else 0

    def _initialize_autocad_keywords(self) -> List[str]:
        """Initialize AutoCAD-related keywords."""
        return [
            # Python keywords
            "def", "class", "if", "else", "elif", "for", "while", "try", "except", "finally",
            "import", "from", "as", "with", "return", "yield", "lambda", "global", "nonlocal",
            
            # AutoCAD-specific
            "EnhancedAutoCAD", "Autocad", "Application", "Document", "ModelSpace",
            "AddLine", "AddCircle", "AddArc", "AddText", "AddDimension",
            
            # Common AutoCAD methods
            "GetEntity", "SelectAll", "Regen", "ZoomExtents", "Save", "Close"
        ]

    def _initialize_code_snippets(self) -> Dict[str, Dict[str, Any]]:
        """Initialize code snippets."""
        return {
            "autocad_connection": {
                "label": "AutoCAD Connection",
                "description": "Connect to AutoCAD with context manager",
                "triggers": ["with", "autocad", "connect"],
                "body": "with EnhancedAutoCAD() as acad:\n    ${1:# Your AutoCAD code here}\n    pass"
            },
            "draw_line": {
                "label": "Draw Line",
                "description": "Draw a line in AutoCAD",
                "triggers": ["line", "draw"],
                "body": "line = model.AddLine([${1:0}, ${2:0}, ${3:0}], [${4:100}, ${5:100}, ${6:0}])"
            },
            "draw_circle": {
                "label": "Draw Circle", 
                "description": "Draw a circle in AutoCAD",
                "triggers": ["circle", "draw"],
                "body": "circle = model.AddCircle([${1:0}, ${2:0}, ${3:0}], ${4:50})"
            },
            "error_handling": {
                "label": "Error Handling",
                "description": "AutoCAD error handling pattern",
                "triggers": ["try", "error", "exception"],
                "body": "try:\n    ${1:# AutoCAD operations}\n    pass\nexcept Exception as e:\n    print(f\"AutoCAD error: {e}\")"
            }
        }