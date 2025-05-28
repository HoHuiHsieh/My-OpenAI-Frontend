# -*- coding: utf-8 -*-
"""
Database log handler module for PostgreSQL logging.

This module provides a custom logging handler that writes log records to 
a PostgreSQL database. It handles connection management, table creation,
and implements fallback mechanisms when database operations fail.

Features:
- Automatic table creation
- Graceful fallback to console logging
- Comprehensive log record fields
- Periodic log rotation based on retention policy
- Reconnection attempts on database errors
"""
import logging
import psycopg2
import psycopg2.extras
from psycopg2 import sql
import os
import sys
import traceback
import socket
from datetime import datetime, timedelta
import threading
import time



class DatabaseLogHandler(logging.Handler):
    """
    A custom logging handler that writes log records to PostgreSQL database.
    Falls back to console logging if database connection fails.
    
    Features:
    - Automatic table creation
    - Connection management and reconnection
    - Log rotation based on retention policy
    - Comprehensive log fields including stack traces
    """
    def __init__(self, db_config, table_prefix, retention_days=30):
        super().__init__()
        self.db_config = db_config
        self.table_prefix = table_prefix
        self.retention_days = retention_days
        self.connection = None
        self._hostname = socket.gethostname()
        self._pid = os.getpid()
        self._initialized = False
        self._init_error = None
        self._lock = threading.RLock()  # For thread safety
        self._connect_to_db()
        
        # Start log rotation thread if rotation is enabled
        if self.retention_days > 0:
            self._start_log_rotation()

    def _connect_to_db(self):
        """Connect to the database and initialize the logs table."""
        with self._lock:
            try:
                self.connection = psycopg2.connect(
                    dbname=self.db_config['name'],
                    user=self.db_config['username'],
                    password=self.db_config['password'],
                    host=self.db_config['host'],
                    port=self.db_config['port'],
                    sslmode=self.db_config.get('ssl_mode', 'prefer')
                )
                
                # Create logs table if it doesn't exist
                table_name = f"{self.table_prefix}_logs"
                
                with self.connection.cursor() as cursor:
                    cursor.execute(sql.SQL(f"""
                        CREATE TABLE IF NOT EXISTS {table_name} (
                            id SERIAL PRIMARY KEY,
                            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            level VARCHAR(10) NOT NULL,
                            logger_name VARCHAR(100) NOT NULL,
                            process_id INTEGER NOT NULL,
                            thread_id BIGINT NOT NULL,
                            thread_name VARCHAR(100),
                            hostname VARCHAR(255) NOT NULL,
                            message TEXT NOT NULL,
                            exception TEXT,
                            function_name VARCHAR(100),
                            module VARCHAR(100),
                            filename VARCHAR(255),
                            lineno INTEGER,
                            pathname TEXT,
                            extra_data JSONB
                        )
                    """))
                    
                    # Add index on commonly queried fields
                    cursor.execute(sql.SQL(f"""
                        CREATE INDEX IF NOT EXISTS idx_{self.table_prefix}_logs_timestamp 
                        ON {table_name} (timestamp)
                    """))
                    
                    cursor.execute(sql.SQL(f"""
                        CREATE INDEX IF NOT EXISTS idx_{self.table_prefix}_logs_level
                        ON {table_name} (level)
                    """))
                    
                    cursor.execute(sql.SQL(f"""
                        CREATE INDEX IF NOT EXISTS idx_{self.table_prefix}_logs_logger
                        ON {table_name} (logger_name)
                    """))
                    
                    self.connection.commit()
                
                self._initialized = True
                self._init_error = None
                
            except Exception as e:
                self._init_error = str(e)
                self._initialized = False
                print(f"Failed to connect to database: {e}", file=sys.stderr)

    def emit(self, record):
        """
        Emit a log record to the database.
        Falls back to console if database logging fails.
        
        Supports structured logging through extra data in record.
        """
        if not self._initialized or not self.connection:
            self._fallback_emit(record)
            return
            
        try:
            # Extract exception info if any
            exc_info = record.exc_info
            exception_text = None
            if exc_info:
                exception_text = ''.join(traceback.format_exception(*exc_info))
            
            # Extract extra data for structured logging
            extra_data = {}
            for key, value in record.__dict__.items():
                if key not in ('args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
                              'funcName', 'id', 'levelname', 'levelno', 'lineno', 'module',
                              'msecs', 'message', 'msg', 'name', 'pathname', 'process',
                              'processName', 'relativeCreated', 'stack_info', 'thread', 'threadName',
                              '_db_error_logged'):
                    extra_data[key] = value
            
            table_name = f"{self.table_prefix}_logs"
            log_entry = self.format(record)
            
            with self._lock:
                if not self.connection or self.connection.closed:
                    self._connect_to_db()
                    if not self._initialized:
                        self._fallback_emit(record)
                        return
                
                with self.connection.cursor() as cursor:
                    cursor.execute(
                        f"""
                        INSERT INTO {table_name} 
                        (timestamp, level, logger_name, process_id, thread_id, thread_name, 
                         hostname, message, exception, function_name, module, filename, lineno, pathname, extra_data)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            datetime.fromtimestamp(record.created),
                            record.levelname,
                            record.name,
                            record.process,
                            record.thread,
                            record.threadName,
                            self._hostname,
                            log_entry,
                            exception_text,
                            record.funcName,
                            record.module,
                            record.filename,
                            record.lineno,
                            record.pathname,
                            psycopg2.extras.Json(extra_data) if extra_data else None
                        )
                    )
                    self.connection.commit()
                
        except Exception as e:
            # If database logging fails, reconnect and try again
            try:
                with self._lock:
                    if self.connection and not self.connection.closed:
                        self.connection.close()
            except:
                pass
                
            self._connect_to_db()
            self._fallback_emit(record)

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

    def _start_log_rotation(self):
        """Start a background thread for log rotation."""
        rotation_thread = threading.Thread(
            target=self._rotation_worker,
            daemon=True,
            name=f"LogRotation-{self.table_prefix}"
        )
        rotation_thread.start()
        
    def _rotation_worker(self):
        """Worker thread that periodically cleans up old logs."""
        # Run rotation once per day
        ROTATION_INTERVAL = 86400  # 24 hours in seconds
        
        while True:
            try:
                # Sleep first to avoid immediate rotation on startup
                time.sleep(ROTATION_INTERVAL)
                self._rotate_logs()
            except Exception as e:
                # Don't let the rotation thread die due to errors
                print(f"Error during log rotation: {str(e)}", file=sys.stderr)
                
    def _rotate_logs(self):
        """Delete logs older than retention_days."""
        if not self._initialized or not self.connection:
            return
            
        try:
            # Calculate the cutoff date
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            table_name = f"{self.table_prefix}_logs"
            
            with self._lock:
                with self.connection.cursor() as cursor:
                    cursor.execute(
                        f"DELETE FROM {table_name} WHERE timestamp < %s",
                        (cutoff_date,)
                    )
                    deleted_count = cursor.rowcount
                    self.connection.commit()
                    
                    # Log the deletion if rows were affected
                    if deleted_count > 0:
                        print(f"Log rotation: Deleted {deleted_count} records older than {cutoff_date.isoformat()}", 
                              file=sys.stdout)
                              
        except Exception as e:
            # If rotation fails, just log the error
            print(f"Failed to rotate logs: {str(e)}", file=sys.stderr)
            try:
                self.connection.rollback()
            except:
                pass

    def close(self):
        """Close the database connection when the handler is closed."""
        with self._lock:
            if self.connection:
                try:
                    self.connection.close()
                except:
                    pass
        super().close()