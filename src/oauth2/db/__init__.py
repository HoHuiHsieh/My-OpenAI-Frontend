"""
Database package initialization for OAuth2.

This module initializes the database connection and provides
access to models and operations.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Generator

from logger import get_logger
from config import get_config
from .base import Base

# Initialize logger
logger = get_logger(__name__)

# Import database configuration from config.py
from .config import (
    DB_ENGINE, DB_HOST, DB_PORT, DB_USER, DB_PASS,
    DB_NAME, DB_SSL_MODE, DB_TABLE_PREFIX
)

# Create SQLAlchemy engine and session factory
DATABASE_URL = f"{DB_ENGINE}://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode={DB_SSL_MODE}"

try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    logger.info(f"Database connection established to {DB_ENGINE}://{DB_USER}:***@{DB_HOST}:{DB_PORT}/{DB_NAME}")
except Exception as e:
    logger.error(f"Error connecting to database: {str(e)}")
    # Create a dummy engine for development/testing
    engine = None
    SessionLocal = sessionmaker()
    

# Database session dependency
def get_db() -> Generator:
    """
    Create a database session for dependency injection.
    
    Yields:
        Session: A SQLAlchemy database session
    """
    if engine is None:
        logger.error("Database engine not available")
        raise Exception("Database connection failed")
        
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
