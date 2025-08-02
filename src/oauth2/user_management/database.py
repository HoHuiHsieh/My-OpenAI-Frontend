"""
Database setup and user model
"""

from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import Config

# Load configuration
config = Config()
Base = declarative_base()


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
