"""
Database module for connection pooling and table initialization.

This module provides:
- Centralized database connection management with connection pooling
- Table initialization for all modules (apikey, logger, oauth2, usage)
- SQLAlchemy engine and session management
- Database connection retrieval from connection pool

Usage:
    from database import get_db_connection, get_db_session, init_database, close_database
    
    # Initialize database and create tables
    init_database()
    
    # Get a database session (recommended for ORM operations)
    with get_db_session() as session:
        # Use session for queries
        pass
    
    # Get a raw connection from the pool (for raw SQL operations)
    with get_db_connection() as conn:
        # Use connection
        pass
    
    # Close all connections on shutdown
    close_database()
"""

from contextlib import contextmanager
from typing import Generator, Optional
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError
from config import get_config

from .schema import Base
from .handler import initialize_database_tables

# Global engine and session factory
_engine = None
_SessionLocal = None


def get_engine():
    """
    Get or create the SQLAlchemy engine singleton with optimized connection pooling.
    
    The engine uses QueuePool for connection pooling with the following settings:
    - pool_size: Maximum number of permanent connections (10)
    - max_overflow: Maximum number of temporary connections (20)
    - pool_timeout: Seconds to wait for a connection (30)
    - pool_recycle: Recycle connections after 1 hour (3600 seconds)
    - pool_pre_ping: Verify connections before using them
    
    Returns:
        SQLAlchemy Engine instance
    """
    global _engine
    
    if _engine is None:
        config = get_config()
        db_url = config.get_database_connection_string()
        
        _engine = create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=10,              # Maximum number of permanent connections
            max_overflow=20,           # Maximum number of temporary connections
            pool_timeout=30,           # Seconds to wait for a connection
            pool_recycle=3600,         # Recycle connections after 1 hour
            pool_pre_ping=True,        # Verify connections before using them
            echo=False                 # Set to True for SQL debugging
        )
        
        # Add event listener to handle connection checkout
        @event.listens_for(_engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """Event listener for new database connections."""
            # Set timezone for PostgreSQL connections
            cursor = dbapi_conn.cursor()
            cursor.execute("SET timezone='UTC'")
            cursor.close()
    
    return _engine


def get_session_factory():
    """
    Get or create the SQLAlchemy session factory.
    
    Returns:
        SQLAlchemy sessionmaker factory
    """
    global _SessionLocal
    
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine
        )
    
    return _SessionLocal


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Get a database session from the connection pool as a context manager.
    
    This is the recommended way to get database sessions for ORM operations.
    The session is automatically committed on success and rolled back on error.
    The session is always closed after use.
    
    Yields:
        SQLAlchemy Session instance
        
    Example:
        with get_db_session() as session:
            user = session.query(UserDB).filter_by(username='admin').first()
    """
    SessionLocal = get_session_factory()
    session = SessionLocal()
    
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_db_connection():
    """
    Get a raw database connection from the pool as a context manager.
    
    This provides access to the underlying database connection for raw SQL operations.
    The connection is automatically returned to the pool after use.
    
    Yields:
        Raw database connection from the pool
        
    Example:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users")
            results = cursor.fetchall()
    """
    engine = get_engine()
    conn = engine.raw_connection()
    
    try:
        yield conn
    finally:
        conn.close()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function for FastAPI routes to get database session.
    
    This is designed to be used with FastAPI's Depends() mechanism.
    Ensures proper session lifecycle management.
    
    Yields:
        SQLAlchemy Session instance
        
    Example:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(UserDB).all()
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    
    try:
        yield db
    finally:
        db.close()


def init_database() -> bool:
    """
    Initialize the database by creating all required tables.
    
    This function:
    1. Creates the database engine and connection pool
    2. Checks for existing tables
    3. Creates only tables that don't exist (preserves existing data)
    4. Creates indexes for optimal query performance
    
    Returns:
        True if initialization successful, False otherwise
        
    Note:
        This function does NOT modify existing tables or data.
        It only creates tables that don't already exist.
    """
    try:
        engine = get_engine()
        success = initialize_database_tables(engine)
        return success
    except SQLAlchemyError as e:
        print(f"Database initialization failed: {e}")
        return False


def close_database():
    """
    Close all database connections and dispose of the engine.
    
    This should be called during application shutdown to properly
    clean up database resources.
    """
    global _engine, _SessionLocal
    
    if _engine is not None:
        _engine.dispose()
        _engine = None
    
    _SessionLocal = None
    print("Database connections closed")


def get_connection_pool_status() -> dict:
    """
    Get the current status of the connection pool.
    
    Returns:
        Dictionary containing pool status information including:
        - size: Current number of connections in the pool
        - checked_out: Number of connections currently checked out
        - overflow: Number of overflow connections
        - checkedin: Number of idle connections in the pool
    """
    engine = get_engine()
    pool = engine.pool
    
    return {
        'size': pool.size(),
        'checked_out': pool.checkedout(),
        'overflow': pool.overflow(),
        'checkedin': pool.checkedin(),
        'timeout': pool.timeout(),
        'recycle': pool._recycle if hasattr(pool, '_recycle') else None,
    }


# Export all public APIs
__all__ = [
    'get_engine',
    'get_session_factory',
    'get_db_session',
    'get_db_connection',
    'get_db',
    'init_database',
    'close_database',
    'get_connection_pool_status',
    'Base',
]
