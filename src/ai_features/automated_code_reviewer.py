"""
Automated Code Review System with Quality Scoring
===============================================

Intelligent code review engine with comprehensive quality analysis including:
- Multi-dimensional code quality scoring and metrics
- AutoCAD-specific best practices and pattern recognition
- Automated suggestions for improvements and optimizations
- Security vulnerability detection and compliance checking
- Code style analysis with configurable standards
"""

import logging
import time
import ast
import re
import json
from typing import Dict, Any, List, Optional, Set, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from collections import defaultdict, Counter
import inspect

# Import existing analysis components
from ..interactive.code_refactoring import CodeRefactoringEngine, RefactoringSuggestion
from .error_prediction_engine import IntelligentErrorPredictor

logger = logging.getLogger(__name__)


class ReviewSeverity(Enum):
    """Severity levels for code review findings."""
    INFO = "info"           # Informational, no action required
    MINOR = "minor"         # Minor improvements suggested
    MAJOR = "major"         # Important issues that should be addressed
    CRITICAL = "critical"   # Critical issues that must be fixed
    BLOCKER = "blocker"     # Blocking issues that prevent deployment


class ReviewCategory(Enum):
    """Categories of code review findings."""
    STYLE = "style"                    # Code style and formatting
    PERFORMANCE = "performance"        # Performance issues and optimizations
    SECURITY = "security"              # Security vulnerabilities
    MAINTAINABILITY = "maintainability"  # Code maintainability issues
    RELIABILITY = "reliability"        # Bug risks and error handling
    AUTOCAD_BEST_PRACTICES = "autocad_best_practices"  # AutoCAD-specific issues
    DOCUMENTATION = "documentation"    # Documentation and comments
    COMPLEXITY = "complexity"          # Code complexity issues
    TESTING = "testing"               # Testing-related issues
    ARCHITECTURE = "architecture"     # Architecture and design issues


@dataclass
class ReviewFinding:
    """A single code review finding with details and suggestions."""
    id: str
    category: ReviewCategory
    severity: ReviewSeverity
    title: str
    description: str
    
    # Location information
    file_path: str
    line_number: int
    column_number: int = 0
    end_line: Optional[int] = None
    
    # Code context
    code_snippet: str = ""
    suggested_fix: Optional[str] = None
    
    # Scoring impact
    quality_impact: float = 0.0  # Impact on overall quality score (-1.0 to 1.0)
    
    # Additional metadata
    rule_id: Optional[str] = None
    references: List[str] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    
    # AutoCAD-specific
    autocad_version_impact: Optional[str] = None
    performance_impact: Optional[str] = None


@dataclass
class QualityMetrics:
    """Comprehensive code quality metrics."""
    overall_score: float  # 0.0 to 10.0
    
    # Individual metric scores
    style_score: float = 0.0
    performance_score: float = 0.0
    security_score: float = 0.0
    maintainability_score: float = 0.0
    reliability_score: float = 0.0
    documentation_score: float = 0.0
    complexity_score: float = 0.0
    
    # AutoCAD-specific scores
    autocad_best_practices_score: float = 0.0
    com_error_handling_score: float = 0.0
    transaction_usage_score: float = 0.0
    
    # Quantitative metrics
    lines_of_code: int = 0
    cyclomatic_complexity: int = 0
    code_duplication_percentage: float = 0.0
    test_coverage_percentage: float = 0.0
    comment_density: float = 0.0
    
    # Trend analysis
    quality_trend: Optional[str] = None  # 'improving', 'declining', 'stable'
    previous_score: Optional[float] = None


@dataclass
class CodeReviewReport:
    """Comprehensive code review report."""
    review_id: str
    timestamp: float
    file_path: str
    
    # Quality assessment
    quality_metrics: QualityMetrics
    findings: List[ReviewFinding] = field(default_factory=list)
    
    # Summary statistics
    total_findings: int = 0
    findings_by_severity: Dict[str, int] = field(default_factory=dict)
    findings_by_category: Dict[str, int] = field(default_factory=dict)
    
    # Recommendations
    priority_fixes: List[ReviewFinding] = field(default_factory=list)
    suggested_refactorings: List[RefactoringSuggestion] = field(default_factory=list)
    
    # Review metadata
    review_duration: float = 0.0
    reviewer_confidence: float = 0.0
    automated_fix_suggestions: int = 0
    
    # Comparison with standards
    compliance_score: Dict[str, float] = field(default_factory=dict)
    best_practices_adherence: float = 0.0


class CodeReviewRule:
    """Represents a single code review rule."""
    
    def __init__(self, rule_id: str, category: ReviewCategory, severity: ReviewSeverity):
        self.rule_id = rule_id
        self.category = category
        self.severity = severity
        self.name = ""
        self.description = ""
        self.pattern = None  # Can be regex, AST pattern, or callable
        self.message_template = ""
        self.suggested_fix_template = ""
        self.references = []
        self.enabled = True
        self.quality_impact = 0.0
    
    def check(self, code: str, ast_tree: Optional[ast.AST] = None, context: Optional[Dict[str, Any]] = None) -> List[ReviewFinding]:
        """Check if this rule applies to the given code."""
        findings = []
        
        if not self.enabled:
            return findings
        
        try:
            if callable(self.pattern):
                # Custom function-based rule
                results = self.pattern(code, ast_tree, context)
                for result in results:
                    finding = self._create_finding_from_result(result)
                    findings.append(finding)
            
            elif isinstance(self.pattern, str):
                # Regex-based rule
                matches = re.finditer(self.pattern, code, re.MULTILINE)
                for match in matches:
                    line_number = code[:match.start()].count('\n') + 1
                    finding = self._create_finding_from_match(match, line_number, code)
                    findings.append(finding)
            
            elif hasattr(self.pattern, 'visit') and ast_tree:
                # AST visitor-based rule
                visitor = self.pattern()
                visitor.visit(ast_tree)
                for result in visitor.findings:
                    finding = self._create_finding_from_ast_result(result)
                    findings.append(finding)
        
        except Exception as e:
            logger.error(f"Rule {self.rule_id} check failed: {e}")
        
        return findings
    
    def _create_finding_from_result(self, result: Dict[str, Any]) -> ReviewFinding:
        """Create a ReviewFinding from a custom rule result."""
        return ReviewFinding(
            id=f"{self.rule_id}_{int(time.time() * 1000) % 1000000:06d}",
            category=self.category,
            severity=self.severity,
            title=self.name,
            description=result.get('message', self.description),
            file_path=result.get('file_path', ''),
            line_number=result.get('line_number', 0),
            code_snippet=result.get('code_snippet', ''),
            suggested_fix=result.get('suggested_fix'),
            quality_impact=self.quality_impact,
            rule_id=self.rule_id,
            references=self.references.copy()
        )
    
    def _create_finding_from_match(self, match: re.Match, line_number: int, code: str) -> ReviewFinding:
        """Create a ReviewFinding from a regex match."""
        lines = code.split('\n')
        code_snippet = lines[line_number - 1] if line_number <= len(lines) else ""
        
        return ReviewFinding(
            id=f"{self.rule_id}_{line_number}_{int(time.time() * 1000) % 1000:06d}",
            category=self.category,
            severity=self.severity,
            title=self.name,
            description=self.message_template.format(match=match.group()),
            file_path='',
            line_number=line_number,
            code_snippet=code_snippet,
            quality_impact=self.quality_impact,
            rule_id=self.rule_id,
            references=self.references.copy()
        )
    
    def _create_finding_from_ast_result(self, result: Dict[str, Any]) -> ReviewFinding:
        """Create a ReviewFinding from an AST visitor result."""
        return ReviewFinding(
            id=f"{self.rule_id}_{result.get('line', 0)}_{int(time.time() * 1000) % 1000000:06d}",
            category=self.category,
            severity=self.severity,
            title=self.name,
            description=result.get('message', self.description),
            file_path='',
            line_number=result.get('line', 0),
            code_snippet=result.get('code_snippet', ''),
            quality_impact=self.quality_impact,
            rule_id=self.rule_id,
            references=self.references.copy()
        )


class AutoCADASTVisitor(ast.NodeVisitor):
    """AST visitor for AutoCAD-specific code analysis."""
    
    def __init__(self):
        self.findings = []
        self.autocad_objects = set()
        self.com_calls = []
        self.transaction_usage = False
        self.error_handling_coverage = 0
        self.total_com_calls = 0
    
    def visit_Call(self, node):
        """Analyze function calls for AutoCAD patterns."""
        call_name = self._get_call_name(node)
        
        # Track AutoCAD COM calls
        if self._is_autocad_call(call_name):
            self.total_com_calls += 1
            self.com_calls.append({
                'name': call_name,
                'line': node.lineno,
                'in_try_block': self._is_in_try_block(node)
            })
            
            # Check for transaction usage
            if 'Transaction' in call_name:
                self.transaction_usage = True
        
        self.generic_visit(node)
    
    def visit_Try(self, node):
        """Analyze error handling patterns."""
        # Check if try block contains COM calls
        com_calls_in_try = 0
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_name = self._get_call_name(child)
                if self._is_autocad_call(call_name):
                    com_calls_in_try += 1
        
        if com_calls_in_try > 0:
            self.error_handling_coverage += com_calls_in_try
        
        self.generic_visit(node)
    
    def _get_call_name(self, node: ast.Call) -> str:
        """Get the name of a function call."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return self._get_attribute_chain(node.func)
        return ""
    
    def _get_attribute_chain(self, node: ast.Attribute) -> str:
        """Get the full attribute chain."""
        parts = []
        current = node
        
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        
        if isinstance(current, ast.Name):
            parts.append(current.id)
        
        return '.'.join(reversed(parts))
    
    def _is_autocad_call(self, call_name: str) -> bool:
        """Check if a call is AutoCAD-related."""
        autocad_indicators = [
            'Application', 'ActiveDocument', 'ModelSpace', 'PaperSpace',
            'Add', 'Insert', 'Create', 'Select', 'Block', 'Layer'
        ]
        return any(indicator in call_name for indicator in autocad_indicators)
    
    def _is_in_try_block(self, node: ast.AST) -> bool:
        """Check if a node is within a try block."""
        # This would require maintaining parent references
        # Simplified implementation
        return False


class AutomatedCodeReviewer:
    """
    Automated code review system with comprehensive quality analysis.
    
    Provides intelligent code review with AutoCAD-specific insights,
    quality scoring, and actionable improvement suggestions.
    """
    
    def __init__(self):
        """Initialize the automated code reviewer."""
        self.refactoring_engine = CodeRefactoringEngine()
        self.error_predictor = IntelligentErrorPredictor()
        
        # Review rules and standards
        self.review_rules = self._initialize_review_rules()
        self.quality_standards = self._load_quality_standards()
        self.autocad_best_practices = self._load_autocad_best_practices()
        
        # Historical data for trend analysis
        self.review_history = []
        self.quality_baselines = {}
        
        # Configuration
        self.enable_automated_fixes = True
        self.max_suggestions_per_category = 10
        self.quality_score_weights = self._initialize_score_weights()
        
        logger.info("Automated code reviewer initialized")
    
    def review_code(self, 
                   code: str,
                   file_path: str,
                   context: Optional[Dict[str, Any]] = None) -> CodeReviewReport:
        """
        Perform comprehensive automated code review.
        
        Args:
            code: Source code to review
            file_path: Path to the source file
            context: Additional context information
            
        Returns:
            Comprehensive code review report
        """
        start_time = time.time()
        review_id = f"review_{int(time.time() * 1000) % 1000000:06d}"
        
        report = CodeReviewReport(
            review_id=review_id,
            timestamp=time.time(),
            file_path=file_path
        )
        
        try:
            # Parse the code
            ast_tree = None
            try:
                ast_tree = ast.parse(code)
            except SyntaxError as e:
                # Add syntax error finding
                syntax_finding = ReviewFinding(
                    id=f"syntax_error_{int(time.time() * 1000) % 1000:06d}",
                    category=ReviewCategory.RELIABILITY,
                    severity=ReviewSeverity.BLOCKER,
                    title="Syntax Error",
                    description=f"Syntax error: {e}",
                    file_path=file_path,
                    line_number=getattr(e, 'lineno', 0),
                    quality_impact=-2.0
                )
                report.findings.append(syntax_finding)
                return report
            
            # Run all review rules
            all_findings = []
            for rule in self.review_rules:
                rule_findings = rule.check(code, ast_tree, context)
                for finding in rule_findings:
                    finding.file_path = file_path
                all_findings.extend(rule_findings)
            
            # Perform specialized analyses
            autocad_findings = self._analyze_autocad_patterns(code, ast_tree)
            all_findings.extend(autocad_findings)
            
            performance_findings = self._analyze_performance_patterns(code, ast_tree)
            all_findings.extend(performance_findings)
            
            security_findings = self._analyze_security_patterns(code, ast_tree)
            all_findings.extend(security_findings)
            
            # Calculate quality metrics
            quality_metrics = self._calculate_quality_metrics(code, ast_tree, all_findings)
            report.quality_metrics = quality_metrics
            
            # Process and rank findings
            report.findings = self._process_and_rank_findings(all_findings)
            
            # Generate summary statistics
            self._generate_summary_statistics(report)
            
            # Get refactoring suggestions
            if self.refactoring_engine:
                refactoring_suggestions = self.refactoring_engine.generate_refactoring_suggestions(file_path)
                report.suggested_refactorings = refactoring_suggestions[:5]  # Top 5 suggestions
            
            # Identify priority fixes
            report.priority_fixes = [
                f for f in report.findings 
                if f.severity in [ReviewSeverity.CRITICAL, ReviewSeverity.BLOCKER]
            ][:10]
            
            # Calculate compliance scores
            report.compliance_score = self._calculate_compliance_scores(report.findings)
            report.best_practices_adherence = self._calculate_best_practices_adherence(ast_tree)
            
            # Set review metadata
            report.review_duration = time.time() - start_time
            report.reviewer_confidence = self._calculate_reviewer_confidence(report)
            report.automated_fix_suggestions = sum(
                1 for f in report.findings if f.suggested_fix is not None
            )
            
            # Store in history for trend analysis
            self.review_history.append(report)
            if len(self.review_history) > 100:
                self.review_history = self.review_history[-50:]
            
        except Exception as e:
            logger.error(f"Code review failed: {e}")
            # Create error report
            error_finding = ReviewFinding(
                id=f"review_error_{int(time.time() * 1000) % 1000:06d}",
                category=ReviewCategory.RELIABILITY,
                severity=ReviewSeverity.CRITICAL,
                title="Review Engine Error",
                description=f"Code review failed: {e}",
                file_path=file_path,
                line_number=0,
                quality_impact=-1.0
            )
            report.findings = [error_finding]
            report.quality_metrics = QualityMetrics(overall_score=0.0)
        
        return report
    
    def review_multiple_files(self, file_paths: List[str]) -> Dict[str, CodeReviewReport]:
        """
        Review multiple files and provide aggregated insights.
        
        Args:
            file_paths: List of file paths to review
            
        Returns:
            Dictionary mapping file paths to review reports
        """
        reports = {}
        
        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                report = self.review_code(code, file_path)
                reports[file_path] = report
                
            except Exception as e:
                logger.error(f"Failed to review {file_path}: {e}")
                # Create error report
                error_report = CodeReviewReport(
                    review_id=f"error_{int(time.time() * 1000) % 1000:06d}",
                    timestamp=time.time(),
                    file_path=file_path,
                    quality_metrics=QualityMetrics(overall_score=0.0)
                )
                reports[file_path] = error_report
        
        return reports
    
    def get_quality_trend_analysis(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze quality trends for a specific file.
        
        Args:
            file_path: Path to analyze trends for
            
        Returns:
            Trend analysis report
        """
        file_history = [
            report for report in self.review_history
            if report.file_path == file_path
        ]
        
        if len(file_history) < 2:
            return {'error': 'Insufficient history for trend analysis'}
        
        # Sort by timestamp
        file_history.sort(key=lambda r: r.timestamp)
        
        # Calculate trends
        quality_scores = [r.quality_metrics.overall_score for r in file_history]
        
        trend_analysis = {
            'file_path': file_path,
            'review_count': len(file_history),
            'time_span_days': (file_history[-1].timestamp - file_history[0].timestamp) / 86400,
            'quality_trend': self._calculate_trend(quality_scores),
            'average_quality': sum(quality_scores) / len(quality_scores),
            'latest_quality': quality_scores[-1],
            'quality_improvement': quality_scores[-1] - quality_scores[0],
            'findings_trend': self._analyze_findings_trend(file_history),
            'recommendations': []
        }
        
        # Generate recommendations based on trends
        if trend_analysis['quality_improvement'] < -1.0:
            trend_analysis['recommendations'].append("Quality is declining - consider code refactoring")
        elif trend_analysis['quality_improvement'] > 1.0:
            trend_analysis['recommendations'].append("Quality is improving - maintain current practices")
        
        return trend_analysis
    
    def generate_team_quality_report(self, reports: Dict[str, CodeReviewReport]) -> Dict[str, Any]:
        """
        Generate team-wide quality report from multiple file reviews.
        
        Args:
            reports: Dictionary of file path to review reports
            
        Returns:
            Team quality report
        """
        if not reports:
            return {'error': 'No reports provided'}
        
        # Aggregate metrics
        total_files = len(reports)
        valid_reports = [r for r in reports.values() if r.quality_metrics.overall_score > 0]
        
        if not valid_reports:
            return {'error': 'No valid reports found'}
        
        team_report = {
            'timestamp': time.time(),
            'total_files_reviewed': total_files,
            'valid_reports': len(valid_reports),
            'overall_metrics': {
                'average_quality_score': sum(r.quality_metrics.overall_score for r in valid_reports) / len(valid_reports),
                'total_findings': sum(len(r.findings) for r in valid_reports),
                'critical_issues': sum(len(r.priority_fixes) for r in valid_reports),
                'total_lines_of_code': sum(r.quality_metrics.lines_of_code for r in valid_reports)
            },
            'category_breakdown': self._aggregate_category_breakdown(valid_reports),
            'severity_breakdown': self._aggregate_severity_breakdown(valid_reports),
            'top_issues': self._identify_top_issues(valid_reports),
            'quality_distribution': self._calculate_quality_distribution(valid_reports),
            'recommendations': []
        }
        
        # Generate team recommendations
        avg_quality = team_report['overall_metrics']['average_quality_score']
        if avg_quality < 5.0:
            team_report['recommendations'].append("Overall code quality is below acceptable standards")
        elif avg_quality > 8.0:
            team_report['recommendations'].append("Excellent code quality maintained across the team")
        
        critical_ratio = team_report['overall_metrics']['critical_issues'] / max(total_files, 1)
        if critical_ratio > 0.5:
            team_report['recommendations'].append("High number of critical issues - prioritize immediate fixes")
        
        return team_report
    
    def _initialize_review_rules(self) -> List[CodeReviewRule]:
        """Initialize built-in code review rules."""
        rules = []
        
        # Style rules
        long_line_rule = CodeReviewRule("long_lines", ReviewCategory.STYLE, ReviewSeverity.MINOR)
        long_line_rule.name = "Long Lines"
        long_line_rule.description = "Lines should not exceed 120 characters"
        long_line_rule.pattern = r'^.{121,}$'
        long_line_rule.quality_impact = -0.1
        rules.append(long_line_rule)
        
        # Performance rules
        string_concat_rule = CodeReviewRule("string_concatenation", ReviewCategory.PERFORMANCE, ReviewSeverity.MINOR)
        string_concat_rule.name = "Inefficient String Concatenation"
        string_concat_rule.description = "Use join() instead of += for string concatenation in loops"
        string_concat_rule.pattern = r'\s*\w+\s*\+=\s*["\'].*["\']'
        string_concat_rule.quality_impact = -0.2
        rules.append(string_concat_rule)
        
        # Security rules
        eval_usage_rule = CodeReviewRule("eval_usage", ReviewCategory.SECURITY, ReviewSeverity.CRITICAL)
        eval_usage_rule.name = "Dangerous eval() Usage"
        eval_usage_rule.description = "Using eval() can be dangerous - consider safer alternatives"
        eval_usage_rule.pattern = r'\beval\s*\('
        eval_usage_rule.quality_impact = -1.0
        rules.append(eval_usage_rule)
        
        # AutoCAD-specific rules
        com_error_rule = CodeReviewRule("missing_com_error_handling", ReviewCategory.AUTOCAD_BEST_PRACTICES, ReviewSeverity.MAJOR)
        com_error_rule.name = "Missing COM Error Handling"
        com_error_rule.description = "AutoCAD COM operations should be wrapped in try-except blocks"
        com_error_rule.pattern = self._create_com_error_checker()
        com_error_rule.quality_impact = -0.5
        rules.append(com_error_rule)
        
        return rules
    
    def _create_com_error_checker(self) -> Callable:
        """Create a checker function for COM error handling."""
        def check_com_errors(code: str, ast_tree: Optional[ast.AST], context: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
            findings = []
            
            if not ast_tree:
                return findings
            
            visitor = AutoCADASTVisitor()
            visitor.visit(ast_tree)
            
            # Check if COM calls have adequate error handling
            unprotected_calls = [
                call for call in visitor.com_calls
                if not call['in_try_block']
            ]
            
            for call in unprotected_calls:
                findings.append({
                    'line_number': call['line'],
                    'message': f"COM call '{call['name']}' should be wrapped in try-except block",
                    'code_snippet': f"# Line {call['line']}: {call['name']}",
                    'suggested_fix': f"try:\n    {call['name']}\nexcept Exception as e:\n    # Handle COM error\n    pass"
                })
            
            return findings
        
        return check_com_errors
    
    def _analyze_autocad_patterns(self, code: str, ast_tree: ast.AST) -> List[ReviewFinding]:
        """Analyze AutoCAD-specific code patterns."""
        findings = []
        
        try:
            visitor = AutoCADASTVisitor()
            visitor.visit(ast_tree)
            
            # Check transaction usage
            if visitor.total_com_calls > 5 and not visitor.transaction_usage:
                findings.append(ReviewFinding(
                    id=f"no_transactions_{int(time.time() * 1000) % 1000:06d}",
                    category=ReviewCategory.AUTOCAD_BEST_PRACTICES,
                    severity=ReviewSeverity.MAJOR,
                    title="Missing Transaction Usage",
                    description=f"Found {visitor.total_com_calls} COM calls without transaction management",
                    file_path="",
                    line_number=1,
                    quality_impact=-0.3,
                    suggested_fix="Wrap multiple AutoCAD operations in StartTransaction/CommitTransaction blocks"
                ))
            
            # Check error handling coverage
            if visitor.total_com_calls > 0:
                coverage_ratio = visitor.error_handling_coverage / visitor.total_com_calls
                if coverage_ratio < 0.5:
                    findings.append(ReviewFinding(
                        id=f"low_error_coverage_{int(time.time() * 1000) % 1000:06d}",
                        category=ReviewCategory.RELIABILITY,
                        severity=ReviewSeverity.MAJOR,
                        title="Low Error Handling Coverage",
                        description=f"Only {coverage_ratio:.1%} of COM calls are protected by error handling",
                        file_path="",
                        line_number=1,
                        quality_impact=-0.4,
                        suggested_fix="Add try-except blocks around AutoCAD COM operations"
                    ))
        
        except Exception as e:
            logger.error(f"AutoCAD pattern analysis failed: {e}")
        
        return findings
    
    def _analyze_performance_patterns(self, code: str, ast_tree: ast.AST) -> List[ReviewFinding]:
        """Analyze performance-related patterns."""
        findings = []
        
        try:
            # Check for inefficient patterns
            if 'for ' in code and ' in range(' in code and '+=' in code:
                findings.append(ReviewFinding(
                    id=f"inefficient_loop_{int(time.time() * 1000) % 1000:06d}",
                    category=ReviewCategory.PERFORMANCE,
                    severity=ReviewSeverity.MINOR,
                    title="Potentially Inefficient Loop",
                    description="Consider using list comprehensions or vectorized operations",
                    file_path="",
                    line_number=1,
                    quality_impact=-0.1
                ))
            
            # Check for repeated expensive operations
            expensive_ops = ['ModelSpace', 'PaperSpace', 'ActiveDocument']
            for op in expensive_ops:
                count = code.count(op)
                if count > 3:
                    findings.append(ReviewFinding(
                        id=f"repeated_expensive_op_{op}_{int(time.time() * 1000) % 1000:06d}",
                        category=ReviewCategory.PERFORMANCE,
                        severity=ReviewSeverity.MINOR,
                        title=f"Repeated Expensive Operation: {op}",
                        description=f"'{op}' is called {count} times - consider caching the reference",
                        file_path="",
                        line_number=1,
                        quality_impact=-0.2,
                        suggested_fix=f"Cache {op} reference at the beginning: {op.lower()} = doc.{op}"
                    ))
        
        except Exception as e:
            logger.error(f"Performance pattern analysis failed: {e}")
        
        return findings
    
    def _analyze_security_patterns(self, code: str, ast_tree: ast.AST) -> List[ReviewFinding]:
        """Analyze security-related patterns."""
        findings = []
        
        try:
            # Check for dangerous functions
            dangerous_functions = ['eval', 'exec', 'compile']
            for func in dangerous_functions:
                if f'{func}(' in code:
                    findings.append(ReviewFinding(
                        id=f"dangerous_function_{func}_{int(time.time() * 1000) % 1000:06d}",
                        category=ReviewCategory.SECURITY,
                        severity=ReviewSeverity.CRITICAL,
                        title=f"Dangerous Function: {func}()",
                        description=f"Using {func}() can be dangerous and should be avoided",
                        file_path="",
                        line_number=1,
                        quality_impact=-1.0
                    ))
            
            # Check for hardcoded passwords or keys
            password_patterns = [
                r'password\s*=\s*["\'][^"\']+["\']',
                r'key\s*=\s*["\'][^"\']+["\']',
                r'secret\s*=\s*["\'][^"\']+["\']'
            ]
            
            for pattern in password_patterns:
                matches = re.finditer(pattern, code, re.IGNORECASE)
                for match in matches:
                    line_number = code[:match.start()].count('\n') + 1
                    findings.append(ReviewFinding(
                        id=f"hardcoded_secret_{line_number}_{int(time.time() * 1000) % 1000:06d}",
                        category=ReviewCategory.SECURITY,
                        severity=ReviewSeverity.MAJOR,
                        title="Hardcoded Secret",
                        description="Secrets should not be hardcoded in source code",
                        file_path="",
                        line_number=line_number,
                        quality_impact=-0.6,
                        suggested_fix="Use environment variables or secure configuration files"
                    ))
        
        except Exception as e:
            logger.error(f"Security pattern analysis failed: {e}")
        
        return findings
    
    def _calculate_quality_metrics(self, 
                                 code: str, 
                                 ast_tree: ast.AST, 
                                 findings: List[ReviewFinding]) -> QualityMetrics:
        """Calculate comprehensive quality metrics."""
        metrics = QualityMetrics(overall_score=10.0)  # Start with perfect score
        
        try:
            # Basic code metrics
            lines = code.split('\n')
            metrics.lines_of_code = len([line for line in lines if line.strip()])
            
            # Calculate comment density
            comment_lines = len([line for line in lines if line.strip().startswith('#')])
            metrics.comment_density = comment_lines / max(metrics.lines_of_code, 1)
            
            # Calculate cyclomatic complexity
            complexity_calculator = CyclomaticComplexityCalculator()
            complexity_calculator.visit(ast_tree)
            metrics.cyclomatic_complexity = complexity_calculator.complexity
            
            # Apply findings impact to scores
            category_impacts = defaultdict(float)
            for finding in findings:
                category_impacts[finding.category] += finding.quality_impact
            
            # Calculate individual scores
            base_score = 10.0
            metrics.style_score = max(0.0, base_score + category_impacts[ReviewCategory.STYLE])
            metrics.performance_score = max(0.0, base_score + category_impacts[ReviewCategory.PERFORMANCE])
            metrics.security_score = max(0.0, base_score + category_impacts[ReviewCategory.SECURITY])
            metrics.maintainability_score = max(0.0, base_score + category_impacts[ReviewCategory.MAINTAINABILITY])
            metrics.reliability_score = max(0.0, base_score + category_impacts[ReviewCategory.RELIABILITY])
            metrics.documentation_score = max(0.0, base_score + category_impacts[ReviewCategory.DOCUMENTATION])
            metrics.autocad_best_practices_score = max(0.0, base_score + category_impacts[ReviewCategory.AUTOCAD_BEST_PRACTICES])
            
            # Complexity score (inverse relationship)
            if metrics.lines_of_code > 0:
                complexity_ratio = metrics.cyclomatic_complexity / metrics.lines_of_code
                metrics.complexity_score = max(0.0, 10.0 - complexity_ratio * 50)
            else:
                metrics.complexity_score = 10.0
            
            # Calculate overall score using weights
            weighted_scores = [
                metrics.style_score * self.quality_score_weights['style'],
                metrics.performance_score * self.quality_score_weights['performance'],
                metrics.security_score * self.quality_score_weights['security'],
                metrics.maintainability_score * self.quality_score_weights['maintainability'],
                metrics.reliability_score * self.quality_score_weights['reliability'],
                metrics.documentation_score * self.quality_score_weights['documentation'],
                metrics.complexity_score * self.quality_score_weights['complexity'],
                metrics.autocad_best_practices_score * self.quality_score_weights['autocad']
            ]
            
            metrics.overall_score = sum(weighted_scores)
        
        except Exception as e:
            logger.error(f"Quality metrics calculation failed: {e}")
            metrics.overall_score = 0.0
        
        return metrics
    
    def _initialize_score_weights(self) -> Dict[str, float]:
        """Initialize quality score weights."""
        return {
            'style': 0.10,
            'performance': 0.20,
            'security': 0.20,
            'maintainability': 0.15,
            'reliability': 0.20,
            'documentation': 0.05,
            'complexity': 0.05,
            'autocad': 0.05
        }
    
    # Additional helper methods for processing findings, generating statistics, etc.
    # The implementation continues with more specialized analysis methods...


class CyclomaticComplexityCalculator(ast.NodeVisitor):
    """Calculate cyclomatic complexity of code."""
    
    def __init__(self):
        self.complexity = 1  # Base complexity
    
    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_While(self, node):
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_For(self, node):
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_ExceptHandler(self, node):
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_With(self, node):
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_BoolOp(self, node):
        self.complexity += len(node.values) - 1
        self.generic_visit(node)