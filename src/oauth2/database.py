"""
Shared database configuration and connection pooling for OAuth2 module.
This module provides a singleton database engine and session factory
that is shared across user management and token management.
"""

from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from config import Config

# Load configuration
config = Config()
Base = declarative_base()

# Global engine instance (singleton pattern)
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create the database engine singleton with optimized pooling"""
    global _engine
    if _engine is None:
        db_url = config.get_database_connection_string()
        _engine = sa.create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=10,              # Maximum number of permanent connections
            max_overflow=20,           # Maximum number of temporary connections
            pool_timeout=30,           # Seconds to wait for a connection
            pool_recycle=3600,         # Recycle connections after 1 hour
            pool_pre_ping=True,        # Verify connections before using them
            echo=False                 # Set to True for SQL debugging
        )
        # Create tables if they don't exist
        Base.metadata.create_all(_engine)
    return _engine


def get_database_session():
    """Create database session factory using singleton engine"""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


def init_database():
    """Initialize database tables and return the engine"""
    engine = get_engine()
    Base.metadata.create_all(engine)
    return engine


def get_db():
    """
    Dependency function for FastAPI routes to get database session.
    Ensures proper session lifecycle management.
    """
    SessionLocal = get_database_session()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
