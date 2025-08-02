"""
Database setup and token model
"""

from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import Config

# Load configuration
config = Config()
Base = declarative_base()


class RefreshTokenDB(Base):
    """Refresh token database model"""
    __tablename__ = f"{config.get_table_prefix()}_refresh_tokens"

    id = sa.Column(sa.Integer, primary_key=True, index=True)
    token = sa.Column(sa.String, unique=True, index=True)
    user_id = sa.Column(sa.Integer, index=True)
    expires_at = sa.Column(sa.DateTime)
    revoked = sa.Column(sa.Boolean, default=False)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)


def get_database_session():
    """Create database session"""
    db_url = config.get_database_connection_string()
    engine = sa.create_engine(db_url)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal


def init_database():
    """Initialize database tables"""
    db_url = config.get_database_connection_string()
    engine = sa.create_engine(db_url)
    Base.metadata.create_all(engine)
    return engine
