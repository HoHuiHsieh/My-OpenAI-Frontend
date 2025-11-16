# -*- coding: utf-8 -*-
"""
SQLAlchemy-based database log handler module.

This module provides a custom logging handler that writes log records to 
a PostgreSQL database using SQLAlchemy ORM. It integrates with the centralized
database module for connection management.

Features:
- Uses SQLAlchemy ORM with centralized connection pooling
- Automatic table creation via database module
- Graceful fallback to console logging
- Comprehensive log record fields
- Batched writes for better performance
- Thread-safe operations
"""

import logging
import os
import sys
import traceback
import socket
from datetime import datetime
import threading
import time
import json
from typing import Dict, Any, Optional
import queue
import atexit


class SQLAlchemyLogHandler(logging.Handler):
    """
    A custom logging handler that writes log records to PostgreSQL database
    using SQLAlchemy ORM and the centralized database module.
    
    Features:
    - Uses centralized database connection pool
    - Batched writes for better performance
    - Graceful fallback to console logging
    - Comprehensive log fields including stack traces
    - Thread-safe operations
    """
    
    # Batching settings
    DEFAULT_BATCH_SIZE = 50
    DEFAULT_FLUSH_INTERVAL = 5.0  # seconds
    
    def __init__(self, 
                 config,
                 batch_size: int = DEFAULT_BATCH_SIZE,
                 flush_interval: float = DEFAULT_FLUSH_INTERVAL,
                 enable_batching: bool = True):
        """
        Initialize the SQLAlchemy log handler.
        
        Args:
            config: Configuration object
            batch_size: Number of log records to batch before writing
            flush_interval: Maximum time to wait before flushing batch
            enable_batching: Whether to use batched writes
        """
        super().__init__()
        self.config = config
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.enable_batching = enable_batching
        
        # System information
        self._hostname = socket.gethostname()
        self._pid = os.getpid()
        
        # State tracking
        self._initialized = False
        self._init_error = None
        self._is_closing = False
        
        # Batching components
        if self.enable_batching:
            self._batch_queue = queue.Queue(maxsize=batch_size * 2)
            self._batch_thread = None
            self._start_batch_worker()
        
        # Initialize database connection
        self._initialize_database()
        
        # Register cleanup on exit
        atexit.register(self.close)

    def _initialize_database(self):
        """Initialize database connection."""
        try:
            # Import here to avoid circular dependency
            from database import get_db_session
            from database.schema import LogDB
            from sqlalchemy import text
            
            # Test the connection
            with get_db_session() as session:
                # Simple test query
                session.execute(text("SELECT 1"))
            
            self._initialized = True
            self._init_error = None
            
        except Exception as e:
            self._init_error = str(e)
            self._initialized = False
            print(f"Failed to initialize database for logging: {e}", file=sys.stderr)

    def _start_batch_worker(self):
        """Start the background thread for batch processing."""
        if self._batch_thread and self._batch_thread.is_alive():
            return
            
        self._batch_thread = threading.Thread(
            target=self._batch_worker,
            daemon=True,
            name=f"SQLAlchemyLogBatch"
        )
        self._batch_thread.start()

    def _batch_worker(self):
        """Worker thread that processes batched log records."""
        batch = []
        last_flush_time = time.time()
        
        while not self._is_closing:
            try:
                # Wait for records with timeout
                try:
                    record_data = self._batch_queue.get(timeout=1.0)
                    if record_data is None:  # Shutdown signal
                        break
                    if isinstance(record_data, tuple) and record_data[0] == 'FLUSH_SIGNAL':
                        # Immediate flush requested
                        if batch:
                            self._flush_batch(batch)
                            batch.clear()
                            last_flush_time = time.time()
                        continue
                    batch.append(record_data)
                except queue.Empty:
                    pass
                
                current_time = time.time()
                should_flush = (
                    len(batch) >= self.batch_size or
                    (batch and current_time - last_flush_time >= self.flush_interval)
                )
                
                if should_flush and batch:
                    self._flush_batch(batch)
                    batch.clear()
                    last_flush_time = current_time
                    
            except Exception as e:
                print(f"Error in batch worker: {e}", file=sys.stderr)
                # Clear the batch to prevent infinite loop
                batch.clear()
                time.sleep(1.0)
        
        # Flush remaining records on shutdown
        if batch:
            try:
                self._flush_batch(batch)
            except Exception as e:
                print(f"Error flushing final batch: {e}", file=sys.stderr)

    def _flush_batch(self, batch):
        """
        Flush a batch of log records to the database.
        
        Args:
            batch: List of log record dictionaries
        """
        if not batch:
            return
            
        try:
            from database import get_db_session
            from database.schema import LogDB
            
            with get_db_session() as session:
                # Create LogDB objects from batch data
                log_objects = []
                for record_dict in batch:
                    log_obj = LogDB(**record_dict)
                    log_objects.append(log_obj)
                
                # Bulk insert
                session.bulk_save_objects(log_objects)
                # Session is auto-committed by the context manager
                    
        except Exception as e:
            print(f"Failed to flush batch to database: {e}", file=sys.stderr)
            # Fall back to individual logging for this batch
            for record_data in batch:
                try:
                    self._fallback_emit_from_data(record_data)
                except Exception as fallback_error:
                    print(f"Fallback logging also failed: {fallback_error}", file=sys.stderr)

    def emit(self, record):
        """
        Emit a log record. Uses batching if enabled, otherwise writes directly.
        Falls back to console if database logging fails.
        
        Args:
            record: LogRecord instance to emit
        """
        if self._is_closing:
            return
            
        try:
            record_data = self._prepare_record_data(record)
            
            if self.enable_batching and self._batch_queue:
                try:
                    # Try to add to batch queue (non-blocking)
                    self._batch_queue.put_nowait(record_data)
                    return
                except queue.Full:
                    # Queue is full, fall back to direct write
                    pass
            
            # Direct write (not batching or queue full)
            self._write_record_directly(record_data)
            
        except Exception as e:
            # If all else fails, fall back to console logging
            self._fallback_emit(record)

    def _prepare_record_data(self, record) -> dict:
        """
        Prepare log record data for database insertion.
        
        Args:
            record: LogRecord instance
            
        Returns:
            dict: Data dictionary ready for database insertion
        """
        # Extract exception info if any
        exc_info = record.exc_info
        exception_text = None
        if exc_info:
            exception_text = ''.join(traceback.format_exception(*exc_info))
        
        # Extract extra data for structured logging
        extra_data = {}
        standard_fields = {
            'args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
            'funcName', 'id', 'levelname', 'levelno', 'lineno', 'module',
            'msecs', 'message', 'msg', 'name', 'pathname', 'process',
            'processName', 'relativeCreated', 'stack_info', 'thread', 'threadName',
            '_db_error_logged'
        }
        
        for key, value in record.__dict__.items():
            if key not in standard_fields:
                # Ensure the value is JSON serializable
                try:
                    json.dumps(value)
                    extra_data[key] = value
                except (TypeError, ValueError):
                    extra_data[key] = str(value)
        
        log_entry = self.format(record)
        
        return {
            'timestamp': datetime.fromtimestamp(record.created),
            'level': record.levelname,
            'logger_name': record.name,
            'process_id': record.process,
            'thread_id': record.thread,
            'thread_name': record.threadName,
            'hostname': self._hostname,
            'message': log_entry,
            'exception': exception_text,
            'function_name': record.funcName,
            'module': record.module,
            'filename': record.filename,
            'lineno': record.lineno,
            'pathname': record.pathname,
            'extra_data': extra_data if extra_data else None,
            'created_at': datetime.fromtimestamp(record.created)
        }

    def _write_record_directly(self, record_data: dict):
        """
        Write a single record directly to the database.
        
        Args:
            record_data: Prepared record data dictionary
        """
        try:
            from database import get_db_session
            from database.schema import LogDB
            
            with get_db_session() as session:
                log_obj = LogDB(**record_data)
                session.add(log_obj)
                # Session is auto-committed by the context manager
                    
        except Exception as e:
            print(f"Failed to write log record directly: {e}", file=sys.stderr)
            raise

    def _fallback_emit(self, record):
        """Log to stderr when database logging fails."""
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [DB LOGGING FAILED] - %(message)s'
        )
        formatted_record = formatter.format(record)
        print(formatted_record, file=sys.stderr)
        
        # Print initialization error if exists
        if self._init_error and not hasattr(record, '_db_error_logged'):
            setattr(record, '_db_error_logged', True)
            err_msg = f"Database logging failed: {self._init_error}"
            print(err_msg, file=sys.stderr)

    def _fallback_emit_from_data(self, record_data: dict):
        """
        Emit fallback log from prepared record data.
        
        Args:
            record_data: Prepared record data dictionary
        """
        try:
            timestamp = record_data.get('timestamp')
            level = record_data.get('level')
            logger_name = record_data.get('logger_name')
            message = record_data.get('message')
            exception = record_data.get('exception')
            
            fallback_msg = f"{timestamp} - {logger_name} - {level} - [DB BATCH FAILED] - {message}"
            if exception:
                fallback_msg += f"\nException: {exception}"
                
            print(fallback_msg, file=sys.stderr)
            
        except Exception as e:
            print(f"Fallback logging failed: {e}", file=sys.stderr)

    def flush(self):
        """
        Force flush any pending log records.
        """
        if self.enable_batching and self._batch_queue:
            # Signal the batch worker to flush immediately
            try:
                # Add a special flush signal
                self._batch_queue.put_nowait(('FLUSH_SIGNAL',))
            except queue.Full:
                pass
        
        # Call parent flush
        super().flush()

    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get the current status of the database connection.
        
        Returns:
            dict: Connection status information
        """
        status = {
            'initialized': self._initialized,
            'connected': False,
            'last_error': self._init_error,
            'hostname': self._hostname,
            'pid': self._pid,
            'batching_enabled': self.enable_batching,
            'batch_size': self.batch_size if self.enable_batching else None,
            'queue_size': self._batch_queue.qsize() if self.enable_batching else None,
        }
        
        try:
            from database import get_db_session
            from sqlalchemy import text
            
            with get_db_session() as session:
                session.execute(text("SELECT 1"))
                status['connected'] = True
                status['initialized'] = True  # If we can connect, we're initialized
        except:
            status['connected'] = False
            
        return status

    def close(self):
        """Close the handler and cleanup resources."""
        self._is_closing = True
        
        # Stop batch processing and flush remaining records
        if self.enable_batching and self._batch_queue:
            try:
                # Signal shutdown to batch worker
                self._batch_queue.put_nowait(None)
                
                # Wait for batch thread to finish (with timeout)
                if self._batch_thread and self._batch_thread.is_alive():
                    self._batch_thread.join(timeout=5.0)
                    
            except Exception as e:
                print(f"Error during batch worker shutdown: {e}", file=sys.stderr)
        
        super().close()
