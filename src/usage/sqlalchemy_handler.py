# -*- coding: utf-8 -*-
"""
SQLAlchemy-based Usage log handler for centralized database.

This module provides a custom logging handler that writes usage log records
using the centralized database module with SQLAlchemy ORM.
"""
import logging
import sys
import traceback
import socket
import os
from datetime import datetime
import threading
import time
import json
import queue
import atexit
from typing import Dict, Any, Optional

from database import get_db_session
from database.schema import UsageLogDB


class SQLAlchemyUsageLogHandler(logging.Handler):
    """
    A robust custom logging handler that writes usage log records using SQLAlchemy.
    Features improved error handling, batching, and connection management.
    """

    # Batching settings
    DEFAULT_BATCH_SIZE = 50
    DEFAULT_FLUSH_INTERVAL = 5.0  # seconds

    def __init__(self,
                 config=None,
                 batch_size: int = DEFAULT_BATCH_SIZE,
                 flush_interval: float = DEFAULT_FLUSH_INTERVAL,
                 enable_batching: bool = True):
        """
        Initialize the log handler with configuration and settings.

        Args:
            config: Configuration object
            batch_size: Number of records to batch before writing
            flush_interval: Interval in seconds to flush batched records
            enable_batching: Whether to enable batching of log records
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
        self._initialized = True
        self._is_closing = False

        # Batching components
        if self.enable_batching:
            self._batch_queue = queue.Queue(maxsize=batch_size * 2)
            self._batch_thread = None
            self._start_batch_worker()

        # Register cleanup on exit
        atexit.register(self.close)

    def _start_batch_worker(self):
        """Start the background thread for batch processing."""
        if self._batch_thread and self._batch_thread.is_alive():
            return

        self._batch_thread = threading.Thread(
            target=self._batch_worker,
            daemon=True,
            name="SQLAlchemyUsageBatch"
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
            with get_db_session() as session:
                # Create UsageLogDB objects
                usage_logs = []
                for record_data in batch:
                    usage_log = UsageLogDB(**record_data)
                    usage_logs.append(usage_log)

                # Bulk insert
                session.bulk_save_objects(usage_logs)
                session.commit()

        except Exception as e:
            print(f"Failed to flush batch to database: {e}", file=sys.stderr)
            traceback.print_exc()
            # Fall back to individual logging for this batch
            for record_data in batch:
                try:
                    self._fallback_emit_from_data(record_data)
                except Exception as fallback_error:
                    print(f"Fallback logging also failed: {fallback_error}", file=sys.stderr)

    def emit(self, record):
        """
        Emit a log record. Uses batching if enabled, otherwise writes directly.

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
            # Last resort: log to stderr
            print(f"Failed to emit usage log record: {e}", file=sys.stderr)
            # Call default handleError to allow Python logging to handle it
            self.handleError(record)

    def flush(self):
        """Force flush any pending log records."""
        if self.enable_batching and self._batch_queue:
            # Signal the batch worker to flush immediately
            try:
                self._batch_queue.put_nowait(('FLUSH_SIGNAL',))
            except queue.Full:
                pass

        # Call parent flush
        super().flush()

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

    def _prepare_record_data(self, record) -> dict:
        """
        Prepare log record data for database insertion.

        Args:
            record: LogRecord instance

        Returns:
            dict: Prepared data dictionary for database insertion
        """
        try:
            # Extract usage data from the log record
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
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

            # Handle extra_data
            extra_data = usage_data.get('extra_data')
            if extra_data is not None and not isinstance(extra_data, dict):
                try:
                    extra_data = json.loads(extra_data) if isinstance(extra_data, str) else dict(extra_data)
                except:
                    extra_data = None

            return {
                'timestamp': timestamp,
                'api_type': usage_data.get('api_type', 'unknown'),
                'user_id': usage_data.get('user_id', 'unknown'),
                'model': usage_data.get('model', 'unknown'),
                'request_id': usage_data.get('request_id'),
                'prompt_tokens': int(usage_data.get('prompt_tokens', 0)),
                'completion_tokens': int(usage_data.get('completion_tokens')) if usage_data.get('completion_tokens') is not None else None,
                'total_tokens': int(usage_data.get('total_tokens', 0)),
                'input_count': int(usage_data.get('input_count')) if usage_data.get('input_count') is not None else None,
                'extra_data': extra_data,
                'hostname': self._hostname,
                'process_id': self._pid
            }

        except Exception as e:
            print(f"Error preparing record data: {e}", file=sys.stderr)
            # Return minimal valid record
            return {
                'timestamp': datetime.fromtimestamp(record.created),
                'api_type': 'unknown',
                'user_id': 'unknown',
                'model': 'unknown',
                'request_id': None,
                'prompt_tokens': 0,
                'completion_tokens': None,
                'total_tokens': 0,
                'input_count': None,
                'extra_data': None,
                'hostname': self._hostname,
                'process_id': self._pid
            }

    def _write_record_directly(self, record_data: dict):
        """
        Write a single record directly to the database.

        Args:
            record_data: Dictionary of record data
        """
        try:
            with get_db_session() as session:
                usage_log = UsageLogDB(**record_data)
                session.add(usage_log)
                session.commit()

        except Exception as e:
            print(f"Failed to write record directly to database: {e}", file=sys.stderr)
            self._fallback_emit_from_data(record_data)

    def _fallback_emit_from_data(self, record_data: dict):
        """
        Fallback method to emit log record data when database write fails.
        This writes to a local file as backup.

        Args:
            record_data: Dictionary of record data
        """
        try:
            # Create a fallback log entry
            fallback_record = {
                'timestamp': record_data['timestamp'].isoformat() if record_data.get('timestamp') else None,
                'api_type': record_data.get('api_type'),
                'user_id': record_data.get('user_id'),
                'model': record_data.get('model'),
                'request_id': record_data.get('request_id'),
                'prompt_tokens': record_data.get('prompt_tokens'),
                'completion_tokens': record_data.get('completion_tokens'),
                'total_tokens': record_data.get('total_tokens'),
                'input_count': record_data.get('input_count'),
                'extra_data': record_data.get('extra_data'),
                'hostname': record_data.get('hostname'),
                'process_id': record_data.get('process_id')
            }

            # Write to fallback file
            fallback_file = "/tmp/usage_log_fallback.jsonl"
            with open(fallback_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(fallback_record) + '\n')

        except Exception as e:
            print(f"Fallback logging failed: {e}", file=sys.stderr)
            # Last resort: print to stderr
            print(f"LOST LOG RECORD: {record_data}", file=sys.stderr)


def create_usage_log_handler(config):
    """
    Factory function to create a SQLAlchemyUsageLogHandler instance.

    Args:
        config: Configuration object containing database connection details.

    Returns:
        An instance of SQLAlchemyUsageLogHandler configured with the provided settings.
    """
    if not config or not config.database:
        return None

    return SQLAlchemyUsageLogHandler(
        config=config,
        batch_size=getattr(config, 'get_log_batch_size', lambda: SQLAlchemyUsageLogHandler.DEFAULT_BATCH_SIZE)(),
        flush_interval=getattr(config, 'get_log_flush_interval', lambda: SQLAlchemyUsageLogHandler.DEFAULT_FLUSH_INTERVAL)(),
        enable_batching=getattr(config, 'get_enable_batching', lambda: True)()
    )
