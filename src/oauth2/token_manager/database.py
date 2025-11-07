"""
Database setup and token model with optimized connection pooling
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


class RefreshTokenDB(Base):
    """Refresh token database model"""
    __tablename__ = f"{config.get_table_prefix()}_refresh_tokens"

    id = sa.Column(sa.Integer, primary_key=True, index=True)
    token = sa.Column(sa.String, unique=True, index=True)
    user_id = sa.Column(sa.Integer, index=True)
    expires_at = sa.Column(sa.DateTime)
    revoked = sa.Column(sa.Boolean, default=False)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)
