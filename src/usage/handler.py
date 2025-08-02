# -*- coding: utf-8 -*-
"""
Usage log handler module for PostgreSQL logging.

This module provides a custom logging handler that writes usage log records to
a PostgreSQL database. It handles connection management, table creation,
and implements fallback mechanisms when database operations fail.

Features:
- Automatic table creation
- Comprehensive record fields
- Reconnection attempts on database errors
"""
import logging
import psycopg2
import psycopg2.extras
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
from .dependencies import get_config
from config import Config


class UsageLogHandler(logging.Handler):
    """
    A robust custom logging handler that writes usage log records to PostgreSQL database.
    Features improved error handling, batching, and connection management.

    Features:
    - Automatic table creation with proper indexing
    - Connection pooling and reconnection with exponential backoff
    - Batched writes for better performance
    - Comprehensive record fields
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

    def __init__(self,
                 db_config:  Dict[str, Any],
                 table_prefix: str = "usage_",
                 batch_size: int = DEFAULT_BATCH_SIZE,
                 flush_interval: float = DEFAULT_FLUSH_INTERVAL,
                 enable_batching: bool = True):
        """
        Initialize the log handler with database connection parameters and settings.

        Args:
            db_config (Dict[str, Any]): Database connection configuration.
            table_prefix (str): Prefix for the usage log table.
            batch_size (int): Number of records to batch before writing to the database.
            flush_interval (float): Interval in seconds to flush batched records.
            enable_batching (bool): Whether to enable batching of log records.

        """
        super().__init__()
        self.db_config = db_config
        self.table_prefix = table_prefix
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.enable_batching = enable_batching

        # Connection management
        self.connection = None
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

        # Register cleanup on exit
        atexit.register(self.close)

    def _create_table(self):
        """Create the usage log table if it does not exist."""
        table_name = f"{self.table_prefix}_usage"

        create_table_query = sql.SQL("""
            CREATE TABLE IF NOT EXISTS {table} (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                api_type VARCHAR(50) NOT NULL,
                user_id VARCHAR(255) NOT NULL,
                model VARCHAR(255) NOT NULL,
                request_id VARCHAR(255),
                prompt_tokens INTEGER NOT NULL DEFAULT 0,
                completion_tokens INTEGER,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                input_count INTEGER,
                extra_data JSONB,
                hostname VARCHAR(255),
                process_id INTEGER,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
        """).format(table=sql.Identifier(table_name))

        with self.connection.cursor() as cursor:
            cursor.execute(create_table_query)

            # Create indexes for better query performance
            indexes = [
                f"CREATE INDEX IF NOT EXISTS idx_{table_name}_timestamp ON {table_name} (timestamp DESC)",
                f"CREATE INDEX IF NOT EXISTS idx_{table_name}_user_id ON {table_name} (user_id)",
                f"CREATE INDEX IF NOT EXISTS idx_{table_name}_api_type ON {table_name} (api_type)",
                f"CREATE INDEX IF NOT EXISTS idx_{table_name}_model ON {table_name} (model)",
                f"CREATE INDEX IF NOT EXISTS idx_{table_name}_user_timestamp ON {table_name} (user_id, timestamp DESC)",
            ]

            for index_query in indexes:
                cursor.execute(index_query)

    def _connect_to_db(self):
        """Establish a connection to the PostgreSQL database."""
        with self._connection_lock:
            # Check if we should retry (implement exponential backoff)
            current_time = time.time()
            if self._retry_count > 0:
                wait_time = min(
                    self.INITIAL_RETRY_DELAY *
                    (self.BACKOFF_MULTIPLIER ** (self._retry_count - 1)),
                    self.MAX_RETRY_DELAY
                )
                if current_time - self._last_retry_time < wait_time:
                    return False

            if self._retry_count >= self.MAX_RETRY_ATTEMPTS:
                return False

            try:
                # Close existing connection if any
                if self.connection:
                    try:
                        self.connection.close()
                    except:
                        pass

                # Create new connection
                self.connection = psycopg2.connect(
                    dbname=self.db_config.get(
                        'database', self.db_config.get('name')),
                    user=self.db_config.get(
                        'username', self.db_config.get('user')),
                    password=self.db_config['password'],
                    host=self.db_config['host'],
                    port=self.db_config.get('port', 5432),
                    sslmode=self.db_config.get('ssl_mode', 'prefer'),
                    connect_timeout=10,  # 10 second timeout
                    application_name=f"DatabaseUsageLogHandler-{self._pid}"
                )

                # Test the connection
                with self.connection.cursor() as cursor:
                    cursor.execute("SELECT 1")

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

                error_msg = f"Database connection attempt {self._retry_count}/{self.MAX_RETRY_ATTEMPTS} failed: {e}"
                print(error_msg, file=sys.stderr)

                return False

    def _initialize_schema(self) -> bool:
        """
        Initialize the database schema (create tables and indexes).

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Create the usage table with improved schema
            self._create_table()

            # Commit the changes
            self.connection.commit()
            return True

        except Exception as e:
            print(
                f"Failed to initialize database schema: {e}", file=sys.stderr)
            try:
                self.connection.rollback()
            except:
                pass
            return False

    @contextmanager
    def _get_connection(self):
        """
        Context manager for database connections with automatic retry.

        Yields:
            psycopg2.connection: Database connection

        Raises:
            Exception: If connection cannot be established after retries
        """
        with self._connection_lock:
            if not self._initialized or not self.connection or self.connection.closed:
                if not self._connect_to_db():
                    raise Exception(
                        f"Failed to establish database connection: {self._init_error}")

            try:
                yield self.connection
            except (OperationalError, InterfaceError) as e:
                # Connection lost, try to reconnect
                print(
                    f"Database connection lost, attempting reconnection: {e}", file=sys.stderr)
                if self._connect_to_db():
                    yield self.connection
                else:
                    raise Exception(
                        f"Failed to reconnect to database: {self._init_error}")

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
                table_name = f"{self.table_prefix}_usage"

                with conn.cursor() as cursor:
                    # Use psycopg2.extras.execute_values for batch insert
                    insert_query = sql.SQL("""
                        INSERT INTO {table} (
                            timestamp, api_type, user_id, model, request_id,
                            prompt_tokens, completion_tokens, total_tokens,
                            input_count, extra_data, hostname, process_id
                        ) VALUES %s
                    """).format(table=sql.Identifier(table_name))

                    psycopg2.extras.execute_values(
                        cursor, insert_query, batch, template=None, page_size=100
                    )
                    conn.commit()

        except Exception as e:
            print(f"Failed to flush batch to database: {e}", file=sys.stderr)
            # Fall back to individual logging for this batch
            for record_data in batch:
                try:
                    self._fallback_emit_from_data(record_data)
                except Exception as fallback_error:
                    print(
                        f"Fallback logging also failed: {fallback_error}", file=sys.stderr)

    def emit(self, record):
        """
        Emit a log record. Uses batching if enabled, otherwise writes directly.

        Args:
            record: LogRecord instance to emit
        """
        if self._is_closing:
            return

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
            'table_name': f"{self.table_prefix}_usage",
            'batching_enabled': self.enable_batching,
            'batch_size': self.batch_size if self.enable_batching else None,
            'queue_size': self._batch_queue.qsize() if self.enable_batching else None
        }

        try:
            if self.connection and not self.connection.closed:
                with self.connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    status['connected'] = True
        except:
            status['connected'] = False

        return status

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
                print(
                    f"Error during batch worker shutdown: {e}", file=sys.stderr)

        # Close database connection
        with self._connection_lock:
            if self.connection:
                try:
                    self.connection.close()
                except Exception as e:
                    print(
                        f"Error closing database connection: {e}", file=sys.stderr)
                finally:
                    self.connection = None

        super().close()

    def _prepare_record_data(self, record) -> tuple:
        """
        Prepare log record data for database insertion.

        Args:
            record: LogRecord instance

        Returns:
            tuple: Prepared data tuple for database insertion
        """
        try:
            # Extract usage data from the log record
            # Expect the record to have a 'usage_data' attribute or message in JSON format
            if hasattr(record, 'usage_data') and record.usage_data:
                usage_data = record.usage_data
            else:
                # Try to parse JSON from the message
                try:
                    usage_data = json.loads(record.getMessage())
                except (json.JSONDecodeError, ValueError):
                    # Fallback to basic record info
                    usage_data = {
                        'api_type': getattr(record, 'api_type', 'unknown'),
                        'user_id': getattr(record, 'user_id', 'unknown'),
                        'model': getattr(record, 'model', 'unknown'),
                        'prompt_tokens': getattr(record, 'prompt_tokens', 0),
                        'total_tokens': getattr(record, 'total_tokens', 0),
                    }

            # Extract fields with defaults
            timestamp = usage_data.get('timestamp')
            if timestamp is None:
                timestamp = datetime.fromtimestamp(record.created)
            elif isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(
                    timestamp.replace('Z', '+00:00'))

            api_type = usage_data.get('api_type', 'unknown')
            user_id = usage_data.get('user_id', 'unknown')
            model = usage_data.get('model', 'unknown')
            request_id = usage_data.get('request_id')
            prompt_tokens = int(usage_data.get('prompt_tokens', 0))
            completion_tokens = usage_data.get('completion_tokens')
            if completion_tokens is not None:
                completion_tokens = int(completion_tokens)
            total_tokens = int(usage_data.get('total_tokens', 0))
            input_count = usage_data.get('input_count')
            if input_count is not None:
                input_count = int(input_count)

            # Handle extra_data
            extra_data = usage_data.get('extra_data')
            if extra_data is not None:
                extra_data = json.dumps(extra_data) if not isinstance(
                    extra_data, str) else extra_data

            return (
                timestamp,
                api_type,
                user_id,
                model,
                request_id,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                input_count,
                extra_data,
                self._hostname,
                self._pid
            )

        except Exception as e:
            print(f"Error preparing record data: {e}", file=sys.stderr)
            # Return minimal valid record
            return (
                datetime.fromtimestamp(record.created),
                'unknown',
                'unknown',
                'unknown',
                None,
                0,
                None,
                0,
                None,
                None,
                self._hostname,
                self._pid
            )

    def _write_record_directly(self, record_data: tuple):
        """
        Write a single record directly to the database.

        Args:
            record_data: Tuple of record data
        """
        try:
            with self._get_connection() as conn:
                table_name = f"{self.table_prefix}_usage"

                with conn.cursor() as cursor:
                    insert_query = sql.SQL("""
                        INSERT INTO {table} (
                            timestamp, api_type, user_id, model, request_id,
                            prompt_tokens, completion_tokens, total_tokens,
                            input_count, extra_data, hostname, process_id
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """).format(table=sql.Identifier(table_name))

                    cursor.execute(insert_query, record_data)
                    conn.commit()

        except Exception as e:
            print(
                f"Failed to write record directly to database: {e}", file=sys.stderr)
            self._fallback_emit_from_data(record_data)

    def _fallback_emit_from_data(self, record_data: tuple):
        """
        Fallback method to emit log record data when database write fails.
        This writes to a local file as backup.

        Args:
            record_data: Tuple of record data
        """
        try:
            # Create a fallback log entry
            fallback_record = {
                'timestamp': record_data[0].isoformat() if record_data[0] else None,
                'api_type': record_data[1],
                'user_id': record_data[2],
                'model': record_data[3],
                'request_id': record_data[4],
                'prompt_tokens': record_data[5],
                'completion_tokens': record_data[6],
                'total_tokens': record_data[7],
                'input_count': record_data[8],
                'extra_data': record_data[9],
                'hostname': record_data[10],
                'process_id': record_data[11]
            }

            # Write to fallback file
            fallback_file = f"/tmp/usage_log_fallback_{self.table_prefix}.jsonl"
            with open(fallback_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(fallback_record) + '\n')

        except Exception as e:
            print(f"Fallback logging failed: {e}", file=sys.stderr)
            # Last resort: print to stderr
            print(f"LOST LOG RECORD: {record_data}", file=sys.stderr)


def create_usage_log_handler(config):
    """
    Factory function to create a DatabaseLogHandler instance.

    Args:
        config: Configuration object containing database connection details.

    Returns:
        An instance of UsageLogHandler configured with the provided settings.
    """
    if not config.database:
        return None
        
    db_config = {
        "host": config.database.host,
        "port": config.database.port,
        "username": config.database.username,
        "user": config.database.username,  # Some parts expect 'user'
        "password": config.database.password,
        "database": config.database.database,
        "name": config.database.database,  # Some parts expect 'name'
        "ssl_mode": "prefer",  # Default SSL mode
    }

    return UsageLogHandler(
        db_config=db_config,
        table_prefix=getattr(config, 'get_table_prefix', lambda: "usage_")(),
        batch_size=getattr(config, 'get_log_batch_size', lambda: UsageLogHandler.DEFAULT_BATCH_SIZE)(),
        flush_interval=getattr(config, 'get_log_flush_interval', lambda: UsageLogHandler.DEFAULT_FLUSH_INTERVAL)(),
        enable_batching=getattr(config, 'get_enable_batching', lambda: True)()  # Re-enable batching
    )
