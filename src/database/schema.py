"""
Database schema definitions for all modules.

This module consolidates all database table schemas using SQLAlchemy ORM.
It includes schemas for:
- apikey: API key management
- logger: Application logging
- oauth2: User authentication and token management
- usage: Usage tracking and analytics
"""

from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from config import get_config

# Get configuration
config = get_config()
table_prefix = config.get_table_prefix()

# Create base class for declarative models
Base = declarative_base()


# ============================================================================
# API Key Module Tables
# ============================================================================

class ApiKeyDB(Base):
    """API key database model for managing API keys."""
    __tablename__ = f"{table_prefix}_api_keys"
    
    id = sa.Column(sa.Integer, primary_key=True, index=True)
    api_key = sa.Column(sa.String, unique=True, index=True, nullable=False)
    user_id = sa.Column(sa.Integer, nullable=False)
    expires_at = sa.Column(sa.DateTime, nullable=False)
    revoked = sa.Column(sa.Boolean, default=False, nullable=False)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow, nullable=False)


# ============================================================================
# Logger Module Tables
# ============================================================================

class LogDB(Base):
    """Application log database model for storing application logs."""
    __tablename__ = f"{table_prefix}_logs"
    
    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    timestamp = sa.Column(sa.DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    level = sa.Column(sa.String(10), nullable=False)
    logger_name = sa.Column(sa.String(255), nullable=False)
    process_id = sa.Column(sa.Integer, nullable=False)
    thread_id = sa.Column(sa.BigInteger, nullable=False)
    thread_name = sa.Column(sa.String(255))
    hostname = sa.Column(sa.String(255), nullable=False)
    message = sa.Column(sa.Text, nullable=False)
    exception = sa.Column(sa.Text)
    function_name = sa.Column(sa.String(255))
    module = sa.Column(sa.String(255))
    filename = sa.Column(sa.String(500))
    lineno = sa.Column(sa.Integer)
    pathname = sa.Column(sa.Text)
    extra_data = sa.Column(sa.JSON)
    created_at = sa.Column(sa.DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        sa.Index(f'idx_{table_prefix}_logs_timestamp', 'timestamp', postgresql_using='btree', postgresql_ops={'timestamp': 'DESC'}),
        sa.Index(f'idx_{table_prefix}_logs_level', 'level'),
        sa.Index(f'idx_{table_prefix}_logs_logger', 'logger_name'),
        sa.Index(f'idx_{table_prefix}_logs_hostname', 'hostname'),
        sa.Index(f'idx_{table_prefix}_logs_composite', 'timestamp', 'level', 'logger_name', postgresql_ops={'timestamp': 'DESC'}),
    )


# ============================================================================
# OAuth2 Module Tables
# ============================================================================

class UserDB(Base):
    """User database model for OAuth2 authentication."""
    __tablename__ = f"{table_prefix}_users"

    id = sa.Column(sa.Integer, primary_key=True, index=True)
    username = sa.Column(sa.String, unique=True, index=True, nullable=False)
    email = sa.Column(sa.String, unique=True, index=True, nullable=False)
    fullname = sa.Column(sa.String, nullable=False)
    hashed_password = sa.Column(sa.String, nullable=False)
    active = sa.Column(sa.Boolean, default=True)
    scopes = sa.Column(sa.ARRAY(sa.String), default=[])
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)
    updated_at = sa.Column(sa.DateTime, onupdate=datetime.utcnow)


class RefreshTokenDB(Base):
    """Refresh token database model for OAuth2 token management."""
    __tablename__ = f"{table_prefix}_refresh_tokens"

    id = sa.Column(sa.Integer, primary_key=True, index=True)
    token = sa.Column(sa.String, unique=True, index=True)
    user_id = sa.Column(sa.Integer, index=True)
    expires_at = sa.Column(sa.DateTime)
    revoked = sa.Column(sa.Boolean, default=False)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)


# ============================================================================
# Usage Module Tables
# ============================================================================

class UsageLogDB(Base):
    """Usage log database model for tracking API usage."""
    __tablename__ = f"{table_prefix}_usage"
    
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    timestamp = sa.Column(sa.DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    api_type = sa.Column(sa.String(50), nullable=False)
    user_id = sa.Column(sa.String(255), nullable=False)
    model = sa.Column(sa.String(255), nullable=False)
    request_id = sa.Column(sa.String(255))
    prompt_tokens = sa.Column(sa.Integer, default=0, nullable=False)
    completion_tokens = sa.Column(sa.Integer)
    total_tokens = sa.Column(sa.Integer, default=0, nullable=False)
    input_count = sa.Column(sa.Integer)
    extra_data = sa.Column(sa.JSON)
    hostname = sa.Column(sa.String(255))
    process_id = sa.Column(sa.Integer)
    created_at = sa.Column(sa.DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        sa.Index(f'idx_{table_prefix}_usage_timestamp', 'timestamp', postgresql_using='btree', postgresql_ops={'timestamp': 'DESC'}),
        sa.Index(f'idx_{table_prefix}_usage_user_id', 'user_id'),
        sa.Index(f'idx_{table_prefix}_usage_api_type', 'api_type'),
        sa.Index(f'idx_{table_prefix}_usage_model', 'model'),
        sa.Index(f'idx_{table_prefix}_usage_user_timestamp', 'user_id', 'timestamp', postgresql_ops={'timestamp': 'DESC'}),
    )
