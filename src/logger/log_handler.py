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
import psycopg2.pool
from psycopg2 import sql, OperationalError, InterfaceError
import os
import sys
import traceback
import socket
from datetime import datetime, timedelta
import threading
import time
import json
from typing import Dict, Any, Optional
from contextlib import contextmanager
import queue
import atexit



class DatabaseLogHandler(logging.Handler):
    """
    A robust custom logging handler that writes log records to PostgreSQL database.
    Features improved error handling, batching, and connection management.
    
    Features:
    - Automatic table creation with proper indexing
    - Connection pooling and reconnection with exponential backoff
    - Batched writes for better performance
    - Graceful fallback to console logging
    - Log rotation based on retention policy
    - Comprehensive log fields including stack traces
    - Thread-safe operations
    - Configurable retry mechanisms
    """
    
    # Connection retry settings
    MAX_RETRY_ATTEMPTS = 5
    INITIAL_RETRY_DELAY = 1.0  # seconds
    MAX_RETRY_DELAY = 60.0  # seconds
    BACKOFF_MULTIPLIER = 2.0
    
    # Batching settings
    DEFAULT_BATCH_SIZE = 50
    DEFAULT_FLUSH_INTERVAL = 5.0  # seconds
    
    # Connection pool settings
    DEFAULT_MIN_POOL_CONNECTIONS = 1
    DEFAULT_MAX_POOL_CONNECTIONS = 10
    
    def __init__(self, 
                 db_config: Dict[str, Any], 
                 table_prefix: str, 
                 retention_days: int = 30,
                 batch_size: int = DEFAULT_BATCH_SIZE,
                 flush_interval: float = DEFAULT_FLUSH_INTERVAL,
                 enable_batching: bool = True,
                 min_pool_connections: int = DEFAULT_MIN_POOL_CONNECTIONS,
                 max_pool_connections: int = DEFAULT_MAX_POOL_CONNECTIONS):
        """
        Initialize the database log handler.
        
        Args:
            db_config: Database configuration dictionary
            table_prefix: Prefix for the log table name
            retention_days: Number of days to retain logs (0 = no rotation)
            batch_size: Number of log records to batch before writing
            flush_interval: Maximum time to wait before flushing batch
            enable_batching: Whether to use batched writes
            min_pool_connections: Minimum number of connections in the pool
            max_pool_connections: Maximum number of connections in the pool
        """
        super().__init__()
        self.db_config = db_config
        self.table_prefix = table_prefix
        self.retention_days = retention_days
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.enable_batching = enable_batching
        self.min_pool_connections = min_pool_connections
        self.max_pool_connections = max_pool_connections
        
        # Connection pool management
        self.connection_pool = None
        self._connection_lock = threading.RLock()
        self._retry_count = 0
        self._last_retry_time = 0
        
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
        self._connect_to_db()
        
        # Start log rotation if enabled
        if self.retention_days > 0:
            self._start_log_rotation()
            
        # Register cleanup on exit
        atexit.register(self.close)

    def _connect_to_db(self) -> bool:
        """
        Initialize connection pool with retry logic and exponential backoff.
        
        Returns:
            bool: True if connection pool created successfully, False otherwise
        """
        with self._connection_lock:
            # Check if we should retry (implement exponential backoff)
            current_time = time.time()
            if self._retry_count > 0:
                wait_time = min(
                    self.INITIAL_RETRY_DELAY * (self.BACKOFF_MULTIPLIER ** (self._retry_count - 1)),
                    self.MAX_RETRY_DELAY
                )
                if current_time - self._last_retry_time < wait_time:
                    return False
            
            if self._retry_count >= self.MAX_RETRY_ATTEMPTS:
                return False
                
            try:
                # Close existing connection pool if any
                if self.connection_pool:
                    try:
                        self.connection_pool.closeall()
                    except:
                        pass
                
                # Create new connection pool
                self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=self.min_pool_connections,
                    maxconn=self.max_pool_connections,
                    dbname=self.db_config.get('database', self.db_config.get('name')),
                    user=self.db_config.get('username', self.db_config.get('user')),
                    password=self.db_config['password'],
                    host=self.db_config['host'],
                    port=self.db_config.get('port', 5432),
                    sslmode=self.db_config.get('ssl_mode', 'prefer'),
                    connect_timeout=10,  # 10 second timeout
                    application_name=f"DatabaseLogHandler-{self._pid}"
                )
                
                # Test the connection pool
                conn = self.connection_pool.getconn()
                try:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                finally:
                    self.connection_pool.putconn(conn)
                
                # Initialize the database schema
                if self._initialize_schema():
                    self._initialized = True
                    self._init_error = None
                    self._retry_count = 0
                    return True
                else:
                    return False
                
            except (OperationalError, InterfaceError, Exception) as e:
                self._init_error = str(e)
                self._initialized = False
                self._retry_count += 1
                self._last_retry_time = current_time
                
                error_msg = f"Database connection pool creation attempt {self._retry_count}/{self.MAX_RETRY_ATTEMPTS} failed: {e}"
                print(error_msg, file=sys.stderr)
                
                return False
    
    def _initialize_schema(self) -> bool:
        """
        Initialize the database schema (create tables and indexes).
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        conn = None
        try:
            table_name = f"{self.table_prefix}_logs"
            
            # Get a connection from the pool
            conn = self.connection_pool.getconn()
            
            with conn.cursor() as cursor:
                # Create logs table with improved schema
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        id BIGSERIAL PRIMARY KEY,
                        timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        level VARCHAR(10) NOT NULL,
                        logger_name VARCHAR(255) NOT NULL,
                        process_id INTEGER NOT NULL,
                        thread_id BIGINT NOT NULL,
                        thread_name VARCHAR(255),
                        hostname VARCHAR(255) NOT NULL,
                        message TEXT NOT NULL,
                        exception TEXT,
                        function_name VARCHAR(255),
                        module VARCHAR(255),
                        filename VARCHAR(500),
                        lineno INTEGER,
                        pathname TEXT,
                        extra_data JSONB,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes if they don't exist
                indexes = [
                    f"CREATE INDEX IF NOT EXISTS idx_{self.table_prefix}_logs_timestamp ON {table_name} (timestamp DESC)",
                    f"CREATE INDEX IF NOT EXISTS idx_{self.table_prefix}_logs_level ON {table_name} (level)",
                    f"CREATE INDEX IF NOT EXISTS idx_{self.table_prefix}_logs_logger ON {table_name} (logger_name)",
                    f"CREATE INDEX IF NOT EXISTS idx_{self.table_prefix}_logs_hostname ON {table_name} (hostname)",
                    f"CREATE INDEX IF NOT EXISTS idx_{self.table_prefix}_logs_composite ON {table_name} (timestamp DESC, level, logger_name)",
                ]
                
                for index_sql in indexes:
                    try:
                        cursor.execute(index_sql)
                    except Exception as e:
                        # Index creation failures are not critical
                        print(f"Warning: Failed to create index: {e}", file=sys.stderr)
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Failed to initialize database schema: {e}", file=sys.stderr)
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            return False
        finally:
            # Always return connection to pool
            if conn:
                try:
                    self.connection_pool.putconn(conn)
                except:
                    pass

    @contextmanager
    def _get_connection(self):
        """
        Context manager for database connections with automatic retry.
        
        Yields:
            psycopg2.connection: Database connection from pool
            
        Raises:
            Exception: If connection cannot be established after retries
        """
        conn = None
        try:
            # Ensure we have a connection pool
            if not self._initialized or not self.connection_pool:
                if not self._connect_to_db():
                    raise Exception(f"Failed to establish database connection pool: {self._init_error}")
            
            # Get a connection from the pool
            conn = self.connection_pool.getconn()
            
            # Verify the connection is still valid
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
            except (OperationalError, InterfaceError):
                # Connection is stale, return it and get a new one
                self.connection_pool.putconn(conn, close=True)
                conn = self.connection_pool.getconn()
            
            yield conn
            
        except (OperationalError, InterfaceError) as e:
            # Connection lost, try to reconnect
            print(f"Database connection lost, attempting reconnection: {e}", file=sys.stderr)
            if conn:
                try:
                    self.connection_pool.putconn(conn, close=True)
                except:
                    pass
                conn = None
            
            if self._connect_to_db():
                conn = self.connection_pool.getconn()
                yield conn
            else:
                raise Exception(f"Failed to reconnect to database: {self._init_error}")
        finally:
            # Always return connection to pool
            if conn:
                try:
                    self.connection_pool.putconn(conn)
                except Exception as e:
                    print(f"Error returning connection to pool: {e}", file=sys.stderr)

    def _start_batch_worker(self):
        """Start the background thread for batch processing."""
        if self._batch_thread and self._batch_thread.is_alive():
            return
            
        self._batch_thread = threading.Thread(
            target=self._batch_worker,
            daemon=True,
            name=f"DatabaseLogBatch-{self.table_prefix}"
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
            batch: List of log record tuples
        """
        if not batch:
            return
            
        try:
            with self._get_connection() as conn:
                table_name = f"{self.table_prefix}_logs"
                
                with conn.cursor() as cursor:
                    cursor.executemany(
                        f"""
                        INSERT INTO {table_name} 
                        (timestamp, level, logger_name, process_id, thread_id, thread_name, 
                         hostname, message, exception, function_name, module, filename, lineno, pathname, extra_data)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        batch
                    )
                    conn.commit()
                    
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

    def _prepare_record_data(self, record) -> tuple:
        """
        Prepare log record data for database insertion.
        
        Args:
            record: LogRecord instance
            
        Returns:
            tuple: Data tuple ready for database insertion
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
        
        return (
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

    def _write_record_directly(self, record_data: tuple):
        """
        Write a single record directly to the database.
        
        Args:
            record_data: Prepared record data tuple
        """
        try:
            with self._get_connection() as conn:
                table_name = f"{self.table_prefix}_logs"
                
                with conn.cursor() as cursor:
                    cursor.execute(
                        f"""
                        INSERT INTO {table_name} 
                        (timestamp, level, logger_name, process_id, thread_id, thread_name, 
                         hostname, message, exception, function_name, module, filename, lineno, pathname, extra_data)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        record_data
                    )
                    conn.commit()
                    
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

    def _fallback_emit_from_data(self, record_data: tuple):
        """
        Emit fallback log from prepared record data.
        
        Args:
            record_data: Prepared record data tuple
        """
        try:
            timestamp, level, logger_name, _, _, _, hostname, message, exception, _, _, _, _, _, _ = record_data
            
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
            'retry_count': self._retry_count,
            'last_error': self._init_error,
            'hostname': self._hostname,
            'pid': self._pid,
            'table_name': f"{self.table_prefix}_logs",
            'batching_enabled': self.enable_batching,
            'batch_size': self.batch_size if self.enable_batching else None,
            'queue_size': self._batch_queue.qsize() if self.enable_batching else None,
            'pool_min_connections': self.min_pool_connections,
            'pool_max_connections': self.max_pool_connections
        }
        
        try:
            if self.connection_pool:
                # Test connection pool by getting and returning a connection
                conn = self.connection_pool.getconn()
                try:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                    status['connected'] = True
                finally:
                    self.connection_pool.putconn(conn)
        except:
            status['connected'] = False
            
        return status

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
        
        while not self._is_closing:
            try:
                # Sleep first to avoid immediate rotation on startup
                time.sleep(min(ROTATION_INTERVAL, 3600))  # Check every hour or at interval
                if not self._is_closing:
                    self._rotate_logs()
            except Exception as e:
                # Don't let the rotation thread die due to errors
                print(f"Error during log rotation: {str(e)}", file=sys.stderr)
                
    def _rotate_logs(self):
        """Delete logs older than retention_days."""
        if not self._initialized or self.retention_days <= 0:
            return
            
        try:
            # Calculate the cutoff date
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            table_name = f"{self.table_prefix}_logs"
            
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # First, count how many records will be deleted
                    cursor.execute(
                        f"SELECT COUNT(*) FROM {table_name} WHERE timestamp < %s",
                        (cutoff_date,)
                    )
                    count_to_delete = cursor.fetchone()[0]
                    
                    # Initialize total_deleted before conditional block
                    total_deleted = 0
                    
                    if count_to_delete > 0:
                        # Delete in chunks to avoid long-running transactions
                        chunk_size = 10000
                        
                        while True:
                            cursor.execute(
                                f"""
                                DELETE FROM {table_name} 
                                WHERE id IN (
                                    SELECT id FROM {table_name} 
                                    WHERE timestamp < %s 
                                    LIMIT %s
                                )
                                """,
                                (cutoff_date, chunk_size)
                            )
                            
                            deleted_in_chunk = cursor.rowcount
                            total_deleted += deleted_in_chunk
                            conn.commit()
                            
                            if deleted_in_chunk < chunk_size:
                                break
                                
                        print(f"Log rotation: Deleted {total_deleted} records older than {cutoff_date.isoformat()}", 
                              file=sys.stdout)
                    
                    # Also run VACUUM to reclaim space (optional)
                    if total_deleted > 1000:
                        try:
                            # Note: VACUUM cannot be run inside a transaction
                            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
                            cursor.execute(f"VACUUM ANALYZE {table_name}")
                            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
                        except Exception as vacuum_error:
                            print(f"VACUUM operation failed (non-critical): {vacuum_error}", file=sys.stderr)
                              
        except Exception as e:
            # If rotation fails, just log the error
            print(f"Failed to rotate logs: {str(e)}", file=sys.stderr)

    def close(self):
        """Close the database connection and cleanup resources."""
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
        
        # Close connection pool
        with self._connection_lock:
            if self.connection_pool:
                try:
                    self.connection_pool.closeall()
                except Exception as e:
                    print(f"Error closing database connection pool: {e}", file=sys.stderr)
                finally:
                    self.connection_pool = None
        
        super().close()