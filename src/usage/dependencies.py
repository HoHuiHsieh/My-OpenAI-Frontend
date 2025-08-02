# -*- coding: utf-8 -*-
"""
Dependency injection for usage module.

This module provides dependency injection for the usage tracking system,
eliminating global state and improving testability.
"""

from typing import Optional, Dict, Any, TYPE_CHECKING
from functools import lru_cache
from fastapi import Depends
from config import Config

if TYPE_CHECKING:
    from .manager import UsageManager


class UsageManagerFactory:
    """Factory for creating and managing UsageManager instances."""
    
    _instance: Optional["UsageManager"] = None
    _config: Optional[Config] = None
    
    @classmethod
    def create_manager(cls, config: Optional[Config] = None) -> "UsageManager":
        """
        Create a new UsageManager instance.
        
        Args:
            config: Configuration object. If None, creates a new Config instance.
            
        Returns:
            UsageManager instance
        """
        if config is None:
            config = Config()
        from .manager import UsageManager  # moved import here to avoid circular import
        manager = UsageManager(config)
        manager.initialize()
        return manager
    
    @classmethod
    def get_singleton(cls, config: Optional[Config] = None) -> "UsageManager":
        """
        Get a singleton UsageManager instance.
        
        Args:
            config: Configuration object for initialization
            
        Returns:
            Singleton UsageManager instance
        """
        if cls._instance is None or cls._config != config:
            cls._instance = cls.create_manager(config)
            cls._config = config
        return cls._instance
    
    @classmethod
    def reset(cls):
        """Reset the singleton instance (useful for testing)."""
        if cls._instance:
            cls._instance.shutdown()
        cls._instance = None
        cls._config = None


@lru_cache()
def get_config() -> Config:
    """
    Get configuration instance.
    
    Returns:
        Config instance
    """
    return Config()


def get_usage_manager(config: Config = Depends(get_config)) -> "UsageManager":
    """
    Dependency injection function for UsageManager.
    
    Args:
        config: Configuration dependency
        
    Returns:
        UsageManager instance
    """
    return UsageManagerFactory.get_singleton(config)


def create_usage_manager(config: Optional[Config] = None) -> "UsageManager":
    """
    Create a new UsageManager instance (for testing or special cases).
    
    Args:
        config: Optional configuration object
        
    Returns:
        New UsageManager instance
    """
    return UsageManagerFactory.create_manager(config)


# Context manager for usage manager lifecycle
class UsageManagerContext:
    """Context manager for UsageManager lifecycle."""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config
        self.manager: Optional["UsageManager"] = None
    
    def __enter__(self) -> "UsageManager":
        self.manager = create_usage_manager(self.config)
        return self.manager
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.manager:
            self.manager.shutdown()
