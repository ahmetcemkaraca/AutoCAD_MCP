"""
Comprehensive security scanning framework.

This module provides automated security scanning capabilities including
static analysis, dependency vulnerability scanning, and security pattern detection.
"""

import json
import logging
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Union, Any
import re
import ast

logger = logging.getLogger(__name__)


class SeverityLevel(Enum):
    """Security finding severity levels."""
    CRITICAL = "critical"
    HIGH = "high" 
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ScannerType(Enum):
    """Types of security scanners."""
    STATIC_ANALYSIS = "static_analysis"
    DEPENDENCY_SCAN = "dependency_scan"
    PATTERN_DETECTION = "pattern_detection"
    CODE_QUALITY = "code_quality"


@dataclass
class SecurityFinding:
    """Represents a security finding."""
    scanner: str
    severity: SeverityLevel
    title: str
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    code_snippet: Optional[str] = None
    cwe_id: Optional[str] = None
    recommendation: Optional[str] = None
    confidence: str = "MEDIUM"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert finding to dictionary."""
        return {
            'scanner': self.scanner,
            'severity': self.severity.value,
            'title': self.title,
            'description': self.description,
            'file_path': self.file_path,
            'line_number': self.line_number,
            'column_number': self.column_number,
            'code_snippet': self.code_snippet,
            'cwe_id': self.cwe_id,
            'recommendation': self.recommendation,
            'confidence': self.confidence
        }


@dataclass 
class ScanResult:
    """Results from a security scan."""
    scanner_type: ScannerType
    scanner_name: str
    start_time: float
    end_time: float
    status: str  # SUCCESS, ERROR, TIMEOUT
    findings: List[SecurityFinding] = field(default_factory=list)
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> float:
        """Scan duration in seconds."""
        return self.end_time - self.start_time
    
    @property
    def severity_counts(self) -> Dict[str, int]:
        """Count findings by severity."""
        counts = {severity.value: 0 for severity in SeverityLevel}
        for finding in self.findings:
            counts[finding.severity.value] += 1
        return counts
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert scan result to dictionary."""
        return {
            'scanner_type': self.scanner_type.value,
            'scanner_name': self.scanner_name,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'status': self.status,
            'findings': [finding.to_dict() for finding in self.findings],
            'error_message': self.error_message,
            'severity_counts': self.severity_counts,
            'metadata': self.metadata
        }


class PatternScanner:
    """Pattern-based security scanner."""
    
    SECURITY_PATTERNS = {
        'eval_usage': {
            'pattern': r'\beval\s*\(',
            'severity': SeverityLevel.HIGH,
            'description': 'Use of eval() function can lead to code injection',
            'cwe': 'CWE-95',
            'recommendation': 'Avoid eval(). Use ast.literal_eval() for safe evaluation'
        },
        'exec_usage': {
            'pattern': r'\bexec\s*\(',
            'severity': SeverityLevel.HIGH,
            'description': 'Use of exec() function can lead to code injection',
            'cwe': 'CWE-95',
            'recommendation': 'Avoid exec(). Use controlled execution environments'
        },
        'subprocess_shell': {
            'pattern': r'subprocess\.[^(]*\([^)]*shell\s*=\s*True',
            'severity': SeverityLevel.HIGH,
            'description': 'subprocess with shell=True can lead to command injection',
            'cwe': 'CWE-78',
            'recommendation': 'Use subprocess without shell=True and validate inputs'
        },
        'hardcoded_password': {
            'pattern': r'(?i)(password|passwd|pwd)\s*[=:]\s*["\'][^"\']{8,}["\']',
            'severity': SeverityLevel.CRITICAL,
            'description': 'Hardcoded password detected',
            'cwe': 'CWE-798',
            'recommendation': 'Use environment variables or secure configuration'
        },
        'hardcoded_api_key': {
            'pattern': r'(?i)(api[_-]?key|apikey|access[_-]?token)\s*[=:]\s*["\'][^"\']{16,}["\']',
            'severity': SeverityLevel.CRITICAL,
            'description': 'Hardcoded API key detected',
            'cwe': 'CWE-798',
            'recommendation': 'Use environment variables or secure configuration'
        },
        'sql_injection_risk': {
            'pattern': r'(execute|query|cursor)\s*\([^)]*["\'][^"\']*%[^"\']*["\']',
            'severity': SeverityLevel.HIGH,
            'description': 'Potential SQL injection vulnerability',
            'cwe': 'CWE-89',
            'recommendation': 'Use parameterized queries or prepared statements'
        },
        'unsafe_pickle': {
            'pattern': r'pickle\.(loads?|load)\s*\(',
            'severity': SeverityLevel.HIGH,
            'description': 'Unsafe pickle usage can lead to code execution',
            'cwe': 'CWE-502',
            'recommendation': 'Use json or other safe serialization formats'
        },
        'debug_code': {
            'pattern': r'(print\s*\(.*password|print\s*\(.*secret|print\s*\(.*token)',
            'severity': SeverityLevel.MEDIUM,
            'description': 'Debug code may leak sensitive information',
            'cwe': 'CWE-200',
            'recommendation': 'Remove debug statements or use proper logging'
        }
    }
    
    def scan_file(self, file_path: Path) -> List[SecurityFinding]:
        """Scan a single file for security patterns."""
        findings = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
            
            for pattern_name, pattern_info in self.SECURITY_PATTERNS.items():
                pattern = pattern_info['pattern']
                
                for line_num, line in enumerate(lines, 1):
                    matches = re.finditer(pattern, line)
                    
                    for match in matches:
                        finding = SecurityFinding(
                            scanner='pattern_scanner',
                            severity=pattern_info['severity'],
                            title=f"Security Pattern: {pattern_name}",
                            description=pattern_info['description'],
                            file_path=str(file_path),
                            line_number=line_num,
                            column_number=match.start(),
                            code_snippet=line.strip(),
                            cwe_id=pattern_info.get('cwe'),
                            recommendation=pattern_info.get('recommendation'),
                            confidence="MEDIUM"
                        )
                        findings.append(finding)
                        
        except Exception as e:
            logger.error(f"Error scanning file {file_path}: {e}")
        
        return findings


class SecurityScanner:
    """
    Comprehensive security scanner for the AutoCAD MCP platform.
    
    Integrates multiple security scanning tools and techniques.
    """
    
    def __init__(self, project_root: Path):
        """
        Initialize security scanner.
        
        Args:
            project_root: Root directory of the project to scan
        """
        self.project_root = Path(project_root)
        self.pattern_scanner = PatternScanner()
        
        # Available external scanners
        self.external_scanners = {
            'bandit': self._run_bandit_scan,
            'safety': self._run_safety_scan,
            'semgrep': self._run_semgrep_scan,
            'mypy': self._run_mypy_scan
        }
    
    def run_comprehensive_scan(self, include_external: bool = True) -> Dict[str, ScanResult]:
        """
        Run comprehensive security scan.
        
        Args:
            include_external: Whether to run external scanner tools
            
        Returns:
            Dictionary of scan results by scanner name
        """
        results = {}
        
        # Run pattern-based scanning
        logger.info("Running pattern-based security scan...")
        pattern_result = self._run_pattern_scan()
        results['pattern_scanner'] = pattern_result
        
        # Run external scanners if available and requested
        if include_external:
            for scanner_name, scanner_func in self.external_scanners.items():
                logger.info(f"Running {scanner_name} scan...")
                try:
                    result = scanner_func()
                    results[scanner_name] = result
                except Exception as e:
                    logger.error(f"Error running {scanner_name}: {e}")
                    results[scanner_name] = ScanResult(
                        scanner_type=ScannerType.STATIC_ANALYSIS,
                        scanner_name=scanner_name,
                        start_time=time.time(),
                        end_time=time.time(),
                        status="ERROR",
                        error_message=str(e)
                    )
        
        return results
    
    def _run_pattern_scan(self) -> ScanResult:
        """Run pattern-based security scanning."""
        start_time = time.time()
        findings = []
        
        # Scan all Python files
        python_files = list(self.project_root.rglob("*.py"))
        
        for file_path in python_files:
            if self._should_skip_file(file_path):
                continue
                
            file_findings = self.pattern_scanner.scan_file(file_path)
            findings.extend(file_findings)
        
        end_time = time.time()
        
        return ScanResult(
            scanner_type=ScannerType.PATTERN_DETECTION,
            scanner_name="pattern_scanner",
            start_time=start_time,
            end_time=end_time,
            status="SUCCESS",
            findings=findings,
            metadata={
                'files_scanned': len(python_files),
                'patterns_checked': len(PatternScanner.SECURITY_PATTERNS)
            }
        )
    
    def _run_bandit_scan(self) -> ScanResult:
        """Run Bandit security scanner."""
        start_time = time.time()
        
        try:
            # Check if bandit is available
            subprocess.run(['bandit', '--version'], capture_output=True, check=True)
            
            # Run bandit scan
            result = subprocess.run([
                'bandit', '-r', str(self.project_root / 'src'),
                '-f', 'json',
                '--skip', 'B101,B601',  # Skip assert_used and shell_injection for subprocess
                '--exclude', '**/test_*,**/tests/**'
            ], capture_output=True, text=True, timeout=300)
            
            findings = []
            if result.stdout:
                bandit_data = json.loads(result.stdout)
                
                for issue in bandit_data.get('results', []):
                    severity_map = {
                        'HIGH': SeverityLevel.HIGH,
                        'MEDIUM': SeverityLevel.MEDIUM,
                        'LOW': SeverityLevel.LOW
                    }
                    
                    finding = SecurityFinding(
                        scanner='bandit',
                        severity=severity_map.get(issue.get('issue_severity', 'MEDIUM'), SeverityLevel.MEDIUM),
                        title=issue.get('test_name', 'Unknown'),
                        description=issue.get('issue_text', ''),
                        file_path=issue.get('filename'),
                        line_number=issue.get('line_number'),
                        code_snippet=issue.get('code', ''),
                        cwe_id=issue.get('test_id'),
                        confidence=issue.get('issue_confidence', 'MEDIUM')
                    )
                    findings.append(finding)
            
            status = "SUCCESS" if result.returncode == 0 else "WARNING"
            
        except subprocess.CalledProcessError as e:
            return ScanResult(
                scanner_type=ScannerType.STATIC_ANALYSIS,
                scanner_name="bandit",
                start_time=start_time,
                end_time=time.time(),
                status="ERROR",
                error_message=f"Bandit failed: {e.stderr}"
            )
        except FileNotFoundError:
            return ScanResult(
                scanner_type=ScannerType.STATIC_ANALYSIS,
                scanner_name="bandit",
                start_time=start_time,
                end_time=time.time(),
                status="NOT_AVAILABLE",
                error_message="Bandit not installed. Install with: pip install bandit"
            )
        except subprocess.TimeoutExpired:
            return ScanResult(
                scanner_type=ScannerType.STATIC_ANALYSIS,
                scanner_name="bandit",
                start_time=start_time,
                end_time=time.time(),
                status="TIMEOUT",
                error_message="Bandit scan timed out"
            )
        
        end_time = time.time()
        
        return ScanResult(
            scanner_type=ScannerType.STATIC_ANALYSIS,
            scanner_name="bandit",
            start_time=start_time,
            end_time=end_time,
            status=status,
            findings=findings
        )
    
    def _run_safety_scan(self) -> ScanResult:
        """Run Safety dependency vulnerability scanner."""
        start_time = time.time()
        
        try:
            # Check if safety is available
            subprocess.run(['safety', '--version'], capture_output=True, check=True)
            
            # Run safety check
            result = subprocess.run([
                'safety', 'check', '--json'
            ], capture_output=True, text=True, timeout=120)
            
            findings = []
            if result.stdout:
                try:
                    safety_data = json.loads(result.stdout)
                    
                    for vuln in safety_data:
                        finding = SecurityFinding(
                            scanner='safety',
                            severity=SeverityLevel.HIGH,  # All dependency vulns are high
                            title=f"Vulnerable dependency: {vuln.get('package')}",
                            description=vuln.get('advisory', ''),
                            recommendation=f"Update {vuln.get('package')} to version {vuln.get('safe_versions', ['latest'])[0]}",
                            cwe_id=vuln.get('cve')
                        )
                        findings.append(finding)
                except json.JSONDecodeError:
                    # Safety might output plain text on no vulnerabilities
                    pass
            
            status = "SUCCESS"
            
        except subprocess.CalledProcessError as e:
            # Safety returns non-zero exit code when vulnerabilities found
            status = "WARNING" if findings else "ERROR"
            
        except FileNotFoundError:
            return ScanResult(
                scanner_type=ScannerType.DEPENDENCY_SCAN,
                scanner_name="safety",
                start_time=start_time,
                end_time=time.time(),
                status="NOT_AVAILABLE",
                error_message="Safety not installed. Install with: pip install safety"
            )
        except subprocess.TimeoutExpired:
            return ScanResult(
                scanner_type=ScannerType.DEPENDENCY_SCAN,
                scanner_name="safety",
                start_time=start_time,
                end_time=time.time(),
                status="TIMEOUT",
                error_message="Safety scan timed out"
            )
        
        end_time = time.time()
        
        return ScanResult(
            scanner_type=ScannerType.DEPENDENCY_SCAN,
            scanner_name="safety",
            start_time=start_time,
            end_time=end_time,
            status=status,
            findings=findings
        )
    
    def _run_semgrep_scan(self) -> ScanResult:
        """Run Semgrep security scanner."""
        start_time = time.time()
        
        try:
            # Check if semgrep is available
            subprocess.run(['semgrep', '--version'], capture_output=True, check=True)
            
            # Run semgrep scan with security rules
            result = subprocess.run([
                'semgrep', '--config=auto',
                '--json',
                '--quiet',
                str(self.project_root / 'src')
            ], capture_output=True, text=True, timeout=300)
            
            findings = []
            if result.stdout:
                semgrep_data = json.loads(result.stdout)
                
                for issue in semgrep_data.get('results', []):
                    severity_map = {
                        'ERROR': SeverityLevel.HIGH,
                        'WARNING': SeverityLevel.MEDIUM,
                        'INFO': SeverityLevel.LOW
                    }
                    
                    finding = SecurityFinding(
                        scanner='semgrep',
                        severity=severity_map.get(issue.get('severity', 'WARNING'), SeverityLevel.MEDIUM),
                        title=issue.get('check_id', 'Unknown'),
                        description=issue.get('message', ''),
                        file_path=issue.get('path'),
                        line_number=issue.get('start', {}).get('line'),
                        code_snippet=issue.get('extra', {}).get('lines', ''),
                        recommendation="Review and fix according to Semgrep recommendation"
                    )
                    findings.append(finding)
            
            status = "SUCCESS"
            
        except FileNotFoundError:
            return ScanResult(
                scanner_type=ScannerType.STATIC_ANALYSIS,
                scanner_name="semgrep",
                start_time=start_time,
                end_time=time.time(),
                status="NOT_AVAILABLE",
                error_message="Semgrep not installed. Install with: pip install semgrep"
            )
        except subprocess.TimeoutExpired:
            return ScanResult(
                scanner_type=ScannerType.STATIC_ANALYSIS,
                scanner_name="semgrep",
                start_time=start_time,
                end_time=time.time(),
                status="TIMEOUT",
                error_message="Semgrep scan timed out"
            )
        except Exception as e:
            return ScanResult(
                scanner_type=ScannerType.STATIC_ANALYSIS,
                scanner_name="semgrep",
                start_time=start_time,
                end_time=time.time(),
                status="ERROR",
                error_message=str(e)
            )
        
        end_time = time.time()
        
        return ScanResult(
            scanner_type=ScannerType.STATIC_ANALYSIS,
            scanner_name="semgrep",
            start_time=start_time,
            end_time=end_time,
            status=status,
            findings=findings
        )
    
    def _run_mypy_scan(self) -> ScanResult:
        """Run MyPy type checker as security scanner."""
        start_time = time.time()
        
        try:
            # Check if mypy is available
            subprocess.run(['mypy', '--version'], capture_output=True, check=True)
            
            # Run mypy scan
            result = subprocess.run([
                'mypy', str(self.project_root / 'src'),
                '--ignore-missing-imports',
                '--show-error-codes'
            ], capture_output=True, text=True, timeout=180)
            
            findings = []
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if ':' in line and ('error:' in line or 'warning:' in line):
                        parts = line.split(':', 3)
                        if len(parts) >= 4:
                            file_path = parts[0]
                            line_num = int(parts[1]) if parts[1].isdigit() else None
                            message = parts[3].strip()
                            
                            finding = SecurityFinding(
                                scanner='mypy',
                                severity=SeverityLevel.LOW,
                                title="Type safety issue",
                                description=message,
                                file_path=file_path,
                                line_number=line_num,
                                recommendation="Fix type annotations for better code safety"
                            )
                            findings.append(finding)
            
            status = "SUCCESS"
            
        except FileNotFoundError:
            return ScanResult(
                scanner_type=ScannerType.CODE_QUALITY,
                scanner_name="mypy",
                start_time=start_time,
                end_time=time.time(),
                status="NOT_AVAILABLE",
                error_message="MyPy not installed. Install with: pip install mypy"
            )
        except subprocess.TimeoutExpired:
            return ScanResult(
                scanner_type=ScannerType.CODE_QUALITY,
                scanner_name="mypy",
                start_time=start_time,
                end_time=time.time(),
                status="TIMEOUT",
                error_message="MyPy scan timed out"
            )
        except Exception as e:
            return ScanResult(
                scanner_type=ScannerType.CODE_QUALITY,
                scanner_name="mypy",
                start_time=start_time,
                end_time=time.time(),
                status="ERROR",
                error_message=str(e)
            )
        
        end_time = time.time()
        
        return ScanResult(
            scanner_type=ScannerType.CODE_QUALITY,
            scanner_name="mypy",
            start_time=start_time,
            end_time=end_time,
            status=status,
            findings=findings
        )
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during scanning."""
        skip_patterns = [
            '__pycache__',
            '.git',
            '.venv',
            'venv',
            'node_modules',
            '.pytest_cache',
            'test_',
            '_test.py',
            'tests/',
            'DELETED/'
        ]
        
        file_str = str(file_path)
        return any(pattern in file_str for pattern in skip_patterns)
    
    def generate_report(self, scan_results: Dict[str, ScanResult], 
                       output_format: str = 'json') -> str:
        """
        Generate security scan report.
        
        Args:
            scan_results: Results from security scans
            output_format: Output format ('json', 'text', 'html')
            
        Returns:
            Formatted report string
        """
        if output_format == 'json':
            return self._generate_json_report(scan_results)
        elif output_format == 'text':
            return self._generate_text_report(scan_results)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
    
    def _generate_json_report(self, scan_results: Dict[str, ScanResult]) -> str:
        """Generate JSON report."""
        report = {
            'scan_timestamp': time.time(),
            'project_root': str(self.project_root),
            'summary': {
                'total_scanners': len(scan_results),
                'successful_scans': sum(1 for r in scan_results.values() if r.status == 'SUCCESS'),
                'total_findings': sum(len(r.findings) for r in scan_results.values()),
                'severity_breakdown': {}
            },
            'scan_results': {}
        }
        
        # Calculate severity breakdown
        all_severities = {severity.value: 0 for severity in SeverityLevel}
        for result in scan_results.values():
            for severity, count in result.severity_counts.items():
                all_severities[severity] += count
        
        report['summary']['severity_breakdown'] = all_severities
        
        # Add scan results
        for scanner_name, result in scan_results.items():
            report['scan_results'][scanner_name] = result.to_dict()
        
        return json.dumps(report, indent=2)
    
    def _generate_text_report(self, scan_results: Dict[str, ScanResult]) -> str:
        """Generate text report."""
        lines = []
        lines.append("=" * 80)
        lines.append("AUTOCAD MCP SECURITY SCAN REPORT")
        lines.append("=" * 80)
        lines.append("")
        
        # Summary
        total_findings = sum(len(r.findings) for r in scan_results.values())
        lines.append(f"Project: {self.project_root}")
        lines.append(f"Scan Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Total Scanners: {len(scan_results)}")
        lines.append(f"Total Findings: {total_findings}")
        lines.append("")
        
        # Severity breakdown
        all_severities = {severity.value: 0 for severity in SeverityLevel}
        for result in scan_results.values():
            for severity, count in result.severity_counts.items():
                all_severities[severity] += count
        
        lines.append("Severity Breakdown:")
        for severity, count in all_severities.items():
            if count > 0:
                lines.append(f"  {severity.upper()}: {count}")
        lines.append("")
        
        # Scanner results
        for scanner_name, result in scan_results.items():
            lines.append(f"Scanner: {scanner_name}")
            lines.append(f"Status: {result.status}")
            lines.append(f"Duration: {result.duration:.2f}s")
            lines.append(f"Findings: {len(result.findings)}")
            
            if result.error_message:
                lines.append(f"Error: {result.error_message}")
            
            # Show critical and high findings
            critical_high = [f for f in result.findings 
                           if f.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]]
            
            if critical_high:
                lines.append("  Critical/High Findings:")
                for finding in critical_high[:5]:  # Show first 5
                    lines.append(f"    - {finding.title}")
                    if finding.file_path:
                        lines.append(f"      File: {finding.file_path}:{finding.line_number or '?'}")
                    lines.append(f"      {finding.description}")
                
                if len(critical_high) > 5:
                    lines.append(f"    ... and {len(critical_high) - 5} more")
            
            lines.append("")
        
        return "\n".join(lines)


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='AutoCAD MCP Security Scanner')
    parser.add_argument('project_path', help='Path to project root')
    parser.add_argument('--format', choices=['json', 'text'], default='text',
                       help='Output format')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    parser.add_argument('--no-external', action='store_true',
                       help='Skip external scanner tools')
    
    args = parser.parse_args()
    
    # Initialize scanner
    scanner = SecurityScanner(Path(args.project_path))
    
    # Run scans
    print("Running comprehensive security scan...", file=sys.stderr)
    results = scanner.run_comprehensive_scan(include_external=not args.no_external)
    
    # Generate report
    report = scanner.generate_report(results, args.format)
    
    # Output report
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"Report saved to {args.output}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    import sys
    main()