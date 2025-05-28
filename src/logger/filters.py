# -*- coding: utf-8 -*-
"""
Logger filters module.

This module provides filtering capabilities for loggers, allowing
log records to be filtered based on criteria like logger name.
"""

import logging

class LoggerNameFilter(logging.Filter):
    """
    Filter logs based on logger name prefixes.
    
    This filter can be used to include or exclude logs from specific modules
    or components based on their logger names.
    
    Args:
        includes: List of logger name prefixes to include
        excludes: List of logger name prefixes to exclude
    """
    def __init__(self, includes=None, excludes=None):
        super().__init__()
        self.includes = includes or []
        self.excludes = excludes or []
        
    def filter(self, record):
        """
        Filter log records based on logger name.
        
        Args:
            record: The log record to check
            
        Returns:
            bool: True if the record should be logged, False otherwise
        """
        # If includes list is empty, allow all except those in excludes
        if not self.includes:
            for exclude in self.excludes:
                if record.name.startswith(exclude):
                    return False
            return True
            
        # If includes list has entries, only allow those and still check excludes
        for include in self.includes:
            if record.name.startswith(include):
                for exclude in self.excludes:
                    if record.name.startswith(exclude):
                        return False
                return True
                
        # If includes has entries but none matched, exclude by default
        return False


def add_logger_filter(handler=None, includes=None, excludes=None):
    """
    Add a filter to a handler or the root logger to filter by logger name.
    
    Args:
        handler: The handler to add the filter to, or None to add to all root handlers
        includes: List of logger name prefixes to include
        excludes: List of logger name prefixes to exclude
        
    Returns:
        LoggerNameFilter: The created filter
    """
    name_filter = LoggerNameFilter(includes, excludes)
    
    if handler:
        handler.addFilter(name_filter)
    else:
        # Add to all handlers on the root logger
        root_logger = logging.getLogger()
        for h in root_logger.handlers:
            h.addFilter(name_filter)
            
    return name_filter
