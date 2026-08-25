"""
Dependency Management for AutoCAD Projects.

Handles dependency installation, management, and compatibility checking
for AutoCAD automation projects.
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
try:
    import tomli
    import tomli_w
except ImportError:
    # Fallback for systems without tomli
    tomli = None
    tomli_w = None

logger = logging.getLogger(__name__)


@dataclass
class Dependency:
    """Represents a project dependency."""
    name: str
    version: str
    description: str = ""
    optional: bool = False
    group: str = "main"  # main, dev, test, etc.
    platform: Optional[str] = None  # windows, linux, macos


class DependencyManager:
    """Manages dependencies for AutoCAD automation projects."""
    
    def __init__(self):
        self.common_dependencies = self._initialize_common_dependencies()
        self.autocad_dependencies = self._initialize_autocad_dependencies()
    
    def _initialize_common_dependencies(self) -> Dict[str, Dependency]:
        """Initialize common Python dependencies."""
        return {
            "pytest": Dependency(
                name="pytest",
                version=">=8.0.0",
                description="Testing framework",
                group="dev"
            ),
            "pytest-cov": Dependency(
                name="pytest-cov", 
                version=">=4.0.0",
                description="Coverage plugin for pytest",
                group="dev"
            ),
            "black": Dependency(
                name="black",
                version=">=24.0.0", 
                description="Code formatter",
                group="dev"
            ),
            "ruff": Dependency(
                name="ruff",
                version=">=0.5.0",
                description="Fast Python linter",
                group="dev"
            ),
            "mypy": Dependency(
                name="mypy",
                version=">=1.8.0",
                description="Static type checker",
                group="dev"
            ),
            "numpy": Dependency(
                name="numpy",
                version=">=1.24.0",
                description="Numerical computing library"
            ),
            "requests": Dependency(
                name="requests",
                version=">=2.31.0",
                description="HTTP library"
            ),
            "click": Dependency(
                name="click",
                version=">=8.1.0", 
                description="Command line interface creation"
            )
        }
    
    def _initialize_autocad_dependencies(self) -> Dict[str, Dependency]:
        """Initialize AutoCAD-specific dependencies."""
        return {
            "pywin32": Dependency(
                name="pywin32",
                version=">=306",
                description="Windows COM interface",
                platform="windows"
            ),
            "pyautocad": Dependency(
                name="pyautocad",
                version=">=0.2.0",
                description="AutoCAD automation library",
                platform="windows"
            ),
            "fastmcp": Dependency(
                name="fastmcp",
                version=">=1.0.0",
                description="MCP server framework",
                optional=True
            ),
            "psutil": Dependency(
                name="psutil",
                version=">=5.9.0",
                description="System and process utilities"
            ),
            "scipy": Dependency(
                name="scipy", 
                version=">=1.10.0",
                description="Scientific computing library",
                optional=True
            ),
            "matplotlib": Dependency(
                name="matplotlib",
                version=">=3.7.0",
                description="Plotting library",
                optional=True
            ),
            "pandas": Dependency(
                name="pandas",
                version=">=2.0.0",
                description="Data analysis library", 
                optional=True
            )
        }
    
    def get_dependencies_for_project_type(self, project_type: str) -> List[Dependency]:
        """Get recommended dependencies for specific project type."""
        base_deps = [
            self.autocad_dependencies["pywin32"],
            self.autocad_dependencies["pyautocad"],
            self.common_dependencies["pytest"],
            self.common_dependencies["black"],
            self.common_dependencies["ruff"]
        ]
        
        if project_type == "basic_autocad":
            return base_deps + [
                self.autocad_dependencies["psutil"],
                self.common_dependencies["click"]
            ]
        
        elif project_type == "advanced_mcp":
            return base_deps + [
                self.autocad_dependencies["fastmcp"],
                self.autocad_dependencies["psutil"],
                self.common_dependencies["pytest-cov"],
                self.common_dependencies["mypy"]
            ]
        
        elif project_type == "manufacturing_cad":
            return base_deps + [
                self.autocad_dependencies["numpy"],
                self.autocad_dependencies["scipy"],
                self.autocad_dependencies["matplotlib"],
                self.autocad_dependencies["pandas"],
                self.common_dependencies["numpy"]
            ]
        
        else:
            return base_deps
    
    def create_pyproject_toml(self, project_path: str, project_type: str, 
                            project_config: Dict[str, Any]) -> str:
        """Create pyproject.toml with proper dependencies."""
        dependencies = self.get_dependencies_for_project_type(project_type)
        
        # Separate dependencies by group
        main_deps = []
        dev_deps = []
        
        for dep in dependencies:
            dep_spec = f"{dep.name}{dep.version}"
            if dep.group == "dev":
                dev_deps.append(dep_spec)
            else:
                main_deps.append(dep_spec)
        
        # Create pyproject.toml structure
        pyproject_data = {
            "tool": {
                "poetry": {
                    "name": project_config.get("project_slug", "autocad-project"),
                    "version": "0.1.0",
                    "description": project_config.get("project_name", "AutoCAD Project"),
                    "authors": [f"{project_config.get('author_name', 'Developer')} <{project_config.get('author_email', 'dev@example.com')}>"],
                    "dependencies": {
                        "python": f"^{project_config.get('python_version', '3.12')}"
                    },
                    "group": {
                        "dev": {
                            "dependencies": {}
                        }
                    }
                },
                "black": {
                    "line-length": 88,
                    "target-version": [f"py{project_config.get('python_version', '3.12').replace('.', '')}"]
                },
                "ruff": {
                    "line-length": 88,
                    "target-version": f"py{project_config.get('python_version', '3.12').replace('.', '')}"
                },
                "mypy": {
                    "python_version": project_config.get('python_version', '3.12'),
                    "warn_return_any": True,
                    "warn_unused_configs": True,
                    "disallow_untyped_defs": True
                }
            },
            "build-system": {
                "requires": ["poetry-core"],
                "build-backend": "poetry.core.masonry.api"
            }
        }
        
        # Add main dependencies
        for dep_spec in main_deps:
            name, version = self._parse_dependency_spec(dep_spec)
            pyproject_data["tool"]["poetry"]["dependencies"][name] = version
        
        # Add dev dependencies
        for dep_spec in dev_deps:
            name, version = self._parse_dependency_spec(dep_spec)
            pyproject_data["tool"]["poetry"]["group"]["dev"]["dependencies"][name] = version
        
        # Write pyproject.toml
        pyproject_path = Path(project_path) / "pyproject.toml"
        with open(pyproject_path, "wb") as f:
            tomli_w.dump(pyproject_data, f)
        
        logger.info(f"Created pyproject.toml with {len(main_deps)} main and {len(dev_deps)} dev dependencies")
        return str(pyproject_path)
    
    def _parse_dependency_spec(self, dep_spec: str) -> Tuple[str, str]:
        """Parse dependency specification into name and version."""
        if ">=" in dep_spec:
            name, version = dep_spec.split(">=")
            return name, f"^{version}"
        elif "==" in dep_spec:
            name, version = dep_spec.split("==")
            return name, version
        else:
            return dep_spec, "*"
    
    def create_requirements_txt(self, project_path: str, project_type: str) -> str:
        """Create requirements.txt file."""
        dependencies = self.get_dependencies_for_project_type(project_type)
        
        requirements_path = Path(project_path) / "requirements.txt"
        with open(requirements_path, "w", encoding="utf-8") as f:
            f.write(f"# Requirements for {project_type} project\\n")
            f.write(f"# Generated by AutoCAD MCP Dependency Manager\\n\\n")
            
            # Main dependencies
            f.write("# Main dependencies\\n")
            for dep in dependencies:
                if dep.group == "main":
                    f.write(f"{dep.name}{dep.version}\\n")
            
            f.write("\\n# Development dependencies\\n")
            for dep in dependencies:
                if dep.group == "dev":
                    f.write(f"{dep.name}{dep.version}\\n")
        
        logger.info(f"Created requirements.txt with {len(dependencies)} dependencies")
        return str(requirements_path)
    
    def check_dependency_compatibility(self, project_path: str) -> Dict[str, Any]:
        """Check for dependency compatibility issues."""
        results = {
            "compatible": True,
            "issues": [],
            "warnings": [],
            "recommendations": []
        }
        
        # Check if pyproject.toml exists
        pyproject_path = Path(project_path) / "pyproject.toml"
        if not pyproject_path.exists():
            results["issues"].append("No pyproject.toml found")
            results["compatible"] = False
            return results
        
        try:
            # Load and parse pyproject.toml
            with open(pyproject_path, "rb") as f:
                pyproject_data = tomli.load(f)
            
            dependencies = pyproject_data.get("tool", {}).get("poetry", {}).get("dependencies", {})
            
            # Check for Windows-only dependencies on non-Windows systems
            import platform
            if platform.system() != "Windows":
                windows_deps = ["pywin32", "pyautocad"]
                for dep in windows_deps:
                    if dep in dependencies:
                        results["warnings"].append(f"{dep} is Windows-only but system is {platform.system()}")
            
            # Check for conflicting versions
            self._check_version_conflicts(dependencies, results)
            
            # Check for missing AutoCAD dependencies
            self._check_autocad_dependencies(dependencies, results)
            
        except Exception as e:
            results["issues"].append(f"Error reading pyproject.toml: {e}")
            results["compatible"] = False
        
        return results
    
    def _check_version_conflicts(self, dependencies: Dict[str, str], results: Dict[str, Any]):
        """Check for version conflicts between dependencies."""
        # This is a simplified version - real implementation would use pip-tools or similar
        known_conflicts = {
            ("numpy", "scipy"): "SciPy requires NumPy - ensure compatible versions"
        }
        
        for (dep1, dep2), message in known_conflicts.items():
            if dep1 in dependencies and dep2 in dependencies:
                results["recommendations"].append(message)
    
    def _check_autocad_dependencies(self, dependencies: Dict[str, str], results: Dict[str, Any]):
        """Check for essential AutoCAD dependencies."""
        required_for_autocad = ["pywin32"]
        for dep in required_for_autocad:
            if dep not in dependencies:
                results["issues"].append(f"Missing required AutoCAD dependency: {dep}")
    
    def install_dependencies(self, project_path: str, use_poetry: bool = True) -> bool:
        """Install project dependencies."""
        try:
            if use_poetry and self._is_poetry_available():
                return self._install_with_poetry(project_path)
            else:
                return self._install_with_pip(project_path)
        except Exception as e:
            logger.error(f"Failed to install dependencies: {e}")
            return False
    
    def _is_poetry_available(self) -> bool:
        """Check if Poetry is available."""
        try:
            result = subprocess.run(["poetry", "--version"], 
                                  capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _install_with_poetry(self, project_path: str) -> bool:
        """Install dependencies using Poetry."""
        try:
            result = subprocess.run(["poetry", "install"], 
                                  cwd=project_path, check=True, capture_output=True)
            logger.info("Dependencies installed successfully with Poetry")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Poetry installation failed: {e}")
            return False
    
    def _install_with_pip(self, project_path: str) -> bool:
        """Install dependencies using pip."""
        try:
            requirements_path = Path(project_path) / "requirements.txt"
            if not requirements_path.exists():
                logger.error("No requirements.txt found")
                return False
            
            result = subprocess.run([
                "python", "-m", "pip", "install", "-r", str(requirements_path)
            ], cwd=project_path, check=True, capture_output=True)
            
            logger.info("Dependencies installed successfully with pip")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Pip installation failed: {e}")
            return False
    
    def update_dependencies(self, project_path: str) -> Dict[str, Any]:
        """Update project dependencies to latest compatible versions."""
        results = {
            "updated": [],
            "failed": [],
            "unchanged": []
        }
        
        try:
            if self._is_poetry_available():
                # Use poetry update
                result = subprocess.run(["poetry", "update"], 
                                      cwd=project_path, check=True, capture_output=True)
                results["updated"].append("All dependencies updated via Poetry")
            else:
                # Use pip upgrade
                result = subprocess.run([
                    "python", "-m", "pip", "list", "--outdated", "--format=json"
                ], cwd=project_path, check=True, capture_output=True)
                
                outdated = json.loads(result.stdout)
                for package in outdated:
                    try:
                        subprocess.run([
                            "python", "-m", "pip", "install", "--upgrade", package["name"]
                        ], cwd=project_path, check=True, capture_output=True)
                        results["updated"].append(package["name"])
                    except subprocess.CalledProcessError:
                        results["failed"].append(package["name"])
        
        except Exception as e:
            logger.error(f"Failed to update dependencies: {e}")
            results["failed"].append(f"Update process failed: {e}")
        
        return results
    
    def generate_dependency_report(self, project_path: str) -> str:
        """Generate dependency analysis report."""
        compatibility = self.check_dependency_compatibility(project_path)
        
        report = []
        report.append("Dependency Analysis Report")
        report.append("=" * 30)
        report.append("")
        
        if compatibility["compatible"]:
            report.append("✓ Dependencies are compatible")
        else:
            report.append("✗ Dependency issues found")
        
        if compatibility["issues"]:
            report.append("\\nIssues:")
            for issue in compatibility["issues"]:
                report.append(f"  - {issue}")
        
        if compatibility["warnings"]:
            report.append("\\nWarnings:")
            for warning in compatibility["warnings"]:
                report.append(f"  - {warning}")
        
        if compatibility["recommendations"]:
            report.append("\\nRecommendations:")
            for rec in compatibility["recommendations"]:
                report.append(f"  - {rec}")
        
        # Add installed packages info
        try:
            result = subprocess.run([
                "python", "-m", "pip", "list", "--format=json"
            ], cwd=project_path, check=True, capture_output=True)
            
            packages = json.loads(result.stdout)
            report.append(f"\\nInstalled Packages: {len(packages)}")
            
            # Show AutoCAD-related packages
            autocad_packages = [p for p in packages if any(
                keyword in p["name"].lower() 
                for keyword in ["autocad", "pywin32", "mcp"]
            )]
            
            if autocad_packages:
                report.append("\\nAutoCAD-related packages:")
                for pkg in autocad_packages:
                    report.append(f"  - {pkg['name']} {pkg['version']}")
                    
        except Exception as e:
            report.append(f"\\nCould not retrieve package information: {e}")
        
        return "\\n".join(report)
    
    def add_dependency(self, project_path: str, dependency_name: str, 
                      version: str = None, group: str = "main") -> bool:
        """Add a new dependency to the project."""
        try:
            pyproject_path = Path(project_path) / "pyproject.toml"
            if not pyproject_path.exists():
                logger.error("No pyproject.toml found")
                return False
            
            # Load current pyproject.toml
            with open(pyproject_path, "rb") as f:
                pyproject_data = tomli.load(f)
            
            # Add dependency
            dep_spec = version if version else "*"
            if group == "dev":
                pyproject_data["tool"]["poetry"]["group"]["dev"]["dependencies"][dependency_name] = dep_spec
            else:
                pyproject_data["tool"]["poetry"]["dependencies"][dependency_name] = dep_spec
            
            # Save updated pyproject.toml
            with open(pyproject_path, "wb") as f:
                tomli_w.dump(pyproject_data, f)
            
            logger.info(f"Added dependency: {dependency_name} ({group})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add dependency: {e}")
            return False
    
    def remove_dependency(self, project_path: str, dependency_name: str) -> bool:
        """Remove a dependency from the project."""
        try:
            pyproject_path = Path(project_path) / "pyproject.toml"
            if not pyproject_path.exists():
                logger.error("No pyproject.toml found")
                return False
            
            # Load current pyproject.toml
            with open(pyproject_path, "rb") as f:
                pyproject_data = tomli.load(f)
            
            # Remove from main dependencies
            main_deps = pyproject_data["tool"]["poetry"]["dependencies"]
            if dependency_name in main_deps:
                del main_deps[dependency_name]
                removed = True
            
            # Remove from dev dependencies
            dev_deps = pyproject_data["tool"]["poetry"]["group"]["dev"]["dependencies"]
            if dependency_name in dev_deps:
                del dev_deps[dependency_name]
                removed = True
            
            if removed:
                # Save updated pyproject.toml
                with open(pyproject_path, "wb") as f:
                    tomli_w.dump(pyproject_data, f)
                
                logger.info(f"Removed dependency: {dependency_name}")
                return True
            else:
                logger.warning(f"Dependency not found: {dependency_name}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to remove dependency: {e}")
            return False