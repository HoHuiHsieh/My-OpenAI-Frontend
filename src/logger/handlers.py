# -*- coding: utf-8 -*-
"""
Logger handlers module.

Contains factory functions for creating different types of logging handlers
(console, database, file) based on configuration.
"""

import logging
import logging.handlers
import sys
import os
from typing import Optional
from pathlib import Path
import logging
import logging.handlers
import sys
from typing import Optional
from pathlib import Path

from .log_handler import DatabaseLogHandler


def create_console_handler(config=None) -> Optional[logging.Handler]:
    """
    Create and configure console handler using util configuration.
    
    Args:
        config: Configuration object from util module
        
    Returns:
        Configured console handler or None if disabled
    """
    try:
        handler = logging.StreamHandler(sys.stdout)
        
        # Set formatter based on util configuration
        if config and hasattr(config, 'logging') and config.logging:
            console_config = getattr(config.logging, 'console', {})
            format_str = console_config.get('format', 
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        else:
            # Default format when no config available
            format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        formatter = logging.Formatter(format_str)
        handler.setFormatter(formatter)
        
        return handler
        
    except Exception as e:
        print(f"Failed to create console handler: {e}", file=sys.stderr)
        return None


def create_database_handler(config) -> Optional[DatabaseLogHandler]:
    """
    Create and configure database handler using util configuration.
    
    Args:
        config: Configuration object from util module
        
    Returns:
        Configured database handler or None if disabled/failed
    """
    if not config or not config.is_database_logging_enabled():
        return None
        
    try:
        # Build database configuration using util config methods
        db_config = {
            'host': config.get_database_host(),
            'port': config.get_database_port(),
            'database': config.get_database_name(),
            'username': config.database.username if config.database else '',
            'password': config.database.password if config.database else '',
            'ssl_mode': 'prefer'
        }
        
        # Validate required database fields
        required_fields = ['host', 'database', 'username', 'password']
        missing_fields = [field for field in required_fields if not db_config.get(field)]
        if missing_fields:
            print(f"Missing required database configuration: {', '.join(missing_fields)}", file=sys.stderr)
            return None
        
        # Get logging-specific configuration from util
        table_prefix = config.get_table_prefix() or 'app'
        retention_days = config.get_log_retention_days()
        
        # Create database handler with configuration from util
        handler = DatabaseLogHandler(
            db_config=db_config,
            table_prefix=table_prefix,
            retention_days=retention_days,
            batch_size=50,  # Could be made configurable in util if needed
            flush_interval=5.0,  # Could be made configurable in util if needed
            enable_batching=True  # Could be made configurable in util if needed
        )
        
        # Set log level from util configuration
        log_level = config.get_logging_level()
        handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        
        # Set formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        handler.setFormatter(formatter)
        
        return handler
        
    except Exception as e:
        print(f"Failed to create database handler: {e}", file=sys.stderr)
        return None


def create_file_handler(log_file: str, max_bytes: int = 10*1024*1024, 
                       backup_count: int = 5) -> Optional[logging.Handler]:
    """
    Create and configure file handler with rotation.
    
    Args:
        log_file: Path to log file
        max_bytes: Maximum file size before rotation
        backup_count: Number of backup files to keep
        
    Returns:
        Configured file handler or None if failed
    """
    try:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create rotating file handler
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        
        # Set formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
        )
        handler.setFormatter(formatter)
        
        return handler
        
    except Exception as e:
        print(f"Failed to create file handler: {e}", file=sys.stderr)
        return None
