"""
Database base module for OAuth2.

This module provides the SQLAlchemy Base class for database models
to avoid circular imports.
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData
from .config import DB_TABLE_PREFIX, generate_table_name

# Create a naming convention for constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

# Create metadata with naming convention
metadata = MetaData(naming_convention=convention)

# Create the SQLAlchemy declarative base
Base = declarative_base(metadata=metadata)

# Note: generate_table_name function is now imported from config.py
