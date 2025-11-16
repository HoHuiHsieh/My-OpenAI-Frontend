"""
Database setup and API key model

This module now uses the centralized database module for connection management.
"""

from datetime import datetime
from typing import Optional
from database import get_db_session
from database.schema import ApiKeyDB


def init_database():
    """
    Initialize database tables.
    
    Note: This is now handled by the centralized database module.
    This function is kept for backward compatibility.
    """
    from database import init_database as init_db
    return init_db()


def get_api_key_from_db(api_key: str) -> Optional[ApiKeyDB]:
    """Get API key from database"""
    with get_db_session() as session:
        result = session.query(ApiKeyDB).filter(
            ApiKeyDB.api_key == api_key,
            ApiKeyDB.revoked == False
        ).first()
        
        if result:
            # Detach the instance so it can be used outside the session
            session.expunge(result)
        return result


def save_api_key_to_db(api_key: str, user_id: int, expires_at: datetime) -> ApiKeyDB:
    """Save API key to database"""
    with get_db_session() as session:
        db_api_key = ApiKeyDB(
            api_key=api_key,
            user_id=user_id,
            expires_at=expires_at,
            created_at=datetime.utcnow()
        )
        session.add(db_api_key)
        session.flush()  # Flush to get the ID
        session.refresh(db_api_key)
        
        # Make the instance detached so it can be used outside the session
        session.expunge(db_api_key)
        return db_api_key


def revoke_api_key_in_db(api_key: str) -> bool:
    """Revoke API key in database"""
    with get_db_session() as session:
        db_api_key = session.query(ApiKeyDB).filter(ApiKeyDB.api_key == api_key).first()
        if db_api_key:
            db_api_key.revoked = True
            return True
        return False

def revoke_api_key_by_user(user_id: int) -> bool:
    """Revoke all API keys for a user"""
    try:
        with get_db_session() as session:
            session.query(ApiKeyDB).filter(ApiKeyDB.user_id == user_id).update(
                {ApiKeyDB.revoked: True},
                synchronize_session=False
            )
            return True
    except Exception as e:
        return False


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
    with get_db_session() as session:
        result = session.query(ApiKeyDB).filter(
            ApiKeyDB.user_id == user_id,
            ApiKeyDB.revoked == False
        ).first()
        
        if result:
            # Detach the instance so it can be used outside the session
            session.expunge(result)
        return result