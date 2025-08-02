# -*- coding: utf-8 -*-
"""
Usage Logger module for application-wide logging management.

This module provides a configurable logging system with database backend support. 

Features:
- PostgreSQL database logging with automatic table creation
- Asynchronous logging using queue handlers
- Comprehensive usage record fields
- Dependency injection for better testability and maintainability
"""

import logging
from typing import Optional
from .manager import UsageManager
from .dependencies import (
    get_usage_manager,
    create_usage_manager,
    UsageManagerFactory,
    UsageManagerContext
)
from .routes import (
    user_router as usage_user_router,
    admin_router as usage_admin_router
)


def initialize_usage_logger(config=None) -> bool:
    """
    Initialize the usage logging system.
    
    Args:
        config: Configuration object. If None, will load from Config.
        
    Returns:
        bool: True if initialization successful
    """
    try:
        manager = UsageManagerFactory.get_singleton(config)
        return manager._initialized
    except Exception:
        return False


def get_usage_logger(api_type: str, manager: Optional[UsageManager] = None) -> logging.Logger:
    """
    Get a configured logger instance for usage logging.
    
    Args:
        api_type: API type for which to get the logger
        manager: Optional UsageManager instance. If None, uses singleton.
        
    Returns:
        Configured logger
        
    Raises:
        RuntimeError: If usage logging system is not initialized
    """
    if manager is None:
        manager = UsageManagerFactory.get_singleton()
    
    if not manager._initialized:
        raise RuntimeError("Usage logging system not initialized. Call initialize_usage_logger() first.")
    
    return manager.get_usage_logger(api_type)


def shutdown_usage_logger():
    """
    Shutdown the usage logging system gracefully.
    
    This will close all handlers and release resources.
    """
    UsageManagerFactory.reset()



__all__ = [
    'initialize_usage_logger',
    'get_usage_logger', 
    'shutdown_usage_logger',
    'get_usage_manager',
    'create_usage_manager',
    'UsageManagerFactory',
    'UsageManagerContext',
    'UsageManager'
]