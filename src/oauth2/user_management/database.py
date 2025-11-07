"""
Database setup and user model with optimized connection pooling
"""

from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from config import Config

# Import shared database utilities
from ..database import (
    get_engine,
    get_database_session,
    init_database,
    get_db,
    Base
)

# Load configuration
config = Config()


class UserDB(Base):
    """User database model"""
    __tablename__ = f"{config.get_table_prefix()}_users"

    id = sa.Column(sa.Integer, primary_key=True, index=True)
    username = sa.Column(sa.String, unique=True, index=True, nullable=False)
    email = sa.Column(sa.String, unique=True, index=True, nullable=False)
    fullname = sa.Column(sa.String, nullable=False)
    hashed_password = sa.Column(sa.String, nullable=False)
    active = sa.Column(sa.Boolean, default=True)
    scopes = sa.Column(sa.ARRAY(sa.String), default=[])
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)
    updated_at = sa.Column(sa.DateTime, onupdate=datetime.utcnow)
