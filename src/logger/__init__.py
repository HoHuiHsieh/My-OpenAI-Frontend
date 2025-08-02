# -*- coding: utf-8 -*-
"""
Logger module for application-wide logging management.

This module provides a configurable logging system with console, and database backend support. 
It includes asynchronous logging capabilities, log rotation, structured logging, and automatic fallback mechanisms.

Features:
- PostgreSQL database logging with automatic table creation
- Automatic database log rotation based on retention policy
- Asynchronous logging using queue handlers
- Configurable log levels (global and per-component)
- Graceful fallback to console logging on database errors
- Comprehensive log record fields including hostname and stack traces
- Structured logging with context data
"""

import logging
from typing import Optional

from .manager import LoggerManager


# Global logger manager instance
_logger_manager: Optional[LoggerManager] = LoggerManager()


def initialize_logger(config=None) -> bool:
    """
    Initialize the application logging system.
    
    Args:
        config: Configuration object. If None, will load from util module.
        
    Returns:
        bool: True if initialization successful
    """
    global _logger_manager
    if _logger_manager is None:
        _logger_manager = LoggerManager(config)
    return _logger_manager.initialize()


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger
        
    Raises:
        RuntimeError: If logger system is not initialized
    """
    global _logger_manager
    if _logger_manager is None:
        raise RuntimeError("Logger system not initialized. Call initialize_logger() first.")
    return _logger_manager.get_logger(name)


def shutdown_logging():
    """Shutdown the logging system gracefully."""
    global _logger_manager
    if _logger_manager:
        _logger_manager.shutdown()
        _logger_manager = None


# Export only the specified functions
__all__ = [
    'initialize_logger',
    'get_logger', 
    'shutdown_logging'
]
