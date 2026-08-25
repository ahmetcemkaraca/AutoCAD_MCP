"""
CI/CD Integration for AutoCAD Testing.

Provides tools for integrating AutoCAD automation tests with CI/CD pipelines,
including GitHub Actions, Azure DevOps, and Jenkins.
"""

import os
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CIConfiguration:
    """CI/CD configuration settings."""
    provider: str  # 'github', 'azure', 'jenkins'
    project_path: str
    test_commands: List[str]
    mock_mode: bool = True
    timeout_minutes: int = 30
    python_version: str = "3.12"
    dependencies: List[str] = None
    environment_variables: Dict[str, str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = [
                "pytest>=8.0.0",
                "pytest-cov>=4.0.0",
                "pytest-html>=4.0.0",
                "psutil>=5.9.0"
            ]
        if self.environment_variables is None:
            self.environment_variables = {}


class CIIntegration:
    """CI/CD integration tools for AutoCAD testing."""
    
    def __init__(self):
        self.supported_providers = {
            'github': self._generate_github_actions,
            'azure': self._generate_azure_pipelines,
            'jenkins': self._generate_jenkins_pipeline
        }
    
    def setup_ci_integration(self, project_path: str, provider: str, 
                           config: Optional[CIConfiguration] = None) -> str:
        """Set up CI/CD integration for AutoCAD project."""
        project_path = Path(project_path)
        
        if provider not in self.supported_providers:
            raise ValueError(f"Unsupported CI provider: {provider}. "
                           f"Supported: {list(self.supported_providers.keys())}")
        
        # Use default config if none provided
        if config is None:
            config = CIConfiguration(
                provider=provider,
                project_path=str(project_path),
                test_commands=[
                    "python -m pytest tests/ --cov=src --cov-report=html --cov-report=xml",
                    "python -m pytest tests/generated/ --html=test-report.html"
                ]
            )
        
        # Generate CI configuration
        generator = self.supported_providers[provider]
        config_content = generator(config)
        
        # Write configuration file
        config_file = self._write_config_file(project_path, provider, config_content)
        
        # Create additional CI support files
        self._create_ci_support_files(project_path, config)
        
        logger.info(f"CI/CD integration set up for {provider} at {config_file}")
        return str(config_file)
    
    def _generate_github_actions(self, config: CIConfiguration) -> str:
        """Generate GitHub Actions workflow."""
        workflow = {
            'name': 'AutoCAD MCP Tests',
            'on': {
                'push': {'branches': ['main', 'develop']},
                'pull_request': {'branches': ['main']}
            },
            'jobs': {
                'test': {
                    'runs-on': 'windows-latest',  # AutoCAD requires Windows
                    'timeout-minutes': config.timeout_minutes,
                    'steps': [
                        {
                            'name': 'Checkout code',
                            'uses': 'actions/checkout@v4'
                        },
                        {
                            'name': 'Set up Python',
                            'uses': 'actions/setup-python@v4',
                            'with': {
                                'python-version': config.python_version
                            }
                        },
                        {
                            'name': 'Install Poetry',
                            'uses': 'snok/install-poetry@v1',
                            'with': {
                                'virtualenvs-create': True,
                                'virtualenvs-in-project': True
                            }
                        },
                        {
                            'name': 'Install dependencies',
                            'run': 'poetry install'
                        },
                        {
                            'name': 'Run linting',
                            'run': 'poetry run ruff check . && poetry run black --check .'
                        },
                        {
                            'name': 'Run type checking',
                            'run': 'poetry run mypy src/'
                        },
                        {
                            'name': 'Run unit tests (mock mode)',
                            'run': 'poetry run python -m pytest tests/ --cov=src --cov-report=xml',
                            'env': dict(config.environment_variables, **{
                                'AUTOCAD_MOCK_MODE': 'true',
                                'PYTHONPATH': '.'
                            })
                        },
                        {
                            'name': 'Run generated tests',
                            'run': 'poetry run python -m pytest tests/generated/ --html=test-report.html',
                            'env': dict(config.environment_variables, **{
                                'AUTOCAD_MOCK_MODE': 'true'
                            })
                        },
                        {
                            'name': 'Upload test results',
                            'uses': 'actions/upload-artifact@v3',
                            'if': 'always()',
                            'with': {
                                'name': 'test-results',
                                'path': '|\\n          test-report.html\\n          coverage.xml\\n          htmlcov/'
                            }
                        },
                        {
                            'name': 'Upload coverage to Codecov',
                            'uses': 'codecov/codecov-action@v3',
                            'with': {
                                'file': './coverage.xml',
                                'flags': 'unittests',
                                'name': 'autocad-mcp-coverage'
                            }
                        }
                    ]
                }
            }
        }
        
        # Add AutoCAD integration test job (optional, requires self-hosted runner)
        if not config.mock_mode:
            workflow['jobs']['integration-test'] = {
                'runs-on': 'self-hosted',
                'needs': 'test',
                'if': "github.event_name == 'push' && github.ref == 'refs/heads/main'",
                'steps': [
                    {'name': 'Checkout code', 'uses': 'actions/checkout@v4'},
                    {
                        'name': 'Run integration tests with AutoCAD',
                        'run': 'poetry run python -m pytest tests/integration/ --autocad-real',
                        'env': dict(config.environment_variables, **{
                            'AUTOCAD_MOCK_MODE': 'false'
                        })
                    }
                ]
            }
        
        return yaml.dump(workflow, default_flow_style=False, sort_keys=False)
    
    def _generate_azure_pipelines(self, config: CIConfiguration) -> str:
        """Generate Azure DevOps pipeline."""
        pipeline = {
            'trigger': ['main', 'develop'],
            'pr': ['main'],
            'pool': {
                'vmImage': 'windows-latest'
            },
            'variables': {
                'python.version': config.python_version,
                **config.environment_variables
            },
            'stages': [
                {
                    'stage': 'Test',
                    'displayName': 'Test AutoCAD MCP',
                    'jobs': [
                        {
                            'job': 'TestJob',
                            'displayName': 'Run Tests',
                            'timeoutInMinutes': config.timeout_minutes,
                            'steps': [
                                {
                                    'task': 'UsePythonVersion@0',
                                    'inputs': {
                                        'versionSpec': '$(python.version)',
                                        'addToPath': True
                                    },
                                    'displayName': 'Use Python $(python.version)'
                                },
                                {
                                    'script': 'pip install poetry',
                                    'displayName': 'Install Poetry'
                                },
                                {
                                    'script': 'poetry install',
                                    'displayName': 'Install dependencies'
                                },
                                {
                                    'script': 'poetry run ruff check . && poetry run black --check .',
                                    'displayName': 'Run linting'
                                },
                                {
                                    'script': 'poetry run mypy src/',
                                    'displayName': 'Run type checking'
                                },
                                {
                                    'script': 'poetry run python -m pytest tests/ --cov=src --cov-report=xml --junitxml=test-results.xml',
                                    'displayName': 'Run unit tests',
                                    'env': {
                                        'AUTOCAD_MOCK_MODE': 'true'
                                    }
                                },
                                {
                                    'task': 'PublishTestResults@2',
                                    'inputs': {
                                        'testResultsFormat': 'JUnit',
                                        'testResultsFiles': 'test-results.xml',
                                        'testRunTitle': 'AutoCAD MCP Tests'
                                    },
                                    'condition': 'succeededOrFailed()'
                                },
                                {
                                    'task': 'PublishCodeCoverageResults@1',
                                    'inputs': {
                                        'codeCoverageTool': 'Cobertura',
                                        'summaryFileLocation': 'coverage.xml'
                                    },
                                    'condition': 'succeededOrFailed()'
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        return yaml.dump(pipeline, default_flow_style=False, sort_keys=False)
    
    def _generate_jenkins_pipeline(self, config: CIConfiguration) -> str:
        """Generate Jenkins pipeline (Jenkinsfile)."""
        jenkinsfile = f'''pipeline {{
    agent {{
        label 'windows'  // AutoCAD requires Windows
    }}
    
    environment {{
        PYTHON_VERSION = '{config.python_version}'
        AUTOCAD_MOCK_MODE = 'true'
        {self._format_env_vars(config.environment_variables)}
    }}
    
    stages {{
        stage('Checkout') {{
            steps {{
                checkout scm
            }}
        }}
        
        stage('Setup Python') {{
            steps {{
                bat """
                    python -m pip install --upgrade pip
                    pip install poetry
                    poetry install
                """
            }}
        }}
        
        stage('Lint') {{
            steps {{
                bat """
                    poetry run ruff check .
                    poetry run black --check .
                    poetry run mypy src/
                """
            }}
        }}
        
        stage('Test') {{
            steps {{
                bat """
                    poetry run python -m pytest tests/ --cov=src --cov-report=xml --junitxml=test-results.xml
                    poetry run python -m pytest tests/generated/ --html=test-report.html
                """
            }}
            post {{
                always {{
                    publishTestResults testResultsPattern: 'test-results.xml'
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: '.',
                        reportFiles: 'test-report.html',
                        reportName: 'Test Report'
                    ])
                }}
            }}
        }}
        
        stage('Coverage') {{
            steps {{
                bat """
                    poetry run coverage html
                """
            }}
            post {{
                always {{
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'htmlcov',
                        reportFiles: 'index.html',
                        reportName: 'Coverage Report'
                    ])
                }}
            }}
        }}
    }}
    
    post {{
        always {{
            cleanWs()
        }}
        failure {{
            emailext (
                subject: "Build Failed: ${{env.JOB_NAME}} - ${{env.BUILD_NUMBER}}",
                body: "The AutoCAD MCP build has failed. Please check the console output.",
                to: "${{env.CHANGE_AUTHOR_EMAIL}}"
            )
        }}
    }}
}}'''
        
        return jenkinsfile
    
    def _format_env_vars(self, env_vars: Dict[str, str]) -> str:
        """Format environment variables for Jenkins."""
        if not env_vars:
            return ""
        
        formatted = []
        for key, value in env_vars.items():
            formatted.append(f"        {key} = '{value}'")
        
        return "\\n".join(formatted)
    
    def _write_config_file(self, project_path: Path, provider: str, content: str) -> Path:
        """Write CI configuration file to appropriate location."""
        if provider == 'github':
            config_dir = project_path / '.github' / 'workflows'
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / 'autocad-tests.yml'
        
        elif provider == 'azure':
            config_file = project_path / 'azure-pipelines.yml'
        
        elif provider == 'jenkins':
            config_file = project_path / 'Jenkinsfile'
        
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return config_file
    
    def _create_ci_support_files(self, project_path: Path, config: CIConfiguration):
        """Create additional CI support files."""
        # Create pytest configuration
        pytest_ini = f'''[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --strict-config
    --verbose
    --tb=short
markers =
    unit: Unit tests
    integration: Integration tests with AutoCAD
    performance: Performance tests
    mock: Tests using mock AutoCAD
    real_autocad: Tests requiring real AutoCAD connection
'''
        
        with open(project_path / 'pytest.ini', 'w', encoding='utf-8') as f:
            f.write(pytest_ini)
        
        # Create coverage configuration
        coverage_config = '''[run]
source = src
omit = 
    */tests/*
    */test_*
    */__pycache__/*
    */venv/*
    */env/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    @abstractmethod

[html]
directory = htmlcov
'''
        
        with open(project_path / '.coveragerc', 'w', encoding='utf-8') as f:
            f.write(coverage_config)
        
        # Create test requirements file
        requirements = "\\n".join(config.dependencies)
        with open(project_path / 'test-requirements.txt', 'w', encoding='utf-8') as f:
            f.write(requirements)
        
        # Create CI test runner script
        test_runner = '''#!/usr/bin/env python3
"""
CI Test Runner for AutoCAD MCP.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_command(command, description):
    """Run a command and log results."""
    logger.info(f"Running: {description}")
    logger.info(f"Command: {command}")
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        logger.info(f"✓ {description} completed successfully")
        if result.stdout:
            logger.info(f"Output: {result.stdout}")
    else:
        logger.error(f"✗ {description} failed")
        logger.error(f"Error: {result.stderr}")
        return False
    
    return True

def main():
    """Run all CI tests."""
    # Set environment for mock mode
    os.environ['AUTOCAD_MOCK_MODE'] = 'true'
    os.environ['PYTHONPATH'] = '.'
    
    logger.info("Starting AutoCAD MCP CI Test Suite")
    
    # Test commands
    commands = [
        ("ruff check .", "Code linting"),
        ("black --check .", "Code formatting check"),
        ("mypy src/", "Type checking"),
        ("python -m pytest tests/ --cov=src --cov-report=xml", "Unit tests"),
        ("python -m pytest tests/generated/ --html=test-report.html", "Generated tests")
    ]
    
    all_passed = True
    for command, description in commands:
        if not run_command(command, description):
            all_passed = False
    
    if all_passed:
        logger.info("🎉 All tests passed!")
        sys.exit(0)
    else:
        logger.error("❌ Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
        
        test_runner_path = project_path / 'run_ci_tests.py'
        with open(test_runner_path, 'w', encoding='utf-8') as f:
            f.write(test_runner)
        
        # Make executable on Unix systems
        if os.name != 'nt':
            test_runner_path.chmod(0o755)
        
        logger.info("Created CI support files: pytest.ini, .coveragerc, test-requirements.txt, run_ci_tests.py")
    
    def validate_ci_setup(self, project_path: str, provider: str) -> Dict[str, Any]:
        """Validate CI/CD setup and configuration."""
        project_path = Path(project_path)
        validation_results = {
            'valid': True,
            'issues': [],
            'warnings': [],
            'provider': provider
        }
        
        # Check for required files
        required_files = {
            'github': ['.github/workflows/autocad-tests.yml'],
            'azure': ['azure-pipelines.yml'],
            'jenkins': ['Jenkinsfile']
        }
        
        if provider in required_files:
            for file_path in required_files[provider]:
                full_path = project_path / file_path
                if not full_path.exists():
                    validation_results['issues'].append(f"Missing CI config file: {file_path}")
                    validation_results['valid'] = False
        
        # Check for test directories
        test_dirs = ['tests', 'tests/generated']
        for test_dir in test_dirs:
            if not (project_path / test_dir).exists():
                validation_results['warnings'].append(f"Test directory not found: {test_dir}")
        
        # Check for Python files
        if not list(project_path.glob('src/**/*.py')):
            validation_results['issues'].append("No Python source files found in src/")
            validation_results['valid'] = False
        
        # Check for CI support files
        support_files = ['pytest.ini', '.coveragerc', 'test-requirements.txt']
        for support_file in support_files:
            if not (project_path / support_file).exists():
                validation_results['warnings'].append(f"Missing CI support file: {support_file}")
        
        return validation_results
    
    def update_ci_config(self, project_path: str, provider: str, updates: Dict[str, Any]) -> str:
        """Update existing CI configuration with new settings."""
        project_path = Path(project_path)
        
        # Load existing configuration
        if provider == 'github':
            config_file = project_path / '.github' / 'workflows' / 'autocad-tests.yml'
        elif provider == 'azure':
            config_file = project_path / 'azure-pipelines.yml'
        elif provider == 'jenkins':
            config_file = project_path / 'Jenkinsfile'
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        
        if not config_file.exists():
            raise FileNotFoundError(f"CI configuration file not found: {config_file}")
        
        # For now, backup and regenerate - could be enhanced for incremental updates
        backup_file = config_file.with_suffix(config_file.suffix + '.backup')
        config_file.rename(backup_file)
        
        logger.info(f"Backed up existing config to {backup_file}")
        
        # Create new configuration with updates
        current_config = CIConfiguration(
            provider=provider,
            project_path=str(project_path),
            test_commands=updates.get('test_commands', [
                "python -m pytest tests/ --cov=src --cov-report=xml",
                "python -m pytest tests/generated/ --html=test-report.html"
            ]),
            **{k: v for k, v in updates.items() if k != 'test_commands'}
        )
        
        # Generate new configuration
        generator = self.supported_providers[provider]
        new_content = generator(current_config)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        logger.info(f"Updated CI configuration: {config_file}")
        return str(config_file)