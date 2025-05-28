# Logging System Documentation

## Overview

The logging system provides a robust, configurable logging infrastructure with support for console, file, and PostgreSQL database backends. It offers asynchronous logging capabilities, structured logging, log filtering, automatic database log rotation, and comprehensive fallback mechanisms.

## Features

- **Multi-backend support**: Log to console, files, and PostgreSQL simultaneously
- **Asynchronous logging**: Non-blocking logging through queue handlers
- **Database integration**: Structured logs stored in PostgreSQL for easy querying
- **Automatic fallback**: Gracefully falls back to console logging on database errors
- **Comprehensive logging**: Captures hostname, thread info, stack traces, and other diagnostic data
- **Configurable**: Easily configurable through the application's config system
- **Log rotation**: Automatic log rotation for both file and database backends
- **Structured logging**: Support for adding consistent context to logs
- **Component-specific log levels**: Configure different log levels for different components
- **Filtering**: Filter logs by logger name
- **Context managers**: Temporarily change log levels for specific code sections
- **Usage tracking**: Track API usage metrics including token counts and request volumes
- **Usage statistics API**: RESTful API for retrieving usage statistics by user and time period

## Configuration

Logging settings can be configured in `asset/config.yml`:

```yaml
logging:
  level: "INFO"  # Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
  use_database: true  # Whether to log to the database
  async_logging: true  # Use asynchronous logging for better performance
  table_prefix: "oauth2"  # Prefix for log tables in the database
  log_retention_days: 30  # How many days to keep logs in the database
  console:
    enabled: true  # Always log to console as a fallback
    format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  components:
    auth: "INFO"
    database: "INFO"
    middleware: "INFO"
    controller: "WARNING"
```

### Database Logging Configuration

The system requires database configuration in the same config file if database logging is enabled:

```yaml
database:
  engine: "postgresql"
  host: "localhost"  
  port: 5432
  username: "postgres"    
  password: "password" 
  name: "ai_platform_auth"        
  ssl_mode: "prefer"
```

### File Logging Configuration

File logging is disabled by default but can be enabled by passing `log_to_file=True` to the `setup_logging` function. The log files are automatically rotated when they reach 10MB, with up to 5 backup files kept.

You can specify a custom file path or use the default path in `/workspace/logs/[service_name].log`.

### Component-Specific Log Levels

You can configure different log levels for different components in the application:

```yaml
logging:
  # ... other settings ...
  components:
    auth: "INFO"         # src.auth module will use INFO level
    database: "DEBUG"    # src.database module will use DEBUG level
    middleware: "INFO"   # src.middleware module will use INFO level
    controller: "WARNING"  # src.controller module will use WARNING level
```

## Database Schema

When database logging is enabled, the system creates a table with the following schema:

```sql
CREATE TABLE IF NOT EXISTS {table_prefix}_logs (
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
    pathname TEXT
)
```

## API Reference

### Logger Setup

#### `setup_logging(level=None, use_db=None, async_logging=None, service_name=None, log_to_file=False, file_path=None)`

Set up the logging system with console, file, and PostgreSQL support when available.

- **Args**:
  - `level`: The logging level to use (defaults to config setting or INFO)
  - `use_db`: Whether to attempt database logging (defaults to config setting)
  - `async_logging`: Whether to use asynchronous logging (defaults to config setting)
  - `service_name`: Name of the service for the logger (defaults to config setting)
  - `log_to_file`: Whether to log to a file (defaults to False)
  - `file_path`: Path to the log file (defaults to `/workspace/logs/[service_name].log`)

### Logging Usage

#### `get_logger(name)`

Get a logger with the specified name.

- **Args**:
  - `name`: The name for the logger

- **Returns**:
  - `logging.Logger`: A configured logger instance

#### `get_structured_logger(name, extra=None)`

Get a structured logger with pre-configured context data.

- **Args**:
  - `name`: The name for the logger
  - `extra`: A dictionary of structured data to include with all log messages

- **Returns**:
  - `StructuredLoggerAdapter`: A logger adapter instance with the extra context

#### `LogLevelContext`

Context manager for temporarily changing the log level of a logger.

```python
with LogLevelContext(logger, logging.DEBUG):
    # All logs in this block will use DEBUG level
    logger.debug("Detailed debugging information")
```

#### `add_logger_filter(handler=None, includes=None, excludes=None)`

Add a filter to a handler or the root logger to filter by logger name.

- **Args**:
  - `handler`: The handler to add the filter to, or None to add to all root handlers
  - `includes`: List of logger name prefixes to include
  - `excludes`: List of logger name prefixes to exclude

- **Returns**:
  - `LoggerNameFilter`: The created filter

### Database Handler

#### `DatabaseLogHandler`

A custom logging handler that writes log records to PostgreSQL database with fallback to console logging.

- **Constructor Args**:
  - `db_config`: Database configuration dictionary
  - `table_prefix`: Prefix for the logs table

- **Key Methods**:
  - `emit(record)`: Sends a log record to the database, falls back to console on failure
  - `close()`: Closes the database connection when the handler is closed

## Usage Examples

### Basic Usage

```python
from logger import get_logger

# Create a logger for your module
logger = get_logger(__name__)

# Log messages at different levels
logger.debug("Debug message with detailed information")
logger.info("Informational message about normal operation")
logger.warning("Warning about potential issues")
logger.error("Error message when something fails")
logger.critical("Critical error affecting the entire application")
```

### Logging Exceptions

```python
from logger import get_logger

logger = get_logger(__name__)

try:
    # Some code that might raise an exception
    result = 1 / 0
except Exception as e:
    # Log the exception with traceback
    logger.exception(f"An error occurred: {str(e)}")
    
    # Alternative way to log with exception info
    logger.error(f"Failed to process data: {str(e)}", exc_info=True)
```

### Custom Logger Setup

```python
from logger import setup_logging, get_logger

# Configure logging with custom settings
setup_logging(
    level="DEBUG",
    use_db=True,
    async_logging=True,
    service_name="my_service",
    log_to_file=True,
    file_path="/var/log/myapp/app.log"
)

logger = get_logger("custom_module")
logger.info("Logger initialized with custom settings")
```

### Structured Logging

```python
from logger import get_structured_logger

# Create a request-specific logger with context
request_logger = get_structured_logger(
    "api.request", 
    {
        "request_id": "req-123",
        "endpoint": "/users",
        "method": "POST",
        "client_ip": "192.168.1.100"
    }
)

# All these logs will include the request context
request_logger.info("Request received")
request_logger.debug("Validating request body")
request_logger.info("Request processed successfully")
```

### Temporary Log Level Changes

```python
from logger import get_logger, LogLevelContext
import logging

logger = get_logger(__name__)

# Temporarily increase verbosity for a complex operation
with LogLevelContext(logger, logging.DEBUG):
    logger.debug("Starting complex operation")
    # Perform the operation with detailed logging
    logger.debug("Complex operation completed")

# Back to original level
logger.debug("This may not be logged if original level was higher")
```

### Log Filtering

```python
from logger import get_logger, add_logger_filter

# Add a filter to only show logs from certain modules
add_logger_filter(
    includes=["api.users", "api.auth"],
    excludes=["api.users.validation"]
)

# These will be logged based on the filter
users_logger = get_logger("api.users")
auth_logger = get_logger("api.auth")
validation_logger = get_logger("api.users.validation")

users_logger.info("This will be logged")       # Included
auth_logger.info("This will be logged")        # Included
validation_logger.info("This won't be logged") # Excluded
```

## Best Practices

1. **Use Module-Specific Loggers**: 
   - Create a logger for each module using `get_logger(__name__)` to easily identify the source of log messages.

2. **Choose Appropriate Log Levels**:
   - `DEBUG`: Detailed information for diagnosing problems
   - `INFO`: Confirmation that things are working as expected
   - `WARNING`: Indication that something unexpected happened or may happen
   - `ERROR`: Due to a more serious problem, the software couldn't perform some function
   - `CRITICAL`: A serious error indicating that the program itself may be unable to continue running

3. **Include Context in Log Messages**:
   - Log messages should include enough context to be useful without being overwhelming.
   - Include identifiers (request IDs, user IDs, etc.) to correlate related log entries.

4. **Handle Sensitive Information**:
   - Never log passwords, tokens, or other sensitive information.
   - Implement sanitization for user input that might contain sensitive data.

5. **Database Considerations**:
   - Implement log rotation or cleaning for database logs to prevent unbounded growth.
   - Create indexes on commonly queried fields like `timestamp`, `level`, and `logger_name`.

## Advanced Features

### Asynchronous Logging

The logging system uses Python's `QueueHandler` and `QueueListener` for asynchronous logging, which:

- Prevents logging operations from blocking the main application thread
- Improves application performance, especially with database logging
- Handles bursts of log messages efficiently

When `async_logging` is enabled, log records are placed in a queue and processed by a separate thread.

### Fallback Mechanism

The database logging handler implements a robust fallback mechanism:

1. If the initial database connection fails, it falls back to console logging
2. If a log record can't be written to the database, it attempts to reconnect
3. If reconnection fails, it logs to the console as a fallback
4. It marks error messages to prevent duplicate database error logs

This ensures that log messages are never lost, even when the database is temporarily unavailable.

### Automatic Log Rotation

#### Database Log Rotation

The system automatically cleans up old log entries from the database based on the `log_retention_days` configuration:

- A background thread runs once per day to delete old logs
- Only logs older than the specified retention period are deleted
- The process is graceful and continues even if rotation temporarily fails

#### File Log Rotation

When file logging is enabled, the system uses Python's `RotatingFileHandler`:

- Log files are automatically rotated when they reach 10MB in size
- Up to 5 backup log files are kept (configurable)
- When the maximum number of backups is reached, the oldest is deleted

### Structured Logging

Structured logging adds consistent contextual information to logs:

- Attach metadata like request IDs, user IDs, or session information
- All logs from the structured logger automatically include the context
- Context data is stored in JSON format in the database's `extra_data` field
- Context data is preserved across handler types (console, file, database)

### Thread Safety

All logging operations are thread-safe:

- Database connections use thread locks to prevent concurrent access issues
- Log rotation operations are protected by locks
- The asynchronous queue system handles concurrent logging from multiple threads

## Usage Tracking and Statistics API

The logging system includes specialized components for API usage tracking and statistics:

- **UsageLogger**: Tracks API usage metrics (tokens, requests) in a dedicated database table
- **Usage Statistics API**: Provides REST endpoints for retrieving usage statistics

For detailed documentation on the Usage Statistics API, see [USAGE_STATISTICS.md](/workspace/doc/USAGE_STATISTICS.md).