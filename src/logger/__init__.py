# -*- coding: utf-8 -*-
"""
Logger module for application-wide logging management.

This module provides a configurable logging system with console, file, and database
backend support. It includes asynchronous logging capabilities, structured logging,
log filtering, log rotation, and automatic fallback mechanisms.

Features:
- PostgreSQL database logging with automatic table creation
- Automatic database log rotation based on retention policy
- File logging with rotation by size
- Asynchronous logging using queue handlers
- Configurable log levels (global and per-component)
- Graceful fallback to console logging on database errors
- Comprehensive log record fields including hostname, thread info, and stack traces
- Structured logging with context data
- Filtering logs by logger name
- Temporary log level adjustments using context managers
"""

import logging
import sys
from queue import Queue
from config import get_config
from .handler import DatabaseLogHandler
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from constant import DEFAULT_LOGGING_PATH
# Import components from separate modules
from .context import LogLevelContext
from .adapter import StructuredLoggerAdapter
from .filters import LoggerNameFilter, add_logger_filter
from .usage import UsageLogger

# Load configuration from config.yml
config = get_config(__name__)
logging_config = config.get('logging', {})
db_config = config.get('database', {})

# Global queue and listener for async logging
_logging_queue = None
_queue_listener = None


def setup_logging(level=None, use_db=None, async_logging=None, service_name=None, log_to_file=False, file_path=None):
    """
    Set up the logging system with PostgreSQL support when available.
    
    Args:
        level: The logging level to use (defaults to config setting or INFO)
        use_db: Whether to attempt database logging (defaults to config setting)
        async_logging: Whether to use asynchronous logging (defaults to config setting)
        service_name: Name of the service for the logger (defaults to config setting)
        log_to_file: Whether to log to a file (defaults to False)
        file_path: Path to the log file (defaults to None, which uses a default location)
    """
    global _logging_queue, _queue_listener
    
    # Get configuration values with fallbacks
    if level is None:
        level_name = logging_config.get('level', 'INFO').upper()
        level = getattr(logging, level_name, logging.INFO)
        
    if use_db is None:
        use_db = logging_config.get('use_database', False)
        
    if async_logging is None:
        async_logging = logging_config.get('async_logging', True)
        
    if service_name is None:
        service_name = logging_config.get('table_prefix', 'app')
        
    # Get log retention days
    retention_days = logging_config.get('log_retention_days', 30)
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    # Set component-specific log levels if configured
    component_levels = logging_config.get('components', {})
    for component, component_level in component_levels.items():
        component_logger = logging.getLogger(f"src.{component}")
        component_logger.setLevel(getattr(logging, component_level.upper(), level))
    
    # Create formatter from config or default
    console_format = logging_config.get('console', {}).get('format', 
                     '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    formatter = logging.Formatter(console_format)
    
    handlers = []
    
    # Always add console handler if enabled in config
    if logging_config.get('console', {}).get('enabled', True):
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(formatter)
        handlers.append(console)
    
    # Add file logging if requested
    if log_to_file:
        import os
        from logging.handlers import RotatingFileHandler
        
        # Default to logs directory in the workspace if not specified
        if file_path is None:
            os.makedirs(DEFAULT_LOGGING_PATH, exist_ok=True)
            file_path = f'{DEFAULT_LOGGING_PATH}/{service_name}.log'
            
        # Set up rotating file handler (10MB files, max 5 backups)
        file_handler = RotatingFileHandler(
            file_path, 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Try to set up PostgreSQL logging if requested
    if use_db and db_config:
        try:
            # Create PostgreSQL handler with retention policy
            pg_handler = DatabaseLogHandler(db_config, service_name, retention_days)
            pg_handler.setFormatter(formatter)
            handlers.append(pg_handler)
        except Exception as e:
            # Log that we couldn't set up PostgreSQL logging
            print(f"Failed to set up PostgreSQL logging: {str(e)}", file=sys.stderr)
    
    if async_logging:
        # Set up asynchronous logging using a queue
        _logging_queue = Queue(-1)  # No limit on size
        
        # Create a queue handler
        queue_handler = QueueHandler(_logging_queue)
        root_logger.addHandler(queue_handler)
        
        # Start queue listener with all handlers
        _queue_listener = QueueListener(_logging_queue, *handlers, respect_handler_level=True)
        _queue_listener.start()
    else:
        # Add all handlers directly to the root logger
        for handler in handlers:
            root_logger.addHandler(handler)
            
    # Create logger for this module
    logger = logging.getLogger(__name__)
    logger.info(f"Logging system initialized with level {logging.getLevelName(level)}")
    
    if len(handlers) > 1:
        logger.info("Logging to both console and PostgreSQL database")
    else:
        logger.info("Logging to console only")

def get_logger(name):
    """
    Get a logger with the specified name.
    
    Args:
        name: The name for the logger
        
    Returns:
        logging.Logger: A configured logger instance
    """
    return logging.getLogger(name)

# Define exported symbols
__all__ = [
    'setup_logging', 
    'get_logger',
    'get_structured_logger',
    'LogLevelContext',
    'LoggerNameFilter', 
    'add_logger_filter',
    'StructuredLoggerAdapter',
    'UsageLogger'
]

# Initialize logging on import
setup_logging()


def get_structured_logger(name, extra=None):
    """
    Get a structured logger with pre-configured context data.
    
    Args:
        name: The name for the logger
        extra: A dictionary of structured data to include with all log messages
        
    Returns:
        StructuredLoggerAdapter: A logger adapter instance with the extra context
    """
    extra = extra or {}
    return StructuredLoggerAdapter(get_logger(name), extra)
