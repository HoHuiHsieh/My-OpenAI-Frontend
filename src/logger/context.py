# -*- coding: utf-8 -*-
"""
Context managers for the logger module.

This module provides context managers that allow temporary modifications
of logger behavior, such as changing log levels for specific code blocks.
"""

import logging

class LogLevelContext:
    """
    Context manager for temporarily changing the log level of a logger.
    
    Example:
        ```python
        from logger import get_logger, LogLevelContext
        import logging
        
        logger = get_logger(__name__)
        
        # Temporarily increase verbosity for a section of code
        with LogLevelContext(logger, logging.DEBUG):
            logger.debug("This debug message will be logged")
            # Do some operations that need detailed logging
        
        # Outside the context, the logger returns to its original level
        logger.debug("This debug message won't be logged if original level was higher")
        ```
    """
    def __init__(self, logger, level):
        """
        Initialize the context manager with a logger and temporary level.
        
        Args:
            logger: The logger instance to modify
            level: The temporary logging level to use
        """
        self.logger = logger
        self.temp_level = level
        self.original_level = logger.level

    def __enter__(self):
        """Set the temporary log level when entering the context."""
        self.logger.setLevel(self.temp_level)
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore the original log level when exiting the context."""
        self.logger.setLevel(self.original_level)
