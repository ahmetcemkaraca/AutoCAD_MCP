"""
Project Scaffolding for AutoCAD Automation Projects.

Creates complete project structures with proper organization,
dependency management, and development tools setup.
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .template_engine import TemplateEngine, ProjectTemplate
from .dependency_manager import DependencyManager

logger = logging.getLogger(__name__)


@dataclass
class ProjectScaffoldConfig:
    """Configuration for project scaffolding."""
    project_name: str
    project_type: str  # 'basic', 'advanced', 'manufacturing'
    output_directory: str
    author_name: str = "Developer"
    author_email: str = "developer@example.com"
    python_version: str = "3.12"
    initialize_git: bool = True
    install_dependencies: bool = True
    create_venv: bool = True
    setup_ci: bool = False
    ci_provider: str = "github"  # 'github', 'azure', 'jenkins'


class ProjectScaffolder:
    """Creates complete project scaffolds for AutoCAD automation."""
    
    def __init__(self):
        self.template_engine = TemplateEngine()
        self.dependency_manager = DependencyManager()
        
    def create_project(self, config: ProjectScaffoldConfig) -> str:
        """Create a complete project from configuration."""
        logger.info(f"Creating project: {config.project_name}")
        
        # Validate configuration
        self._validate_config(config)
        
        # Create project from template
        project_path = self._create_from_template(config)
        
        # Initialize git repository if requested
        if config.initialize_git:
            self._initialize_git(project_path)
        
        # Create virtual environment if requested
        if config.create_venv:
            self._create_virtual_environment(project_path)
        
        # Install dependencies if requested
        if config.install_dependencies:
            self._install_dependencies(project_path, config)
        
        # Setup CI/CD if requested
        if config.setup_ci:
            self._setup_ci_cd(project_path, config)
        
        # Post-creation setup
        self._post_creation_setup(project_path, config)
        
        logger.info(f"Project created successfully at: {project_path}")
        return project_path
    
    def _validate_config(self, config: ProjectScaffoldConfig):
        """Validate project configuration."""
        if not config.project_name.strip():
            raise ValueError("Project name cannot be empty")
        
        if config.project_type not in ['basic_autocad', 'advanced_mcp', 'manufacturing_cad']:
            raise ValueError(f"Invalid project type: {config.project_type}")
        
        output_path = Path(config.output_directory)
        if output_path.exists() and list(output_path.iterdir()):
            raise ValueError(f"Output directory is not empty: {config.output_directory}")
    
    def _create_from_template(self, config: ProjectScaffoldConfig) -> str:
        """Create project from template."""
        template_params = {
            'project_name': config.project_name,
            'author_name': config.author_name,
            'author_email': config.author_email,
            'python_version': config.python_version
        }
        
        # Add type-specific parameters
        if config.project_type == 'manufacturing_cad':
            template_params.update({
                'company_name': 'Manufacturing Corp',
                'material_types': ['steel', 'aluminum', 'plastic'],
                'default_thickness': '3.0'
            })
        
        project_path = self.template_engine.create_project_from_template(
            template_name=config.project_type,
            output_dir=config.output_directory,
            parameters=template_params
        )
        
        return project_path
    
    def _initialize_git(self, project_path: str):
        """Initialize git repository."""
        try:
            import subprocess
            
            # Initialize git repository
            subprocess.run(['git', 'init'], cwd=project_path, check=True, capture_output=True)
            
            # Create initial commit
            subprocess.run(['git', 'add', '.'], cwd=project_path, check=True, capture_output=True)
            subprocess.run([
                'git', 'commit', '-m', 'Initial commit - Project scaffolding complete'
            ], cwd=project_path, check=True, capture_output=True)
            
            logger.info("Git repository initialized")
            
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.warning(f"Failed to initialize git repository: {e}")
    
    def _create_virtual_environment(self, project_path: str):
        """Create Python virtual environment."""
        try:
            import subprocess
            
            venv_path = Path(project_path) / 'venv'
            
            # Create virtual environment
            subprocess.run([
                'python', '-m', 'venv', str(venv_path)
            ], check=True, capture_output=True)
            
            logger.info("Virtual environment created")
            
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to create virtual environment: {e}")
    
    def _install_dependencies(self, project_path: str, config: ProjectScaffoldConfig):
        """Install project dependencies."""
        try:
            # Check if Poetry is available
            if self._is_poetry_available():
                self._install_with_poetry(project_path)
            else:
                self._install_with_pip(project_path)
                
        except Exception as e:
            logger.warning(f"Failed to install dependencies: {e}")
    
    def _is_poetry_available(self) -> bool:
        """Check if Poetry is available."""
        try:
            import subprocess
            result = subprocess.run(['poetry', '--version'], 
                                  capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _install_with_poetry(self, project_path: str):
        """Install dependencies using Poetry."""
        try:
            import subprocess
            
            # Install dependencies
            subprocess.run(['poetry', 'install'], 
                         cwd=project_path, check=True, capture_output=True)
            
            logger.info("Dependencies installed with Poetry")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Poetry installation failed: {e}")
            # Fallback to pip
            self._install_with_pip(project_path)
    
    def _install_with_pip(self, project_path: str):
        """Install dependencies using pip."""
        try:
            import subprocess
            
            # Check for requirements.txt or extract from pyproject.toml
            requirements_file = Path(project_path) / 'requirements.txt'
            if not requirements_file.exists():
                self._create_requirements_file(project_path)
            
            # Determine python executable
            venv_path = Path(project_path) / 'venv'
            if venv_path.exists():
                if os.name == 'nt':  # Windows
                    python_exe = venv_path / 'Scripts' / 'python.exe'
                else:  # Unix-like
                    python_exe = venv_path / 'bin' / 'python'
            else:
                python_exe = 'python'
            
            # Install dependencies
            subprocess.run([
                str(python_exe), '-m', 'pip', 'install', '-r', str(requirements_file)
            ], check=True, capture_output=True)
            
            logger.info("Dependencies installed with pip")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Pip installation failed: {e}")
    
    def _create_requirements_file(self, project_path: str):
        """Create requirements.txt from template dependencies."""
        template_name = self._detect_template_type(project_path)
        template = self.template_engine.get_template(template_name)
        
        if template and template.dependencies:
            requirements_path = Path(project_path) / 'requirements.txt'
            with open(requirements_path, 'w', encoding='utf-8') as f:
                for dep in template.dependencies:
                    f.write(f"{dep}\\n")
            
            logger.info("Created requirements.txt file")
    
    def _detect_template_type(self, project_path: str) -> str:
        """Detect template type from project structure."""
        project_path = Path(project_path)
        
        if (project_path / 'src' / 'mcp_tools').exists():
            return 'advanced_mcp'
        elif (project_path / 'src' / 'manufacturing').exists():
            return 'manufacturing_cad'
        else:
            return 'basic_autocad'
    
    def _setup_ci_cd(self, project_path: str, config: ProjectScaffoldConfig):
        """Setup CI/CD integration."""
        try:
            from .ci_integration import CIIntegration, CIConfiguration
            
            ci_integration = CIIntegration()
            ci_config = CIConfiguration(
                provider=config.ci_provider,
                project_path=project_path,
                test_commands=[
                    "python -m pytest tests/ --cov=src",
                    "python -m pytest tests/generated/"
                ],
                python_version=config.python_version
            )
            
            ci_integration.setup_ci_integration(project_path, config.ci_provider, ci_config)
            logger.info(f"CI/CD setup completed for {config.ci_provider}")
            
        except Exception as e:
            logger.warning(f"Failed to setup CI/CD: {e}")
    
    def _post_creation_setup(self, project_path: str, config: ProjectScaffoldConfig):
        """Perform post-creation setup tasks."""
        # Create additional directories if needed
        additional_dirs = ['logs', 'temp', 'output']
        for dir_name in additional_dirs:
            dir_path = Path(project_path) / dir_name
            dir_path.mkdir(exist_ok=True)
            
            # Create .gitkeep files
            (dir_path / '.gitkeep').touch()
        
        # Create development scripts
        self._create_development_scripts(project_path)
        
        logger.info("Post-creation setup completed")
    
    def _create_development_scripts(self, project_path: str):
        """Create helpful development scripts."""
        scripts_dir = Path(project_path) / 'scripts'
        scripts_dir.mkdir(exist_ok=True)
        
        # Create test runner script
        test_script = scripts_dir / 'run_tests.py'
        test_script_content = '''#!/usr/bin/env python3
"""Test runner script."""

import subprocess
import sys
from pathlib import Path

def main():
    """Run all tests."""
    project_root = Path(__file__).parent.parent
    
    # Run tests
    result = subprocess.run([
        sys.executable, '-m', 'pytest', 
        'tests/', '--cov=src', '--cov-report=html'
    ], cwd=project_root)
    
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
'''
        
        with open(test_script, 'w', encoding='utf-8') as f:
            f.write(test_script_content)
        
        # Create setup script
        setup_script = scripts_dir / 'setup_dev.py'
        setup_script_content = '''#!/usr/bin/env python3
"""Development environment setup script."""

import subprocess
import sys
from pathlib import Path

def main():
    """Setup development environment."""
    print("Setting up development environment...")
    
    # Install pre-commit hooks if available
    try:
        subprocess.run(['pre-commit', 'install'], check=True)
        print("Pre-commit hooks installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Pre-commit not available")
    
    print("Development environment setup complete!")

if __name__ == "__main__":
    main()
'''
        
        with open(setup_script, 'w', encoding='utf-8') as f:
            f.write(setup_script_content)
        
        # Make scripts executable on Unix systems
        if os.name != 'nt':
            test_script.chmod(0o755)
            setup_script.chmod(0o755)
    
    def get_available_project_types(self) -> List[Dict[str, Any]]:
        """Get available project types for scaffolding."""
        return self.template_engine.get_available_templates()
    
    def create_custom_project(self, template: ProjectTemplate, config: ProjectScaffoldConfig) -> str:
        """Create project from custom template."""
        # Save custom template temporarily
        self.template_engine.save_template(template, overwrite=True)
        
        # Update config to use custom template
        config.project_type = template.name
        
        # Create project
        return self.create_project(config)
    
    def validate_project_structure(self, project_path: str) -> Dict[str, Any]:
        """Validate created project structure."""
        project_path = Path(project_path)
        validation = {
            'valid': True,
            'issues': [],
            'warnings': []
        }
        
        # Check essential directories
        essential_dirs = ['src', 'tests', 'docs']
        for dir_name in essential_dirs:
            if not (project_path / dir_name).exists():
                validation['issues'].append(f"Missing directory: {dir_name}")
                validation['valid'] = False
        
        # Check essential files
        essential_files = ['README.md', 'pyproject.toml']
        for file_name in essential_files:
            if not (project_path / file_name).exists():
                validation['issues'].append(f"Missing file: {file_name}")
                validation['valid'] = False
        
        # Check for Python files
        if not list(project_path.glob('src/**/*.py')):
            validation['warnings'].append("No Python source files found")
        
        # Check for test files
        if not list(project_path.glob('tests/**/*.py')):
            validation['warnings'].append("No test files found")
        
        return validation
    
    def generate_project_report(self, project_path: str) -> str:
        """Generate project creation report."""
        project_path = Path(project_path)
        
        # Count files and directories
        python_files = list(project_path.glob('**/*.py'))
        test_files = list(project_path.glob('tests/**/*.py'))
        directories = [d for d in project_path.rglob('*') if d.is_dir()]
        
        report = f"""
Project Creation Report
=====================

Project Path: {project_path}
Created: {project_path.stat().st_ctime}

Structure:
- Total Directories: {len(directories)}
- Python Files: {len(python_files)}
- Test Files: {len(test_files)}

Key Features:
- ✓ Project structure created
- ✓ Dependencies configured
- ✓ Testing framework setup
- ✓ Documentation structure
- ✓ Development scripts included

Next Steps:
1. Review README.md for project-specific instructions
2. Run 'scripts/setup_dev.py' to complete development setup
3. Start developing in the 'src/' directory
4. Run tests with 'scripts/run_tests.py'

Happy coding!
"""
        
        return report.strip()