"""
User and token data models for OAuth2.

This module defines the database models for users and tokens
for authentication and authorization.
"""

from sqlalchemy import Boolean, Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime

from logger import get_logger
from .base import Base, generate_table_name

# Initialize logger
logger = get_logger(__name__)


class User(Base):
    """User model for authentication and authorization."""
    __tablename__ = generate_table_name("users")
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    hashed_password = Column(String, nullable=False)
    disabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    scopes = Column(JSONB, nullable=False, default=list)
    
    # Relationship to tokens
    tokens = relationship("Token", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"


class Token(Base):
    """Token model for API access tokens."""
    __tablename__ = generate_table_name("tokens")
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    token_type = Column(String, nullable=False)  # session, access
    user_id = Column(Integer, ForeignKey(f"{generate_table_name('users')}.id", ondelete="CASCADE"))
    scopes = Column(JSONB, nullable=False, default=list)
    token_metadata = Column(JSONB, nullable=True)  # renamed from metadata to avoid conflict with SQLAlchemy
    expires_at = Column(DateTime, nullable=True)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to user
    user = relationship("User", back_populates="tokens")
    
    def __repr__(self):
        return f"<Token(token_type='{self.token_type}', user_id='{self.user_id}', revoked='{self.revoked}')>"
