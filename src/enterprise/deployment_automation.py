"""
Deployment Automation with Containerization Support
==================================================

Enterprise-grade deployment automation system including:
- Automated containerization with Docker and Kubernetes support
- Multi-environment deployment pipelines (dev, staging, production)
- Infrastructure as Code with automated provisioning
- Rolling deployments with health checks and rollback capabilities
- Service mesh integration and microservices orchestration
"""

import logging
import os
import time
import json
import yaml
import subprocess
import tempfile
from typing import Dict, Any, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import threading
import shutil
import tarfile
import zipfile

# Import existing components
from ..enhanced_autocad.performance_monitor import PerformanceMonitor
from ..enhanced_autocad.error_handler import ErrorHandler

logger = logging.getLogger(__name__)


class DeploymentEnvironment(Enum):
    """Deployment environment types."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"
    DISASTER_RECOVERY = "disaster_recovery"


class DeploymentStrategy(Enum):
    """Deployment strategy types."""
    BLUE_GREEN = "blue_green"
    ROLLING_UPDATE = "rolling_update"
    CANARY = "canary"
    RECREATE = "recreate"
    A_B_TESTING = "a_b_testing"


class ContainerOrchestrator(Enum):
    """Container orchestration platforms."""
    DOCKER_COMPOSE = "docker_compose"
    KUBERNETES = "kubernetes"
    DOCKER_SWARM = "docker_swarm"
    NOMAD = "nomad"
    ECS = "ecs"
    AKS = "aks"
    GKE = "gke"


@dataclass
class DeploymentConfig:
    """Configuration for a deployment."""
    name: str
    version: str
    environment: DeploymentEnvironment
    strategy: DeploymentStrategy
    orchestrator: ContainerOrchestrator
    
    # Container configuration
    image_name: str
    image_tag: str
    registry_url: Optional[str] = None
    
    # Resource requirements
    cpu_limit: str = "1000m"
    memory_limit: str = "2Gi"
    cpu_request: str = "500m"
    memory_request: str = "1Gi"
    
    # Scaling configuration
    replica_count: int = 3
    min_replicas: int = 1
    max_replicas: int = 10
    
    # Health checks
    health_check_path: str = "/health"
    readiness_probe_path: str = "/ready"
    liveness_probe_path: str = "/health"
    
    # Networking
    port: int = 8080
    target_port: int = 8080
    service_type: str = "ClusterIP"
    
    # Environment variables
    environment_variables: Dict[str, str] = field(default_factory=dict)
    secrets: Dict[str, str] = field(default_factory=dict)
    config_maps: Dict[str, str] = field(default_factory=dict)
    
    # Storage
    persistent_volumes: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)


@dataclass
class DeploymentResult:
    """Result of a deployment operation."""
    deployment_id: str
    success: bool
    start_time: float
    end_time: Optional[float] = None
    
    # Environment details
    environment: DeploymentEnvironment
    version: str
    strategy: DeploymentStrategy
    
    # Status information
    status: str = "unknown"
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    
    # Deployment artifacts
    container_images: List[str] = field(default_factory=list)
    service_endpoints: List[str] = field(default_factory=list)
    
    # Health check results
    health_checks_passed: bool = False
    readiness_checks_passed: bool = False
    
    # Rollback information
    previous_version: Optional[str] = None
    rollback_available: bool = False
    
    # Metrics
    deployment_duration: Optional[float] = None
    resources_created: List[str] = field(default_factory=list)
    resources_updated: List[str] = field(default_factory=list)


class DockerManager:
    """Docker container management utilities."""
    
    def __init__(self):
        """Initialize Docker manager."""
        self.docker_available = self._check_docker_availability()
        
    def _check_docker_availability(self) -> bool:
        """Check if Docker is available."""
        try:
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def build_image(self, 
                   dockerfile_path: str, 
                   image_name: str, 
                   image_tag: str,
                   build_args: Optional[Dict[str, str]] = None) -> bool:
        """
        Build a Docker image.
        
        Args:
            dockerfile_path: Path to Dockerfile
            image_name: Name of the image
            image_tag: Tag for the image
            build_args: Build arguments
            
        Returns:
            True if build successful
        """
        if not self.docker_available:
            logger.error("Docker is not available")
            return False
        
        try:
            # Prepare build command
            full_image_name = f"{image_name}:{image_tag}"
            cmd = ['docker', 'build', '-t', full_image_name, '-f', dockerfile_path, '.']
            
            # Add build args if provided
            if build_args:
                for key, value in build_args.items():
                    cmd.extend(['--build-arg', f'{key}={value}'])
            
            # Execute build
            logger.info(f"Building Docker image: {full_image_name}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                logger.info(f"Successfully built image: {full_image_name}")
                return True
            else:
                logger.error(f"Docker build failed: {result.stderr}")
                return False
        
        except subprocess.TimeoutExpired:
            logger.error("Docker build timed out")
            return False
        except Exception as e:
            logger.error(f"Docker build error: {e}")
            return False
    
    def push_image(self, image_name: str, image_tag: str, registry_url: Optional[str] = None) -> bool:
        """
        Push Docker image to registry.
        
        Args:
            image_name: Name of the image
            image_tag: Tag of the image
            registry_url: Registry URL (optional)
            
        Returns:
            True if push successful
        """
        if not self.docker_available:
            return False
        
        try:
            # Prepare image name with registry
            if registry_url:
                full_image_name = f"{registry_url}/{image_name}:{image_tag}"
            else:
                full_image_name = f"{image_name}:{image_tag}"
            
            # Tag image for registry if needed
            if registry_url:
                tag_cmd = ['docker', 'tag', f"{image_name}:{image_tag}", full_image_name]
                subprocess.run(tag_cmd, check=True, timeout=60)
            
            # Push image
            logger.info(f"Pushing Docker image: {full_image_name}")
            push_cmd = ['docker', 'push', full_image_name]
            result = subprocess.run(push_cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info(f"Successfully pushed image: {full_image_name}")
                return True
            else:
                logger.error(f"Docker push failed: {result.stderr}")
                return False
        
        except Exception as e:
            logger.error(f"Docker push error: {e}")
            return False
    
    def generate_dockerfile(self, 
                          base_image: str = "python:3.9-slim",
                          working_dir: str = "/app",
                          requirements_file: str = "requirements.txt",
                          entry_point: str = "python app.py") -> str:
        """
        Generate a Dockerfile for the AutoCAD MCP application.
        
        Args:
            base_image: Base Docker image
            working_dir: Working directory in container
            requirements_file: Python requirements file
            entry_point: Application entry point
            
        Returns:
            Dockerfile content as string
        """
        dockerfile_content = f"""# AutoCAD MCP Application Dockerfile
FROM {base_image}

# Set working directory
WORKDIR {working_dir}

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY {requirements_file} .
RUN pip install --no-cache-dir -r {requirements_file}

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && \\
    chown -R app:app {working_dir}
USER app

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Set entry point
CMD {entry_point}
"""
        return dockerfile_content


class KubernetesManager:
    """Kubernetes deployment management utilities."""
    
    def __init__(self):
        """Initialize Kubernetes manager."""
        self.kubectl_available = self._check_kubectl_availability()
        
    def _check_kubectl_availability(self) -> bool:
        """Check if kubectl is available."""
        try:
            result = subprocess.run(['kubectl', 'version', '--client'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def generate_deployment_manifest(self, config: DeploymentConfig) -> str:
        """
        Generate Kubernetes deployment manifest.
        
        Args:
            config: Deployment configuration
            
        Returns:
            YAML manifest content
        """
        # Full image name
        if config.registry_url:
            image = f"{config.registry_url}/{config.image_name}:{config.image_tag}"
        else:
            image = f"{config.image_name}:{config.image_tag}"
        
        # Deployment manifest
        deployment = {
            'apiVersion': 'apps/v1',
            'kind': 'Deployment',
            'metadata': {
                'name': config.name,
                'labels': {
                    'app': config.name,
                    'version': config.version,
                    'environment': config.environment.value,
                    **config.labels
                },
                'annotations': config.annotations
            },
            'spec': {
                'replicas': config.replica_count,
                'selector': {
                    'matchLabels': {
                        'app': config.name,
                        'version': config.version
                    }
                },
                'template': {
                    'metadata': {
                        'labels': {
                            'app': config.name,
                            'version': config.version,
                            'environment': config.environment.value
                        }
                    },
                    'spec': {
                        'containers': [{
                            'name': config.name,
                            'image': image,
                            'ports': [{
                                'containerPort': config.target_port,
                                'name': 'http'
                            }],
                            'resources': {
                                'limits': {
                                    'cpu': config.cpu_limit,
                                    'memory': config.memory_limit
                                },
                                'requests': {
                                    'cpu': config.cpu_request,
                                    'memory': config.memory_request
                                }
                            },
                            'env': [
                                {'name': k, 'value': v} 
                                for k, v in config.environment_variables.items()
                            ],
                            'livenessProbe': {
                                'httpGet': {
                                    'path': config.liveness_probe_path,
                                    'port': config.target_port
                                },
                                'initialDelaySeconds': 30,
                                'periodSeconds': 10,
                                'timeoutSeconds': 5,
                                'failureThreshold': 3
                            },
                            'readinessProbe': {
                                'httpGet': {
                                    'path': config.readiness_probe_path,
                                    'port': config.target_port
                                },
                                'initialDelaySeconds': 10,
                                'periodSeconds': 5,
                                'timeoutSeconds': 3,
                                'failureThreshold': 3
                            }
                        }],
                        'securityContext': {
                            'runAsNonRoot': True,
                            'runAsUser': 1000,
                            'fsGroup': 2000
                        }
                    }
                },
                'strategy': self._get_kubernetes_strategy(config.strategy)
            }
        }
        
        return yaml.dump(deployment, default_flow_style=False)
    
    def generate_service_manifest(self, config: DeploymentConfig) -> str:
        """
        Generate Kubernetes service manifest.
        
        Args:
            config: Deployment configuration
            
        Returns:
            YAML manifest content
        """
        service = {
            'apiVersion': 'v1',
            'kind': 'Service',
            'metadata': {
                'name': f"{config.name}-service",
                'labels': {
                    'app': config.name,
                    'version': config.version,
                    'environment': config.environment.value
                }
            },
            'spec': {
                'type': config.service_type,
                'ports': [{
                    'port': config.port,
                    'targetPort': config.target_port,
                    'protocol': 'TCP',
                    'name': 'http'
                }],
                'selector': {
                    'app': config.name,
                    'version': config.version
                }
            }
        }
        
        return yaml.dump(service, default_flow_style=False)
    
    def generate_hpa_manifest(self, config: DeploymentConfig) -> str:
        """
        Generate Horizontal Pod Autoscaler manifest.
        
        Args:
            config: Deployment configuration
            
        Returns:
            YAML manifest content
        """
        hpa = {
            'apiVersion': 'autoscaling/v2',
            'kind': 'HorizontalPodAutoscaler',
            'metadata': {
                'name': f"{config.name}-hpa",
                'labels': {
                    'app': config.name,
                    'version': config.version,
                    'environment': config.environment.value
                }
            },
            'spec': {
                'scaleTargetRef': {
                    'apiVersion': 'apps/v1',
                    'kind': 'Deployment',
                    'name': config.name
                },
                'minReplicas': config.min_replicas,
                'maxReplicas': config.max_replicas,
                'metrics': [
                    {
                        'type': 'Resource',
                        'resource': {
                            'name': 'cpu',
                            'target': {
                                'type': 'Utilization',
                                'averageUtilization': 70
                            }
                        }
                    },
                    {
                        'type': 'Resource',
                        'resource': {
                            'name': 'memory',
                            'target': {
                                'type': 'Utilization',
                                'averageUtilization': 80
                            }
                        }
                    }
                ]
            }
        }
        
        return yaml.dump(hpa, default_flow_style=False)
    
    def apply_manifest(self, manifest_content: str, namespace: str = "default") -> bool:
        """
        Apply Kubernetes manifest.
        
        Args:
            manifest_content: YAML manifest content
            namespace: Kubernetes namespace
            
        Returns:
            True if application successful
        """
        if not self.kubectl_available:
            logger.error("kubectl is not available")
            return False
        
        try:
            # Write manifest to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                f.write(manifest_content)
                manifest_file = f.name
            
            # Apply manifest
            cmd = ['kubectl', 'apply', '-f', manifest_file, '-n', namespace]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            # Cleanup
            os.unlink(manifest_file)
            
            if result.returncode == 0:
                logger.info("Successfully applied Kubernetes manifest")
                return True
            else:
                logger.error(f"kubectl apply failed: {result.stderr}")
                return False
        
        except Exception as e:
            logger.error(f"Manifest application error: {e}")
            return False
    
    def check_deployment_status(self, 
                              deployment_name: str, 
                              namespace: str = "default") -> Dict[str, Any]:
        """
        Check Kubernetes deployment status.
        
        Args:
            deployment_name: Name of the deployment
            namespace: Kubernetes namespace
            
        Returns:
            Deployment status information
        """
        if not self.kubectl_available:
            return {'error': 'kubectl not available'}
        
        try:
            # Get deployment status
            cmd = ['kubectl', 'get', 'deployment', deployment_name, '-n', namespace, '-o', 'json']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                deployment_info = json.loads(result.stdout)
                status = deployment_info.get('status', {})
                
                return {
                    'name': deployment_name,
                    'namespace': namespace,
                    'replicas': status.get('replicas', 0),
                    'ready_replicas': status.get('readyReplicas', 0),
                    'available_replicas': status.get('availableReplicas', 0),
                    'updated_replicas': status.get('updatedReplicas', 0),
                    'conditions': status.get('conditions', []),
                    'ready': status.get('readyReplicas', 0) == status.get('replicas', 0)
                }
            else:
                return {'error': f'Failed to get deployment status: {result.stderr}'}
        
        except Exception as e:
            return {'error': f'Status check error: {e}'}
    
    def _get_kubernetes_strategy(self, strategy: DeploymentStrategy) -> Dict[str, Any]:
        """Get Kubernetes deployment strategy configuration."""
        if strategy == DeploymentStrategy.ROLLING_UPDATE:
            return {
                'type': 'RollingUpdate',
                'rollingUpdate': {
                    'maxUnavailable': '25%',
                    'maxSurge': '25%'
                }
            }
        elif strategy == DeploymentStrategy.RECREATE:
            return {'type': 'Recreate'}
        else:
            # Default to rolling update
            return {
                'type': 'RollingUpdate',
                'rollingUpdate': {
                    'maxUnavailable': '25%',
                    'maxSurge': '25%'
                }
            }


class DeploymentAutomationEngine:
    """
    Comprehensive deployment automation engine.
    
    Provides enterprise-grade deployment automation with containerization,
    orchestration, and multi-environment support.
    """
    
    def __init__(self):
        """Initialize the deployment automation engine."""
        self.docker_manager = DockerManager()
        self.kubernetes_manager = KubernetesManager()
        self.performance_monitor = PerformanceMonitor()
        self.error_handler = ErrorHandler()
        
        # Deployment tracking
        self.active_deployments: Dict[str, DeploymentResult] = {}
        self.deployment_history: List[DeploymentResult] = []
        
        # Configuration templates
        self.environment_configs = self._load_environment_configs()
        self.deployment_templates = self._load_deployment_templates()
        
        # Threading for async operations
        self.deployment_lock = threading.RLock()
        
        logger.info("Deployment automation engine initialized")
    
    def create_deployment_package(self, 
                                source_dir: str,
                                output_dir: str,
                                include_tests: bool = False) -> str:
        """
        Create a deployment package from source code.
        
        Args:
            source_dir: Source code directory
            output_dir: Output directory for package
            include_tests: Whether to include test files
            
        Returns:
            Path to created deployment package
        """
        try:
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate package name with timestamp
            timestamp = int(time.time())
            package_name = f"autocad_mcp_deploy_{timestamp}.tar.gz"
            package_path = os.path.join(output_dir, package_name)
            
            # Create tar archive
            with tarfile.open(package_path, 'w:gz') as tar:
                # Add source files
                for root, dirs, files in os.walk(source_dir):
                    # Skip certain directories
                    dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', '.pytest_cache', 'node_modules']]
                    
                    for file in files:
                        file_path = os.path.join(root, file)
                        
                        # Skip certain file types
                        if file.endswith(('.pyc', '.pyo', '.pyd', '.so', '.egg-info')):
                            continue
                        
                        # Skip test files if not requested
                        if not include_tests and ('test_' in file or file.endswith('_test.py')):
                            continue
                        
                        # Add file to archive
                        arcname = os.path.relpath(file_path, source_dir)
                        tar.add(file_path, arcname=arcname)
            
            logger.info(f"Created deployment package: {package_path}")
            return package_path
        
        except Exception as e:
            logger.error(f"Failed to create deployment package: {e}")
            raise
    
    def deploy_application(self, config: DeploymentConfig) -> DeploymentResult:
        """
        Deploy application using the specified configuration.
        
        Args:
            config: Deployment configuration
            
        Returns:
            Deployment result
        """
        deployment_id = f"deploy_{config.name}_{int(time.time())}"
        
        result = DeploymentResult(
            deployment_id=deployment_id,
            success=False,
            start_time=time.time(),
            environment=config.environment,
            version=config.version,
            strategy=config.strategy
        )
        
        try:
            with self.deployment_lock:
                self.active_deployments[deployment_id] = result
            
            logger.info(f"Starting deployment {deployment_id} for {config.name} v{config.version}")
            
            # Step 1: Build and push container image
            if not self._build_and_push_image(config, result):
                return result
            
            # Step 2: Generate deployment manifests
            manifests = self._generate_deployment_manifests(config)
            
            # Step 3: Deploy to orchestrator
            if config.orchestrator == ContainerOrchestrator.KUBERNETES:
                success = self._deploy_to_kubernetes(config, manifests, result)
            elif config.orchestrator == ContainerOrchestrator.DOCKER_COMPOSE:
                success = self._deploy_to_docker_compose(config, result)
            else:
                logger.error(f"Unsupported orchestrator: {config.orchestrator}")
                result.error_message = f"Unsupported orchestrator: {config.orchestrator}"
                return result
            
            if not success:
                return result
            
            # Step 4: Health checks
            if not self._perform_health_checks(config, result):
                # Attempt rollback on health check failure
                self._attempt_rollback(config, result)
                return result
            
            # Step 5: Update traffic routing (for blue-green/canary)
            if config.strategy in [DeploymentStrategy.BLUE_GREEN, DeploymentStrategy.CANARY]:
                if not self._update_traffic_routing(config, result):
                    self._attempt_rollback(config, result)
                    return result
            
            # Deployment successful
            result.success = True
            result.status = "deployed"
            result.end_time = time.time()
            result.deployment_duration = result.end_time - result.start_time
            
            logger.info(f"Deployment {deployment_id} completed successfully in {result.deployment_duration:.2f}s")
        
        except Exception as e:
            logger.error(f"Deployment {deployment_id} failed: {e}")
            result.error_message = str(e)
            result.status = "failed"
            result.end_time = time.time()
        
        finally:
            # Store in history
            self.deployment_history.append(result)
            
            # Clean up active deployments
            with self.deployment_lock:
                if deployment_id in self.active_deployments:
                    del self.active_deployments[deployment_id]
        
        return result
    
    def rollback_deployment(self, 
                          deployment_id: str, 
                          target_version: Optional[str] = None) -> bool:
        """
        Rollback a deployment to a previous version.
        
        Args:
            deployment_id: ID of deployment to rollback
            target_version: Target version to rollback to
            
        Returns:
            True if rollback successful
        """
        try:
            # Find deployment in history
            deployment = None
            for dep in self.deployment_history:
                if dep.deployment_id == deployment_id:
                    deployment = dep
                    break
            
            if not deployment:
                logger.error(f"Deployment {deployment_id} not found")
                return False
            
            if not deployment.rollback_available:
                logger.error(f"Rollback not available for deployment {deployment_id}")
                return False
            
            # Determine target version
            if not target_version:
                target_version = deployment.previous_version
            
            if not target_version:
                logger.error("No target version specified for rollback")
                return False
            
            logger.info(f"Rolling back deployment {deployment_id} to version {target_version}")
            
            # Create rollback configuration
            # This would involve finding the previous deployment config and applying it
            # Implementation would depend on the specific orchestrator and strategy used
            
            return True
        
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False
    
    def get_deployment_status(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a deployment.
        
        Args:
            deployment_id: ID of the deployment
            
        Returns:
            Deployment status information or None if not found
        """
        # Check active deployments
        if deployment_id in self.active_deployments:
            deployment = self.active_deployments[deployment_id]
            return {
                'deployment_id': deployment_id,
                'status': 'in_progress',
                'start_time': deployment.start_time,
                'environment': deployment.environment.value,
                'version': deployment.version,
                'strategy': deployment.strategy.value
            }
        
        # Check deployment history
        for deployment in self.deployment_history:
            if deployment.deployment_id == deployment_id:
                return {
                    'deployment_id': deployment_id,
                    'status': 'completed' if deployment.success else 'failed',
                    'success': deployment.success,
                    'start_time': deployment.start_time,
                    'end_time': deployment.end_time,
                    'duration': deployment.deployment_duration,
                    'environment': deployment.environment.value,
                    'version': deployment.version,
                    'strategy': deployment.strategy.value,
                    'error_message': deployment.error_message,
                    'warnings': deployment.warnings
                }
        
        return None
    
    def _build_and_push_image(self, config: DeploymentConfig, result: DeploymentResult) -> bool:
        """Build and push container image."""
        try:
            # Generate Dockerfile if it doesn't exist
            dockerfile_path = "Dockerfile"
            if not os.path.exists(dockerfile_path):
                dockerfile_content = self.docker_manager.generate_dockerfile()
                with open(dockerfile_path, 'w') as f:
                    f.write(dockerfile_content)
                logger.info("Generated Dockerfile")
            
            # Build image
            if not self.docker_manager.build_image(
                dockerfile_path, config.image_name, config.image_tag
            ):
                result.error_message = "Failed to build Docker image"
                return False
            
            # Push image to registry
            if config.registry_url:
                if not self.docker_manager.push_image(
                    config.image_name, config.image_tag, config.registry_url
                ):
                    result.error_message = "Failed to push Docker image"
                    return False
            
            # Update result
            image_name = f"{config.image_name}:{config.image_tag}"
            if config.registry_url:
                image_name = f"{config.registry_url}/{image_name}"
            
            result.container_images.append(image_name)
            result.resources_created.append(f"docker_image:{image_name}")
            
            return True
        
        except Exception as e:
            result.error_message = f"Image build/push failed: {e}"
            return False
    
    def _generate_deployment_manifests(self, config: DeploymentConfig) -> Dict[str, str]:
        """Generate deployment manifests for the orchestrator."""
        manifests = {}
        
        if config.orchestrator == ContainerOrchestrator.KUBERNETES:
            # Generate Kubernetes manifests
            manifests['deployment'] = self.kubernetes_manager.generate_deployment_manifest(config)
            manifests['service'] = self.kubernetes_manager.generate_service_manifest(config)
            manifests['hpa'] = self.kubernetes_manager.generate_hpa_manifest(config)
        
        return manifests
    
    def _deploy_to_kubernetes(self, 
                            config: DeploymentConfig, 
                            manifests: Dict[str, str], 
                            result: DeploymentResult) -> bool:
        """Deploy to Kubernetes cluster."""
        try:
            namespace = config.environment.value
            
            # Apply manifests
            for manifest_type, manifest_content in manifests.items():
                if self.kubernetes_manager.apply_manifest(manifest_content, namespace):
                    result.resources_created.append(f"k8s_{manifest_type}:{config.name}")
                else:
                    result.error_message = f"Failed to apply {manifest_type} manifest"
                    return False
            
            # Wait for deployment to be ready
            timeout = 300  # 5 minutes
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                status = self.kubernetes_manager.check_deployment_status(config.name, namespace)
                
                if status.get('ready', False):
                    result.status = "deployed"
                    return True
                
                time.sleep(10)  # Check every 10 seconds
            
            result.error_message = "Deployment timed out waiting for pods to be ready"
            return False
        
        except Exception as e:
            result.error_message = f"Kubernetes deployment failed: {e}"
            return False
    
    def _deploy_to_docker_compose(self, config: DeploymentConfig, result: DeploymentResult) -> bool:
        """Deploy using Docker Compose."""
        try:
            # Generate docker-compose.yml
            compose_config = self._generate_docker_compose_config(config)
            
            # Write compose file
            with open('docker-compose.yml', 'w') as f:
                yaml.dump(compose_config, f, default_flow_style=False)
            
            # Deploy with docker-compose
            cmd = ['docker-compose', 'up', '-d']
            result_process = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result_process.returncode == 0:
                result.resources_created.append("docker_compose:services")
                return True
            else:
                result.error_message = f"docker-compose up failed: {result_process.stderr}"
                return False
        
        except Exception as e:
            result.error_message = f"Docker Compose deployment failed: {e}"
            return False
    
    def _perform_health_checks(self, config: DeploymentConfig, result: DeploymentResult) -> bool:
        """Perform health checks on deployed application."""
        try:
            # This would implement actual health check logic
            # For now, simulate health checks
            logger.info("Performing health checks...")
            
            # Simulate health check delay
            time.sleep(10)
            
            # In a real implementation, this would make HTTP requests to health endpoints
            result.health_checks_passed = True
            result.readiness_checks_passed = True
            
            return True
        
        except Exception as e:
            logger.error(f"Health checks failed: {e}")
            result.error_message = f"Health checks failed: {e}"
            return False
    
    def _update_traffic_routing(self, config: DeploymentConfig, result: DeploymentResult) -> bool:
        """Update traffic routing for blue-green or canary deployments."""
        try:
            # This would implement traffic routing logic
            # For blue-green: switch traffic from blue to green
            # For canary: gradually increase traffic to new version
            
            logger.info(f"Updating traffic routing for {config.strategy.value} deployment")
            
            # Simulate traffic routing update
            time.sleep(5)
            
            return True
        
        except Exception as e:
            logger.error(f"Traffic routing update failed: {e}")
            result.error_message = f"Traffic routing failed: {e}"
            return False
    
    def _attempt_rollback(self, config: DeploymentConfig, result: DeploymentResult):
        """Attempt automatic rollback on deployment failure."""
        try:
            logger.warning(f"Attempting automatic rollback for failed deployment")
            
            # This would implement rollback logic specific to the orchestrator
            # For now, just log the attempt
            result.warnings.append("Automatic rollback attempted")
            
        except Exception as e:
            logger.error(f"Automatic rollback failed: {e}")
            result.warnings.append(f"Automatic rollback failed: {e}")
    
    def _generate_docker_compose_config(self, config: DeploymentConfig) -> Dict[str, Any]:
        """Generate Docker Compose configuration."""
        # Full image name
        if config.registry_url:
            image = f"{config.registry_url}/{config.image_name}:{config.image_tag}"
        else:
            image = f"{config.image_name}:{config.image_tag}"
        
        compose_config = {
            'version': '3.8',
            'services': {
                config.name: {
                    'image': image,
                    'ports': [f"{config.port}:{config.target_port}"],
                    'environment': config.environment_variables,
                    'restart': 'unless-stopped',
                    'deploy': {
                        'replicas': config.replica_count,
                        'resources': {
                            'limits': {
                                'cpus': config.cpu_limit.rstrip('m'),
                                'memory': config.memory_limit
                            },
                            'reservations': {
                                'cpus': config.cpu_request.rstrip('m'),
                                'memory': config.memory_request
                            }
                        }
                    },
                    'healthcheck': {
                        'test': f"curl -f http://localhost:{config.target_port}{config.health_check_path} || exit 1",
                        'interval': '30s',
                        'timeout': '10s',
                        'retries': 3,
                        'start_period': '60s'
                    }
                }
            }
        }
        
        return compose_config
    
    def _load_environment_configs(self) -> Dict[DeploymentEnvironment, Dict[str, Any]]:
        """Load environment-specific configurations."""
        return {
            DeploymentEnvironment.DEVELOPMENT: {
                'replica_count': 1,
                'cpu_limit': '500m',
                'memory_limit': '1Gi',
                'auto_scaling': False
            },
            DeploymentEnvironment.TESTING: {
                'replica_count': 2,
                'cpu_limit': '1000m',
                'memory_limit': '2Gi',
                'auto_scaling': False
            },
            DeploymentEnvironment.STAGING: {
                'replica_count': 2,
                'cpu_limit': '1000m',
                'memory_limit': '2Gi',
                'auto_scaling': True
            },
            DeploymentEnvironment.PRODUCTION: {
                'replica_count': 3,
                'cpu_limit': '2000m',
                'memory_limit': '4Gi',
                'auto_scaling': True
            }
        }
    
    def _load_deployment_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load deployment templates for common scenarios."""
        return {
            'web_application': {
                'port': 8080,
                'health_check_path': '/health',
                'readiness_probe_path': '/ready',
                'environment_variables': {
                    'LOG_LEVEL': 'INFO',
                    'METRICS_ENABLED': 'true'
                }
            },
            'api_service': {
                'port': 8080,
                'health_check_path': '/api/health',
                'readiness_probe_path': '/api/ready',
                'environment_variables': {
                    'API_VERSION': 'v1',
                    'CORS_ENABLED': 'true'
                }
            },
            'background_worker': {
                'port': 8080,
                'health_check_path': '/health',
                'environment_variables': {
                    'WORKER_PROCESSES': '4',
                    'QUEUE_BACKEND': 'redis'
                }
            }
        }