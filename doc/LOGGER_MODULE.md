# LOGGER Module Documentation

## Overview

The LOGGER module provides a comprehensive, configurable logging system for the application. It supports multiple logging backends including console output and PostgreSQL database storage, with features like asynchronous logging, automatic log rotation, and graceful fallback mechanisms.

## Features

- **Multi-Backend Support**: Console and PostgreSQL database logging
- **Asynchronous Logging**: Queue-based batched writes for better performance
- **Database Integration**: Automatic table creation and schema management
- **Log Rotation**: Automatic cleanup based on retention policy
- **Component-Specific Levels**: Different log levels per application component
- **Graceful Fallback**: Automatic fallback to console when database fails
- **Thread-Safe Operations**: Safe for use in multi-threaded applications
- **Connection Resilience**: Automatic reconnection with exponential backoff
- **Structured Logging**: Rich log records with metadata and context

## Module Structure

```
src/logger/
├── __init__.py          # Module initialization and public API
├── manager.py           # LoggerManager class for centralized configuration  
├── handlers.py          # Handler factory functions
└── log_handler.py       # DatabaseLogHandler implementation
```

## Core Components

### LoggerManager
Central manager that handles configuration and setup of all loggers with:
- Automatic configuration loading from CONFIG module
- Component-specific log level management
- Thread-safe logger creation and caching
- Graceful shutdown handling

### DatabaseLogHandler
Custom PostgreSQL logging handler featuring:
- Automatic table creation with proper indexing
- Batched writes for performance optimization
- Connection pooling with retry logic
- Comprehensive log record fields
- Fallback to console on database errors

### Handler Factories
Factory functions for creating different handler types:
- Console handlers with configurable formatting
- Database handlers with configuration validation
- File handlers with rotation support

## Database Schema

The module automatically creates a logs table with the following structure:

```sql
CREATE TABLE {prefix}_logs (
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
);
```

### Indexes
Automatically created indexes for optimal query performance:
- `idx_{prefix}_logs_timestamp` - Timestamp descending
- `idx_{prefix}_logs_level` - Log level
- `idx_{prefix}_logs_logger` - Logger name  
- `idx_{prefix}_logs_hostname` - Hostname
- `idx_{prefix}_logs_composite` - Combined timestamp, level, logger

## Usage Examples

### Basic Logger Setup
```python
from logger import initialize_logger, get_logger

# Initialize the logging system
if initialize_logger():
    # Get a logger for your component
    logger = get_logger("my_component")
    
    # Log messages at different levels
    logger.debug("Debug information")
    logger.info("General information")
    logger.warning("Warning message")
    logger.error("Error occurred")
    logger.critical("Critical error")
else:
    print("Failed to initialize logging system")
```

### Component-Specific Logging
```python
from logger import get_logger

# Get loggers for different components
auth_logger = get_logger("authentication")
db_logger = get_logger("database") 
api_logger = get_logger("apikey")

# Each logger respects its configured level from config.yml
auth_logger.debug("Authentication debug info")  # May be visible if DEBUG level
db_logger.info("Database operation completed")   # Visible if INFO or lower
api_logger.error("API key validation failed")    # Always visible
```

### Exception Logging
```python
from logger import get_logger
import traceback

logger = get_logger("error_handler")

try:
    # Some operation that might fail
    result = risky_operation()
except Exception as e:
    # Log with full stack trace
    logger.error(f"Operation failed: {e}", exc_info=True)
    
    # Or log exception details manually
    logger.error(f"Error: {e}\nTraceback: {traceback.format_exc()}")
```

### Structured Logging with Extra Data
```python
from logger import get_logger

logger = get_logger("api")

# Log with additional context data
logger.info("User login", extra={
    "user_id": 123,
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0...",
    "session_id": "abc123"
})

# The extra data is stored in the extra_data JSONB field
```

### Application Shutdown
```python
from logger import shutdown_logging

# Gracefully shutdown logging (flushes batches, closes connections)
shutdown_logging()
```

## Configuration Integration

The LOGGER module integrates with the CONFIG module for settings:

### Required Configuration
```yaml
logging:
  level: "DEBUG"                    # Global log level
  database:
    enabled: true                   # Enable database logging
    retention_days: 365             # Log retention period
  console:
    enabled: true                   # Enable console logging
    format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  components:
    authentication: "DEBUG"         # Component-specific levels
    database: "INFO"
    apikey: "INFO"
    models: "WARNING"
```

### Database Configuration
Uses database settings from CONFIG module:
```yaml
database:
  host: "postgres"
  port: 5432
  username: "postgresql"
  password: "password"
  database: "ai_platform_auth"
  table_prefix: "myopenaiapi"
```

## Advanced Features

### Batched Database Writes
The DatabaseLogHandler uses batching for performance:
- **Batch Size**: 50 records per batch (configurable)
- **Flush Interval**: 5 seconds maximum wait time
- **Queue Management**: Non-blocking queues with overflow handling
- **Background Thread**: Dedicated worker thread for batch processing

### Connection Resilience
Robust connection management with:
- **Retry Logic**: Up to 5 retry attempts with exponential backoff
- **Health Checks**: Connection validation before use
- **Automatic Reconnection**: Transparent reconnection on connection loss
- **Timeout Handling**: 10-second connection timeout

### Log Rotation
Automatic log cleanup based on retention policy:
- **Configurable Retention**: Set retention period in days
- **Background Cleanup**: Periodic cleanup of old log records
- **Performance Optimized**: Uses efficient DELETE queries with indexes

### Fallback Mechanisms
Multiple fallback layers ensure logging never fails:
1. **Database Primary**: Attempt database logging first
2. **Console Fallback**: Fall back to console if database fails
3. **Emergency Logging**: Print to stderr as last resort
4. **Graceful Degradation**: Continue operation even if logging fails

## Performance Considerations

### Batching Benefits
- **Reduced I/O**: Fewer database connections and queries
- **Better Throughput**: Higher sustained logging rates
- **Lower Latency**: Non-blocking log calls for application code
- **Connection Efficiency**: Reuse connections across batches

### Memory Management
- **Bounded Queues**: Prevents unlimited memory growth
- **Queue Overflow**: Graceful handling when queues are full
- **Background Processing**: Separate thread doesn't block main application
- **Automatic Cleanup**: Resources cleaned up on shutdown

## Error Handling

### Database Errors
- **Connection Failures**: Automatic retry with exponential backoff
- **Schema Issues**: Automatic table and index creation
- **Write Failures**: Fallback to console logging
- **Timeout Handling**: Configurable connection and query timeouts

### Application Errors
- **Logger Initialization**: Safe failure with error reporting
- **Configuration Issues**: Graceful degradation with defaults
- **Resource Exhaustion**: Queue overflow protection
- **Shutdown Handling**: Clean resource cleanup

## Monitoring and Debugging

### Log Fields
Each log record includes comprehensive metadata:
- **Timing**: Precise timestamp with timezone
- **Source**: Logger name, function, filename, line number
- **Process**: Process ID, thread ID, thread name
- **System**: Hostname for distributed system tracking
- **Context**: Exception details, extra data in JSON format

### Performance Metrics
Monitor logging system health:
- **Batch Queue Size**: Monitor queue depth
- **Flush Frequency**: Track batch processing rate
- **Connection Status**: Monitor database connection health
- **Error Rates**: Track fallback usage and error frequency

## Integration with Other Modules

### CONFIG Module
- Loads logging configuration settings
- Gets database connection parameters
- Retrieves component-specific log levels

### Database Modules
- Shares database connection configuration
- Uses same table prefix scheme
- Coordinates with other database operations

### All Application Components
- Provides logging services to all modules
- Maintains consistent logging format
- Enables centralized log management

## Troubleshooting

### Common Issues

**Database Connection Failures**
- Check database configuration in config.yml
- Verify PostgreSQL server is running and accessible
- Confirm credentials and database permissions

**Missing Log Records**
- Check if database logging is enabled in configuration
- Verify table creation permissions
- Monitor for connection errors in console output

**Performance Issues**
- Adjust batch size and flush interval
- Monitor queue depth and processing rate
- Consider increasing database connection pool size

**Configuration Problems**
- Validate YAML syntax in config.yml
- Check for missing required configuration sections
- Verify log level names are valid Python logging levels