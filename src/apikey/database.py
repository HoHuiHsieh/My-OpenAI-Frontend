"""
Database setup and API key model
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine
from config import get_config

Base = declarative_base()

config = get_config()
table_prefix = config.get_table_prefix()


class ApiKeyDB(Base):
    """API key database model"""
    __tablename__ = f"{table_prefix}_api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    api_key = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# Database session management
_engine = None
_SessionLocal = None


def get_engine():
    """Get database engine"""
    global _engine
    if _engine is None:
        config = get_config()
        connection_string = config.get_database_connection_string()
        _engine = create_engine(connection_string)
    return _engine


def get_session():
    """Get database session"""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal()


def init_database():
    """Initialize database tables"""
    config = get_config()
    table_prefix = config.get_table_prefix()
    
    # Set table name with prefix
    ApiKeyDB.__tablename__ = f"{table_prefix}_api_keys"
    
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def get_api_key_from_db(api_key: str) -> Optional[ApiKeyDB]:
    """Get API key from database"""
    db = get_session()
    try:
        return db.query(ApiKeyDB).filter(
            ApiKeyDB.api_key == api_key,
            ApiKeyDB.revoked == False
        ).first()
    finally:
        db.close()


def save_api_key_to_db(api_key: str, user_id: int, expires_at: datetime) -> ApiKeyDB:
    """Save API key to database"""
    db = get_session()
    try:
        db_api_key = ApiKeyDB(
            api_key=api_key,
            user_id=user_id,
            expires_at=expires_at,
            created_at=datetime.utcnow()
        )
        db.add(db_api_key)
        db.commit()
        db.refresh(db_api_key)
        return db_api_key
    finally:
        db.close()


def revoke_api_key_in_db(api_key: str) -> bool:
    """Revoke API key in database"""
    db = get_session()
    try:
        db_api_key = db.query(ApiKeyDB).filter(ApiKeyDB.api_key == api_key).first()
        if db_api_key:
            db_api_key.revoked = True
            db.commit()
            return True
        return False
    finally:
        db.close()

def revoke_api_key_by_user(user_id: int) -> bool:
    """Revoke all API keys for a user"""
    db = get_session()
    try:
        db.query(ApiKeyDB).filter(ApiKeyDB.user_id == user_id).update(
            {ApiKeyDB.revoked: True},
            synchronize_session=False
        )
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        return False
    finally:
        db.close()


def get_api_key_data(api_key: str = None):
    """Dependency to extract API key data from database"""
    if not api_key:
        return None
    
    db_api_key = get_api_key_from_db(api_key)
    if not db_api_key:
        return None
    
    # Check if expired
    if db_api_key.expires_at < datetime.utcnow():
        return None
    
    return db_api_key


def get_api_key_by_user(user_id: int) -> Optional[ApiKeyDB]:
    """Get API key by user ID"""
    db = get_session()
    try:
        return db.query(ApiKeyDB).filter(
            ApiKeyDB.user_id == user_id,
            ApiKeyDB.revoked == False
        ).first()
    finally:
        db.close()