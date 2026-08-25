"""
Security Sandbox for Interactive Development
===========================================

Enhanced security sandbox specifically designed for interactive REPL sessions.
Provides fine-grained security controls, session-based policies, and comprehensive
monitoring for safe interactive development with AutoCAD integration.
"""

import logging
import ast
import sys
import time
import threading
from typing import Dict, Any, List, Optional, Set, Callable
from dataclasses import dataclass
from enum import Enum
import re

# Import base security manager
from ..mcp_integration.security_manager import SecurityManager, SecurityError

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Security levels for different session types."""
    STRICT = "strict"        # Maximum security, minimal permissions
    NORMAL = "normal"        # Balanced security for general development
    RELAXED = "relaxed"      # Reduced restrictions for experienced developers
    TRUSTED = "trusted"      # Minimal restrictions for trusted code


@dataclass
class SecurityPolicy:
    """Security policy configuration for sessions."""
    level: SecurityLevel
    allow_file_operations: bool = False
    allow_network_operations: bool = False
    allow_system_calls: bool = False
    allow_imports: List[str] = None
    blocked_imports: List[str] = None
    allow_exec_eval: bool = False
    max_execution_time: float = 30.0
    max_memory_mb: float = 500.0
    max_output_length: int = 50000


class SecuritySandbox:
    """
    Advanced security sandbox for interactive development sessions.
    """

    def __init__(self, default_policy: Optional[SecurityPolicy] = None):
        """
        Initialize security sandbox.

        Args:
            default_policy: Default security policy (creates NORMAL if None)
        """
        self.base_security_manager = SecurityManager()
        self.session_policies = {}
        self.security_violations_log = []
        self.default_policy = default_policy or self._create_default_policy()
        
        # Session-specific violation tracking
        self.session_violations = {}
        
        # Advanced security patterns
        self.advanced_patterns = self._initialize_advanced_patterns()
        
        logger.info("Security Sandbox initialized with advanced policies")

    def create_session_policy(self, session_id: str, 
                            security_level: SecurityLevel = SecurityLevel.NORMAL,
                            custom_settings: Optional[Dict[str, Any]] = None) -> SecurityPolicy:
        """
        Create security policy for a specific session.

        Args:
            session_id: Session identifier
            security_level: Base security level
            custom_settings: Custom policy overrides

        Returns:
            Created security policy
        """
        # Start with level-based defaults
        policy = self._create_policy_for_level(security_level)
        
        # Apply custom settings
        if custom_settings:
            for key, value in custom_settings.items():
                if hasattr(policy, key):
                    setattr(policy, key, value)
        
        # Store policy for session
        self.session_policies[session_id] = policy
        self.session_violations[session_id] = []
        
        logger.info(f"Security policy created for session {session_id}: {security_level.value}")
        
        return policy

    def validate_session_code(self, code: str, session_id: str) -> tuple[bool, List[str]]:
        """
        Validate code against session-specific security policy.

        Args:
            code: Python code to validate
            session_id: Session identifier

        Returns:
            Tuple of (is_valid, violations_list)
        """
        policy = self.session_policies.get(session_id, self.default_policy)
        violations = []

        try:
            # Base validation using SecurityManager
            base_valid, base_violations = self.base_security_manager.validate_python_code(code)
            if not base_valid:
                violations.extend(base_violations)

            # Advanced policy-specific validation
            policy_violations = self._validate_against_policy(code, policy)
            violations.extend(policy_violations)

            # Session-specific pattern checking
            pattern_violations = self._check_advanced_patterns(code, policy)
            violations.extend(pattern_violations)

            # Log violations for this session
            if violations:
                self.session_violations[session_id].extend([
                    {
                        "timestamp": time.time(),
                        "code_snippet": code[:100] + "..." if len(code) > 100 else code,
                        "violation": violation
                    }
                    for violation in violations
                ])

            is_valid = len(violations) == 0
            
            if not is_valid:
                logger.warning(f"Security violations in session {session_id}: {violations}")
            
            return is_valid, violations

        except Exception as e:
            error_msg = f"Security validation error: {str(e)}"
            logger.error(error_msg)
            return False, [error_msg]

    def execute_with_sandbox(self, code: str, context: Dict[str, Any], 
                           session_id: str) -> tuple[bool, Any, str]:
        """
        Execute code within session sandbox with policy enforcement.

        Args:
            code: Python code to execute
            context: Execution context
            session_id: Session identifier

        Returns:
            Tuple of (success, result, error_message)
        """
        policy = self.session_policies.get(session_id, self.default_policy)
        
        # Validate code first
        is_valid, violations = self.validate_session_code(code, session_id)
        if not is_valid:
            return False, None, f"Security violations: {'; '.join(violations)}"

        try:
            # Create sandboxed context based on policy
            sandboxed_context = self._create_sandboxed_context(context, policy)
            
            # Execute with policy-specific timeout
            success, result, error_msg = self.base_security_manager.execute_with_timeout(
                code, sandboxed_context, policy.max_execution_time
            )
            
            # Validate output length
            if success and result is not None:
                result_str = str(result)
                if len(result_str) > policy.max_output_length:
                    return False, None, f"Output too long: {len(result_str)} > {policy.max_output_length}"
            
            return success, result, error_msg

        except Exception as e:
            error_msg = f"Sandbox execution error: {str(e)}"
            logger.error(f"Sandbox execution failed for session {session_id}: {error_msg}")
            return False, None, error_msg

    def get_session_security_status(self, session_id: str) -> Dict[str, Any]:
        """Get security status for a session."""
        policy = self.session_policies.get(session_id)
        violations = self.session_violations.get(session_id, [])
        
        if not policy:
            return {
                "has_policy": False,
                "security_level": "unknown",
                "total_violations": 0
            }

        return {
            "has_policy": True,
            "security_level": policy.level.value,
            "total_violations": len(violations),
            "recent_violations": violations[-10:] if violations else [],
            "policy_settings": {
                "allow_file_operations": policy.allow_file_operations,
                "allow_network_operations": policy.allow_network_operations,
                "allow_system_calls": policy.allow_system_calls,
                "max_execution_time": policy.max_execution_time,
                "max_memory_mb": policy.max_memory_mb
            }
        }

    def update_session_policy(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Update security policy for a session."""
        if session_id not in self.session_policies:
            return False

        policy = self.session_policies[session_id]
        
        for key, value in updates.items():
            if hasattr(policy, key):
                setattr(policy, key, value)
                logger.info(f"Updated policy {key} for session {session_id}: {value}")
        
        return True

    def cleanup_session(self, session_id: str):
        """Clean up security data for a session."""
        if session_id in self.session_policies:
            del self.session_policies[session_id]
        
        if session_id in self.session_violations:
            del self.session_violations[session_id]
        
        logger.info(f"Security data cleaned up for session {session_id}")

    def get_security_report(self) -> Dict[str, Any]:
        """Get comprehensive security report."""
        total_sessions = len(self.session_policies)
        total_violations = sum(len(violations) for violations in self.session_violations.values())
        
        # Security level distribution
        level_distribution = {}
        for policy in self.session_policies.values():
            level = policy.level.value
            level_distribution[level] = level_distribution.get(level, 0) + 1

        # Most common violations
        all_violations = []
        for violations in self.session_violations.values():
            all_violations.extend([v["violation"] for v in violations])
        
        violation_counts = {}
        for violation in all_violations:
            violation_counts[violation] = violation_counts.get(violation, 0) + 1
        
        common_violations = sorted(violation_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "total_sessions": total_sessions,
            "total_violations": total_violations,
            "security_level_distribution": level_distribution,
            "most_common_violations": common_violations,
            "default_security_level": self.default_policy.level.value,
            "advanced_patterns_enabled": True
        }

    def _create_default_policy(self) -> SecurityPolicy:
        """Create default security policy."""
        return SecurityPolicy(
            level=SecurityLevel.NORMAL,
            allow_file_operations=False,
            allow_network_operations=False,
            allow_system_calls=False,
            allow_imports=["math", "random", "datetime", "json", "re"],
            blocked_imports=["os", "sys", "subprocess", "socket"],
            allow_exec_eval=False,
            max_execution_time=30.0,
            max_memory_mb=500.0,
            max_output_length=50000
        )

    def _create_policy_for_level(self, level: SecurityLevel) -> SecurityPolicy:
        """Create policy based on security level."""
        base_policy = self._create_default_policy()
        base_policy.level = level

        if level == SecurityLevel.STRICT:
            base_policy.allow_imports = ["math"]
            base_policy.max_execution_time = 10.0
            base_policy.max_memory_mb = 100.0
            base_policy.max_output_length = 10000

        elif level == SecurityLevel.RELAXED:
            base_policy.allow_imports.extend(["urllib", "requests", "pathlib"])
            base_policy.max_execution_time = 60.0
            base_policy.max_memory_mb = 1000.0

        elif level == SecurityLevel.TRUSTED:
            base_policy.allow_file_operations = True
            base_policy.allow_imports.extend(["os", "pathlib", "shutil"])
            base_policy.blocked_imports = ["subprocess", "socket"]
            base_policy.max_execution_time = 120.0
            base_policy.max_memory_mb = 2000.0

        return base_policy

    def _validate_against_policy(self, code: str, policy: SecurityPolicy) -> List[str]:
        """Validate code against specific policy."""
        violations = []

        # Check imports against policy
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if not self._is_import_allowed(alias.name, policy):
                            violations.append(f"Import not allowed: {alias.name}")
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module and not self._is_import_allowed(node.module, policy):
                        violations.append(f"Import from not allowed: {node.module}")

        except SyntaxError:
            # Syntax errors will be caught by base validation
            pass

        # Check for policy-specific patterns
        if not policy.allow_exec_eval:
            if re.search(r'\b(exec|eval)\s*\(', code, re.IGNORECASE):
                violations.append("exec/eval not allowed by policy")

        if not policy.allow_file_operations:
            file_patterns = [r'\bopen\s*\(', r'\bfile\s*\(', r'\.write\s*\(', r'\.read\s*\(']
            for pattern in file_patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    violations.append("File operations not allowed by policy")

        return violations

    def _check_advanced_patterns(self, code: str, policy: SecurityPolicy) -> List[str]:
        """Check for advanced security patterns."""
        violations = []

        for pattern_name, pattern_info in self.advanced_patterns.items():
            if re.search(pattern_info["pattern"], code, re.IGNORECASE):
                # Check if this pattern is allowed by policy
                if not pattern_info.get("allowed_levels", []):
                    violations.append(f"Advanced pattern detected: {pattern_name}")
                elif policy.level not in pattern_info["allowed_levels"]:
                    violations.append(f"Pattern '{pattern_name}' not allowed at {policy.level.value} level")

        return violations

    def _initialize_advanced_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize advanced security patterns."""
        return {
            "memory_manipulation": {
                "pattern": r"\b(gc\.|ctypes\.|memoryview)",
                "allowed_levels": [SecurityLevel.TRUSTED],
                "description": "Memory manipulation operations"
            },
            "reflection_abuse": {
                "pattern": r"\b(__dict__|__class__|__bases__|getattr\s*\(\s*\w+\s*,\s*['\"]__)",
                "allowed_levels": [SecurityLevel.RELAXED, SecurityLevel.TRUSTED],
                "description": "Reflection and introspection abuse"
            },
            "code_generation": {
                "pattern": r"\b(compile\s*\(|types\.CodeType|ast\.parse)",
                "allowed_levels": [SecurityLevel.TRUSTED],
                "description": "Dynamic code generation"
            },
            "threading_operations": {
                "pattern": r"\b(threading\.|Thread\(|multiprocessing\.)",
                "allowed_levels": [SecurityLevel.RELAXED, SecurityLevel.TRUSTED],
                "description": "Threading and multiprocessing operations"
            }
        }

    def _is_import_allowed(self, module_name: str, policy: SecurityPolicy) -> bool:
        """Check if import is allowed by policy."""
        # Check blocked imports first
        if policy.blocked_imports and module_name in policy.blocked_imports:
            return False
        
        # Check allowed imports
        if policy.allow_imports:
            # Allow if module is in allowed list or is a submodule of allowed
            for allowed in policy.allow_imports:
                if module_name == allowed or module_name.startswith(allowed + "."):
                    return True
            return False
        
        # If no allow list specified, allow everything not in blocked list
        return True

    def _create_sandboxed_context(self, base_context: Dict[str, Any], 
                                policy: SecurityPolicy) -> Dict[str, Any]:
        """Create sandboxed execution context based on policy."""
        # Start with safe builtins from base security manager
        sandboxed_context = self.base_security_manager.create_safe_globals()
        
        # Add base context (AutoCAD objects, etc.)
        sandboxed_context.update(base_context)
        
        # Apply policy-specific restrictions
        if not policy.allow_file_operations:
            # Remove file-related functions that might have been added
            restricted_functions = ["open", "file"]
            for func in restricted_functions:
                sandboxed_context.pop(func, None)
        
        return sandboxed_context