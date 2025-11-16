"""
Database setup and user model with optimized connection pooling.

This module now uses the centralized database module for connection management.
"""

# Import from centralized database module
from database import get_engine, get_session_factory, Base
from database.schema import UserDB


def get_database_session():
    """
    Get database session factory using centralized database module.
    
    Returns:
        SQLAlchemy sessionmaker factory
    """
    return get_session_factory()


def init_database():
    """
    Initialize database tables.
    
    Note: This is now handled by the centralized database module.
    This function is kept for backward compatibility.
    """
    from database import init_database as init_db
    return init_db()


# Export all for backward compatibility
__all__ = [
    'UserDB',
    'get_database_session',
    'init_database'
]
