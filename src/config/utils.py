"""
Global configuration instance and utilities
"""

from typing import Optional
from .manager import Config

# Global configuration instance
_config_instance: Optional[Config] = None


def get_config(config_path: Optional[str] = None) -> Config:
    """
    Get the global configuration instance.
    
    Args:
        config_path: Path to config file (only used on first call)
    
    Returns:
        Config instance
    """
    global _config_instance
    
    if _config_instance is None:
        _config_instance = Config(config_path)
    
    return _config_instance


def reload_config() -> None:
    """Reload the global configuration from file."""
    global _config_instance
    
    if _config_instance:
        _config_instance.reload()


def reset_config() -> None:
    """Reset the global configuration instance (useful for testing)."""
    global _config_instance
    _config_instance = None
