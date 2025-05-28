#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Usage Logger Module

This module provides specialized logging functionality for API usage metrics.
It helps track and log API consumption data like token counts, request counts,
and other usage statistics.

Features:
- Structured logging of API usage metrics
- Support for different API types (chat, embeddings, etc.)
- User-specific usage tracking
- Standardized format for easy analysis and billing
"""
import traceback
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, Union

from .adapter import StructuredLoggerAdapter

# Create a dedicated logger for usage metrics
_usage_logger = logging.getLogger("usage")

class UsageLogger:
    """
    Specialized logger for API usage metrics.
    
    This class provides methods for logging structured usage data
    for different API endpoints, with a focus on token counts and
    request metrics.
    """
    
    @staticmethod
    def initialize():
        """
        Initialize the usage logger with a dedicated file handler and database table.
        
        This method should be called on application startup to ensure the usage logs
        are properly configured with their own log file and database table.
        """
        from config import get_config
        import os
        from logging.handlers import RotatingFileHandler
        import psycopg2
        from psycopg2 import sql
        from constant import DEFAULT_LOGGING_PATH
        
        # Get configuration
        config = get_config()
        logging_config = config.get('logging', {})
        db_config = config.get('database', {})
        
        # Create usage log directory if it doesn't exist
        os.makedirs(DEFAULT_LOGGING_PATH, exist_ok=True)
        
        # Set up a dedicated file handler for usage logs
        file_path = f"{DEFAULT_LOGGING_PATH}/usage.log"
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Check if the usage logger already has handlers
        has_handlers = False
        for handler in _usage_logger.handlers:
            if isinstance(handler, RotatingFileHandler) and handler.baseFilename == os.path.abspath(file_path):
                has_handlers = True
                break
                
        if not has_handlers:
            file_handler = RotatingFileHandler(
                file_path,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            file_handler.setFormatter(formatter)
            _usage_logger.addHandler(file_handler)
            
        # Create a dedicated database table for usage logs if database logging is enabled
        use_db = logging_config.get('use_database', False)
        if use_db and db_config:
            try:
                # Connect to the database with a timeout
                connection = psycopg2.connect(
                    dbname=db_config.get('name'),
                    user=db_config.get('username'),
                    password=db_config.get('password'),
                    host=db_config.get('host'),
                    port=db_config.get('port'),
                    sslmode=db_config.get('ssl_mode', 'prefer'),
                    connect_timeout=5  # 5 second timeout for connection
                )
                
                table_prefix = logging_config.get('table_prefix', 'myopenaiapi')
                table_name = f"{table_prefix}_usage"
                
                with connection.cursor() as cursor:
                    # Create the usage logs table if it doesn't exist
                    cursor.execute(sql.SQL(f"""
                        CREATE TABLE IF NOT EXISTS {table_name} (
                            id SERIAL PRIMARY KEY,
                            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            api_type VARCHAR(50) NOT NULL,
                            user_id VARCHAR(255) NOT NULL,
                            model VARCHAR(100) NOT NULL,
                            request_id VARCHAR(255),
                            prompt_tokens INTEGER NOT NULL,
                            completion_tokens INTEGER,
                            total_tokens INTEGER NOT NULL,
                            input_count INTEGER,
                            extra_data JSONB
                        )
                    """))
                    
                    # Add indices for common queries
                    cursor.execute(sql.SQL(f"""
                        CREATE INDEX IF NOT EXISTS idx_{table_prefix}_usage_timestamp 
                        ON {table_name} (timestamp)
                    """))
                    
                    cursor.execute(sql.SQL(f"""
                        CREATE INDEX IF NOT EXISTS idx_{table_prefix}_usage_user_id 
                        ON {table_name} (user_id)
                    """))
                    
                    cursor.execute(sql.SQL(f"""
                        CREATE INDEX IF NOT EXISTS idx_{table_prefix}_usage_api_type 
                        ON {table_name} (api_type)
                    """))
                
                connection.commit()
                _usage_logger.info(f"Initialized usage log table: {table_name}")
            except Exception as e:
                _usage_logger.error(f"Failed to initialize usage log database table: {str(e)}")
            finally:
                if connection:
                    connection.close()
                    
        _usage_logger.info("UsageLogger initialized successfully")
    
    @staticmethod
    def log_chat_usage(
        user_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        request_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log usage metrics for chat completion API.
        
        Args:
            user_id: The ID of the user making the request
            model: The model used for the completion
            prompt_tokens: Number of tokens in the prompt
            completion_tokens: Number of tokens in the completion
            total_tokens: Total number of tokens used
            request_id: Optional unique identifier for the request
            extra: Optional additional data to log
        """
        extra = extra or {}
        usage_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "api_type": "chat_completion",
            "user_id": user_id,
            "model": model,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            },
            "request_id": request_id,
            **extra
        }
        
        # Use structured logger for consistent format
        adapter = StructuredLoggerAdapter(_usage_logger, usage_data)
        adapter.info(f"Chat usage: {user_id} used {total_tokens} tokens with model {model}")
        
        # Also save directly to database if configured
        UsageLogger._save_to_database(usage_data)
    
    @staticmethod
    def log_embeddings_usage(
        user_id: str,
        model: str,
        prompt_tokens: int,
        total_tokens: int,
        input_count: int,
        request_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log usage metrics for embeddings API.
        
        Args:
            user_id: The ID of the user making the request
            model: The model used for embeddings
            prompt_tokens: Number of tokens in the input
            total_tokens: Total number of tokens used
            input_count: Number of inputs processed
            request_id: Optional unique identifier for the request
            extra: Optional additional data to log
        """
        extra = extra or {}
        usage_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "api_type": "embeddings",
            "user_id": user_id,
            "model": model,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "total_tokens": total_tokens,
                "input_count": input_count
            },
            "request_id": request_id,
            **extra
        }
        
        # Use structured logger for consistent format
        adapter = StructuredLoggerAdapter(_usage_logger, usage_data)
        adapter.info(f"Embeddings usage: {user_id} used {total_tokens} tokens with model {model}")
        
        # Also save directly to database if configured
        UsageLogger._save_to_database(usage_data)
    
    @staticmethod
    def _save_to_database(usage_data):
        """
        Save usage data directly to the dedicated usage database table.
        
        Args:
            usage_data: Dictionary containing usage information
        """
        from config import get_config
        import psycopg2
        import psycopg2.extras
        import json
        
        # Get configuration
        config = get_config()
        logging_config = config.get('logging', {})
        db_config = config.get('database', {})
        
        # Only proceed if database logging is enabled
        use_db = logging_config.get('use_database', False)
        if not use_db or not db_config:
            return
        
        connection = None
        try:
            # Connect to the database
            connection = psycopg2.connect(
                dbname=db_config.get('name'),
                user=db_config.get('username'),
                password=db_config.get('password'),
                host=db_config.get('host'),
                port=db_config.get('port'),
                sslmode=db_config.get('ssl_mode', 'prefer')
            )
            
            table_prefix = logging_config.get('table_prefix', 'myopenaiapi')
            table_name = f"{table_prefix}_usage"
            
            # Extract values from usage_data
            api_type = usage_data.get('api_type')
            user_id = usage_data.get('user_id')
            model = usage_data.get('model')
            request_id = usage_data.get('request_id')
            usage = usage_data.get('usage', {})
            timestamp = usage_data.get('timestamp')
            
            # Extract metrics and convert numpy types to Python native types
            prompt_tokens = int(usage.get('prompt_tokens', 0))
            completion_tokens = int(usage.get('completion_tokens', 0)) if 'completion_tokens' in usage else None
            total_tokens = int(usage.get('total_tokens', 0))
            input_count = int(usage.get('input_count')) if 'input_count' in usage else None
            
            # Remove nested usage data to avoid duplication in extra_data
            extra_data = {k: v for k, v in usage_data.items() if k not in ('api_type', 'user_id', 'model', 'request_id', 'usage', 'timestamp')}
            
            # Set isolation level to autocommit for better performance with logging
            connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            
            # Insert the data
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    INSERT INTO {table_name} 
                    (timestamp, api_type, user_id, model, request_id, prompt_tokens, completion_tokens, total_tokens, input_count, extra_data)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        timestamp,
                        api_type,
                        user_id,
                        model,
                        request_id,
                            prompt_tokens,
                            completion_tokens,
                            total_tokens,
                            input_count,
                            json.dumps(extra_data) if extra_data else None
                        )
                    )
            # No need to commit with AUTOCOMMIT isolation level
            
        except Exception as e:
            print(traceback.sys.exc_info())
            _usage_logger.error(f"Failed to save usage data to database: {str(e)}")
            if connection:
                connection.rollback()
        finally:
            if connection:
                connection.close()
