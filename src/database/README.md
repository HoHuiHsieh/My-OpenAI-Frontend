# Database Module

The database module provides centralized database connection management and table initialization for all application modules.

## Overview

This module consolidates database operations using SQLAlchemy and provides:

- **Connection Pooling**: Efficient connection management with configurable pool settings
- **Table Initialization**: Automatic table creation for all modules (apikey, logger, oauth2, usage)
- **Schema Management**: Centralized schema definitions using SQLAlchemy ORM
- **Session Management**: Context managers for safe database operations

## Architecture

```
src/database/
├── __init__.py      # Main module exports and connection pool management
├── handler.py       # Table initialization handler
└── schema.py        # SQLAlchemy table schema definitions
```

## Features

### 1. Connection Pooling

The module uses SQLAlchemy's QueuePool with optimized settings:

- **pool_size**: 10 permanent connections
- **max_overflow**: 20 temporary connections
- **pool_timeout**: 30 seconds wait time
- **pool_recycle**: 3600 seconds (1 hour) connection lifetime
- **pool_pre_ping**: Connection health check before use

### 2. Table Schemas

All table schemas are defined in `schema.py`:

- **ApiKeyDB**: API key management (`{prefix}_api_keys`)
- **LogDB**: Application logs (`{prefix}_logs`)
- **UserDB**: OAuth2 users (`{prefix}_users`)
- **RefreshTokenDB**: OAuth2 refresh tokens (`{prefix}_refresh_tokens`)
- **UsageLogDB**: API usage tracking (`{prefix}_usage`)

### 3. Safe Table Initialization

The initialization handler:
- Checks for existing tables before creation
- Creates only missing tables
- **Does NOT modify existing table data**
- Creates indexes for optimal query performance
- Provides detailed logging of initialization process

## Usage

### Initialize Database (Application Startup)

```python
from database import init_database, close_database

# Initialize all tables
init_database()

# On shutdown
close_database()
```

### Get Database Session (Recommended for ORM)

```python
from database import get_db_session
from database.schema import UserDB

# Using context manager (automatic commit/rollback)
with get_db_session() as session:
    user = session.query(UserDB).filter_by(username='admin').first()
    # Session is automatically committed on success
    # and rolled back on error
```

### Get Raw Database Connection

```python
from database import get_db_connection

# For raw SQL operations
with get_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    results = cursor.fetchall()
    # Connection is automatically returned to pool
```

### FastAPI Dependency Injection

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from database import get_db
from database.schema import UserDB

@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    return db.query(UserDB).all()
```

### Check Connection Pool Status

```python
from database import get_connection_pool_status

status = get_connection_pool_status()
print(f"Pool size: {status['size']}")
print(f"Checked out: {status['checked_out']}")
print(f"Overflow: {status['overflow']}")
print(f"Available: {status['checkedin']}")
```

## Integration with Existing Modules

The database module is designed to work alongside existing module database implementations:

### API Key Module
- Existing: `src/apikey/database.py`
- New Schema: `database.schema.ApiKeyDB`
- The existing module can continue to work, or be updated to import from `database.schema`

### Logger Module
- Existing: `src/logger/log_handler.py` (uses psycopg2)
- New Schema: `database.schema.LogDB`
- Logger handler continues to work with psycopg2, new schema for reference

### OAuth2 Module
- Existing: `src/oauth2/database.py`
- New Schemas: `database.schema.UserDB`, `database.schema.RefreshTokenDB`
- OAuth2 already uses the shared engine pattern

### Usage Module
- Existing: `src/usage/handler.py` (uses psycopg2)
- New Schema: `database.schema.UsageLogDB`
- Usage handler continues to work with psycopg2, new schema for reference

## Table Initialization Process

When `init_database()` is called:

1. **Connect to Database**: Creates engine with connection pooling
2. **Check Existing Tables**: Inspects database to find existing tables
3. **Create Missing Tables**: Creates only tables that don't exist
4. **Create Indexes**: Adds indexes for query optimization
5. **Log Results**: Reports success/failure for each module

Example output:
```
Initializing database tables...
Table 'app_api_keys' already exists, skipping creation
Creating table 'app_logs'...
Successfully created table 'app_logs'
Table 'app_users' already exists, skipping creation
Table 'app_refresh_tokens' already exists, skipping creation
Creating table 'app_usage'...
Successfully created table 'app_usage'
All database tables initialized successfully
```

## Configuration

The module uses the application's configuration from `config` module:

```python
from config import get_config

config = get_config()

# Database connection string
db_url = config.get_database_connection_string()

# Table prefix
table_prefix = config.get_table_prefix()
```

Required configuration in `config.yml`:
```yaml
database:
  host: localhost
  port: 5432
  username: postgres
  password: password
  database: myapp
  table_prefix: app
```

## Error Handling

The module includes comprehensive error handling:

- **Connection Errors**: Logged to stderr, returns False from init_database()
- **Table Creation Errors**: Individual table failures don't stop other tables
- **Session Errors**: Automatic rollback in context managers
- **Pool Exhaustion**: Configurable timeout with clear error messages

## Thread Safety

All connection pool operations are thread-safe:
- Multiple threads can safely request connections
- Session factories are thread-safe
- Connection checkout/checkin is handled automatically

## Best Practices

1. **Use Context Managers**: Always use `get_db_session()` or `get_db_connection()` with context managers
2. **Initialize Once**: Call `init_database()` once at application startup
3. **Close on Shutdown**: Call `close_database()` during application shutdown
4. **Use Sessions for ORM**: Prefer `get_db_session()` for SQLAlchemy ORM operations
5. **Use Connections for Raw SQL**: Use `get_db_connection()` for raw SQL queries
6. **Monitor Pool Status**: Check `get_connection_pool_status()` for performance monitoring

## Troubleshooting

### "Pool limit reached"
- Increase `pool_size` or `max_overflow` in `get_engine()`
- Check for leaked connections (not properly closed)
- Monitor with `get_connection_pool_status()`

### "Table already exists" errors
- This is normal and expected
- The handler checks for existing tables before creation
- No action needed

### Connection timeouts
- Increase `pool_timeout` in `get_engine()`
- Check database server load
- Verify network connectivity

## API Reference

### Functions

#### `init_database() -> bool`
Initialize all database tables. Returns True on success.

#### `close_database() -> None`
Close all connections and dispose of the engine.

#### `get_db_session() -> Generator[Session, None, None]`
Context manager that yields a database session.

#### `get_db_connection() -> Generator[Connection, None, None]`
Context manager that yields a raw database connection.

#### `get_db() -> Generator[Session, None, None]`
FastAPI dependency function for database sessions.

#### `get_engine() -> Engine`
Get the SQLAlchemy engine singleton.

#### `get_session_factory() -> sessionmaker`
Get the SQLAlchemy session factory.

#### `get_connection_pool_status() -> dict`
Get current connection pool status information.

## Migration from Existing Code

To migrate existing modules to use the database module:

```python
# Old way
from apikey.database import get_session
session = get_session()
# ... use session
session.close()

# New way
from database import get_db_session
with get_db_session() as session:
    # ... use session
    # automatic commit/rollback and close
```

## License

This module is part of the My OpenAI Frontend API application.
