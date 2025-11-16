"""
Token management logic
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from config import Config

from . import models
from .database import RefreshTokenDB, get_database_session

# Load configuration
config = Config()



class TokenManager:
    """Token management functionality"""
    # Token settings
    ACCESS_TOKEN_EXPIRE_MINUTES = config.get_access_token_expire_time() // 60
    REFRESH_TOKEN_EXPIRE_DAYS = config.get_refresh_token_expire_time() // (60 * 60 * 24)
    SECRET_KEY = config.get_secret_key()
    ALGORITHM = config.get_algorithm()

    
    def __init__(self):
        """Initialize token manager with default database configuration"""
        # Note: Database tables are initialized in main.py lifespan
        # No need to call init_database() here to avoid duplicate initialization
        pass
    
    def create_access_token(self, data: dict) -> str:
        """
        Create a new JWT access token
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire, "iat": datetime.utcnow(), "jti": secrets.token_hex(8)})
        encoded_jwt = jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)
        return encoded_jwt
    
    def decode_token(self, token: str) -> Optional[models.TokenPayload]:
        """
        Decode and validate a JWT token
        """
        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            return models.TokenPayload(**payload)
        except JWTError:
            return None
    
    def create_refresh_token(self, db: Session, user_id: int, old_token: Optional[str] = None) -> str:
        """
        Create a new refresh token and store in database
        If old_token is provided, revoke it first
        """
        # Revoke the old refresh token if provided
        print(old_token)
        if old_token:
            self.revoke_refresh_token(db, old_token)
        
        token = secrets.token_urlsafe(64)
        expires_at = datetime.utcnow() + timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS)
        
        db_token = RefreshTokenDB(
            token=token,
            user_id=user_id,
            expires_at=expires_at
        )
        
        db.add(db_token)
        db.commit()
        db.refresh(db_token)
        
        return token
    
    def verify_refresh_token(self, db: Session, token: str) -> Optional[int]:
        """
        Verify a refresh token and return the associated user_id if valid
        """
        db_token = (
            db.query(RefreshTokenDB)
            .filter(RefreshTokenDB.token == token)
            .filter(RefreshTokenDB.expires_at > datetime.utcnow())
            .filter(RefreshTokenDB.revoked == False)
            .first()
        )
        
        if not db_token:
            return None
            
        return db_token.user_id
    
    def revoke_refresh_token(self, db: Session, token: str) -> bool:
        """
        Revoke a refresh token
        """
        db_token = db.query(RefreshTokenDB).filter(RefreshTokenDB.token == token).first()
        
        if not db_token:
            return False
            
        db_token.revoked = True
        db.commit()
        return True
    
    def revoke_all_user_tokens(self, db: Session, user_id: int) -> int:
        """
        Revoke all refresh tokens for a user
        Returns the number of tokens revoked
        """
        tokens = (
            db.query(RefreshTokenDB)
            .filter(RefreshTokenDB.user_id == user_id)
            .filter(RefreshTokenDB.revoked == False)
            .all()
        )
        
        count = 0
        for token in tokens:
            token.revoked = True
            count += 1
            
        db.commit()
        return count
    
    def clean_expired_tokens(self, db: Session) -> int:
        """
        Delete expired tokens from the database
        Returns the number of tokens deleted
        """
        result = db.query(RefreshTokenDB).filter(
            RefreshTokenDB.expires_at < datetime.utcnow()
        ).delete()
        
        db.commit()
        return result
