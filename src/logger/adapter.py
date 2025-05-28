# -*- coding: utf-8 -*-
"""
Logger adapters module.

This module provides adapter classes that enhance standard loggers 
with additional capabilities like structured logging.
"""

import logging

class StructuredLoggerAdapter(logging.LoggerAdapter):
    """
    An adapter that adds structured data to log messages.
    
    This adapter helps with adding consistent context to all log messages
    from a particular component or context, without having to repeat the
    same extra arguments in every log call.
    
    Example:
        ```python
        from logger import get_logger, get_structured_logger
        
        # Create a logger with context for a specific request
        request_id = "abc123"
        user_id = "user456"
        logger = get_structured_logger(__name__, {"request_id": request_id, "user_id": user_id})
        
        # All log messages will automatically include the structured data
        logger.info("Processing request")  # Will include request_id and user_id
        logger.error("Request failed")     # Will also include request_id and user_id
        ```
    """
    def process(self, msg, kwargs):
        # Ensure that kwargs has an 'extra' dict
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        
        # Update kwargs['extra'] with the adapter's extra dict
        for key, value in self.extra.items():
            if key not in kwargs['extra']:
                kwargs['extra'][key] = value
                
        return msg, kwargs
