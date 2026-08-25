"""
Lazy loading framework for optional dependencies.

This module provides a standardized way to handle optional dependencies
across the AutoCAD MCP platform, with graceful fallbacks and comprehensive
error handling.
"""

import logging
import importlib
from typing import Any, Callable, Dict, Optional, Union
import functools

logger = logging.getLogger(__name__)


class LazyLoader:
    """
    Lazy loader for optional dependencies with fallback support.
    
    This class provides a standardized way to handle optional dependencies
    that may not be available in all deployment environments.
    """
    
    def __init__(self, module_name: str, fallback_factory: Optional[Callable] = None, 
                 package: Optional[str] = None):
        """
        Initialize lazy loader.
        
        Args:
            module_name: Name of the module to load
            fallback_factory: Optional factory function for fallback object
            package: Package name for relative imports
        """
        self.module_name = module_name
        self.fallback_factory = fallback_factory
        self.package = package
        self._module = None
        self._attempted_load = False
        self._load_error = None
    
    def __getattr__(self, name: str) -> Any:
        """Get attribute from the lazily loaded module."""
        if not self._attempted_load:
            self._load_module()
        
        if self._module is not None:
            try:
                return getattr(self._module, name)
            except AttributeError:
                if self.fallback_factory:
                    fallback = self.fallback_factory()
                    if hasattr(fallback, name):
                        return getattr(fallback, name)
                raise AttributeError(f"Module '{self.module_name}' has no attribute '{name}'")
        
        # Module not available, try fallback
        if self.fallback_factory:
            fallback = self.fallback_factory()
            if hasattr(fallback, name):
                logger.warning(f"Using fallback for {self.module_name}.{name}")
                return getattr(fallback, name)
        
        raise AttributeError(
            f"Optional dependency '{self.module_name}' not available and no fallback provided. "
            f"Install with: pip install {self.module_name}"
        )
    
    def _load_module(self):
        """Attempt to load the module."""
        self._attempted_load = True
        try:
            self._module = importlib.import_module(self.module_name, self.package)
            logger.debug(f"Successfully loaded optional dependency: {self.module_name}")
        except ImportError as e:
            self._load_error = e
            logger.info(f"Optional dependency '{self.module_name}' not available: {e}")
            if self.fallback_factory:
                logger.info(f"Fallback available for {self.module_name}")
            else:
                logger.warning(f"No fallback available for {self.module_name}")
    
    def is_available(self) -> bool:
        """Check if the module is available."""
        if not self._attempted_load:
            self._load_module()
        return self._module is not None
    
    def get_error(self) -> Optional[ImportError]:
        """Get the import error if module loading failed."""
        if not self._attempted_load:
            self._load_module()
        return self._load_error


def lazy_import(module_name: str, fallback_factory: Optional[Callable] = None,
                package: Optional[str] = None) -> LazyLoader:
    """
    Create a lazy loader for an optional dependency.
    
    Args:
        module_name: Name of the module to load
        fallback_factory: Optional factory function for fallback object  
        package: Package name for relative imports
        
    Returns:
        LazyLoader instance
        
    Example:
        >>> psutil = lazy_import('psutil', fallback_factory=lambda: MockPsutil())
        >>> cpu_percent = psutil.cpu_percent()  # Uses real psutil or fallback
    """
    return LazyLoader(module_name, fallback_factory, package)


class MockPsutil:
    """Mock implementation of psutil for fallback."""
    
    def cpu_percent(self, interval: Optional[float] = None) -> float:
        """Mock CPU percentage."""
        logger.debug("Using mock psutil.cpu_percent()")
        return 0.0
    
    def virtual_memory(self):
        """Mock virtual memory info."""
        logger.debug("Using mock psutil.virtual_memory()")
        return type('MockMemory', (), {
            'total': 8 * 1024 * 1024 * 1024,  # 8GB
            'available': 4 * 1024 * 1024 * 1024,  # 4GB
            'percent': 50.0,
            'used': 4 * 1024 * 1024 * 1024
        })()
    
    def disk_usage(self, path: str):
        """Mock disk usage info."""
        logger.debug(f"Using mock psutil.disk_usage({path})")
        return type('MockDiskUsage', (), {
            'total': 100 * 1024 * 1024 * 1024,  # 100GB
            'used': 50 * 1024 * 1024 * 1024,    # 50GB
            'free': 50 * 1024 * 1024 * 1024     # 50GB
        })()


class MockJinja2:
    """Mock implementation of Jinja2 for fallback."""
    
    class Template:
        def __init__(self, template_string: str):
            self.template_string = template_string
        
        def render(self, **kwargs) -> str:
            """Simple string substitution fallback."""
            logger.debug("Using mock Jinja2 template rendering")
            result = self.template_string
            for key, value in kwargs.items():
                result = result.replace(f"{{{{{key}}}}}", str(value))
            return result
    
    def Environment(self, **kwargs):
        """Mock Jinja2 Environment."""
        return self
    
    def from_string(self, template_string: str):
        """Create template from string."""
        return self.Template(template_string)


# Pre-configured lazy loaders for common optional dependencies
psutil = lazy_import('psutil', fallback_factory=MockPsutil)
jinja2 = lazy_import('jinja2', fallback_factory=MockJinja2)

# Cryptography for enterprise security features
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    HAS_CRYPTOGRAPHY = True
    cryptography_available = True
except ImportError:
    HAS_CRYPTOGRAPHY = False
    cryptography_available = False
    
    # Mock cryptography classes
    class MockFernet:
        def __init__(self, key):
            self.key = key
        
        def encrypt(self, data: bytes) -> bytes:
            logger.warning("Cryptography not available, returning unencrypted data")
            return data
        
        def decrypt(self, data: bytes) -> bytes:
            logger.warning("Cryptography not available, returning data as-is") 
            return data
    
    Fernet = MockFernet
    hashes = None
    PBKDF2HMAC = None


def check_dependencies() -> Dict[str, Dict[str, Union[bool, str]]]:
    """
    Check the availability of all optional dependencies.
    
    Returns:
        Dictionary with dependency status information
    """
    dependencies = {
        'psutil': psutil,
        'jinja2': jinja2,
    }
    
    status = {}
    for name, loader in dependencies.items():
        status[name] = {
            'available': loader.is_available(),
            'error': str(loader.get_error()) if loader.get_error() else None
        }
    
    # Check cryptography separately
    status['cryptography'] = {
        'available': HAS_CRYPTOGRAPHY,
        'error': None if HAS_CRYPTOGRAPHY else "cryptography package not installed"
    }
    
    return status


if __name__ == "__main__":
    # Test the lazy loading system
    print("Testing lazy loading framework...")
    
    # Check all dependencies
    dep_status = check_dependencies()
    
    for name, info in dep_status.items():
        status_icon = "✅" if info['available'] else "❌"
        print(f"{status_icon} {name}: {'Available' if info['available'] else 'Not available'}")
        if info['error']:
            print(f"   Error: {info['error']}")
    
    # Test psutil fallback
    print(f"\nTesting psutil: CPU = {psutil.cpu_percent()}%")
    memory = psutil.virtual_memory()
    print(f"Memory: {memory.percent}% used")
    
    # Test jinja2 fallback
    env = jinja2.Environment()
    template = env.from_string("Hello {{name}}!")
    result = template.render(name="AutoCAD MCP")
    print(f"Template result: {result}")