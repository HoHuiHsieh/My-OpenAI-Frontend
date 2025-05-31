"""
Database operations for OAuth2 module.

This module provides database operations for user and token management.
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from logger import get_logger
from config import get_config
from ..auth import get_password_hash
from .models import User, Token

# Initialize logger
logger = get_logger(__name__)

# Load configuration
config = get_config()
oauth2_config = config.get("oauth2", {})


# User operations
def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """
    Get user by username.
    
    Args:
        db: Database session
        username: Username to look up
        
    Returns:
        Optional[User]: User if found, None otherwise
    """
    try:
        user = db.query(User).filter(User.username == username).first()
        if user:
            logger.debug(f"Retrieved user: {username}")
        else:
            logger.debug(f"User not found: {username}")
        return user
    except SQLAlchemyError as e:
        logger.error(f"Error retrieving user by username {username}: {str(e)}")
        return None


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Get user by email.
    
    Args:
        db: Database session
        email: Email to look up
        
    Returns:
        Optional[User]: User if found, None otherwise
    """
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            logger.debug(f"Retrieved user by email: {email}")
        else:
            logger.debug(f"User not found for email: {email}")
        return user
    except SQLAlchemyError as e:
        logger.error(f"Error retrieving user by email {email}: {str(e)}")
        return None


def create_user(
    db: Session,
    username: str,
    password: str,
    email: Optional[str] = None,
    full_name: Optional[str] = None,
    role: str = "user",
    disabled: bool = False
) -> Optional[User]:
    """
    Create a new user.
    
    Args:
        db: Database session
        username: Username for the new user
        password: Plain password for the new user
        email: Email for the new user
        full_name: Full name of the new user
        role: Role for the new user (user, admin)
        disabled: Whether the user is disabled
        
    Returns:
        Optional[User]: Created user or None if creation failed
    """
    try:
        # Check if username already exists
        existing_user = get_user_by_username(db, username)
        if existing_user:
            logger.warning(f"User creation failed: Username {username} already exists")
            return None
            
        # Check if email already exists (if provided)
        if email:
            existing_email = get_user_by_email(db, email)
            if existing_email:
                logger.warning(f"User creation failed: Email {email} already in use")
                return None
        
        # Hash the password
        hashed_password = get_password_hash(password)
        
        # Create new user
        user = User(
            username=username,
            hashed_password=hashed_password,
            email=email,
            full_name=full_name,
            role=role,
            disabled=disabled
        )
        
        # Add to database
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"Created new user: {username} with role {role}")
        return user
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creating user {username}: {str(e)}")
        return None


def update_user(
    db: Session,
    username: str,
    update_data: Dict[str, Any]
) -> Optional[User]:
    """
    Update user information.
    
    Args:
        db: Database session
        username: Username of the user to update
        update_data: Dictionary of fields to update
        
    Returns:
        Optional[User]: Updated user or None if update failed
    """
    try:
        # Get user
        user = get_user_by_username(db, username)
        if not user:
            logger.warning(f"User update failed: User {username} not found")
            return None
              # Handle password update
        if "password" in update_data and update_data["password"] is not None:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        elif "password" in update_data:
            # Remove the None password without updating hashed_password
            update_data.pop("password")
            # Update user fields
        for key, value in update_data.items():
            if hasattr(user, key):
                setattr(user, key, value)
                
        # Save changes
        db.commit()
        db.refresh(user)
        
        logger.info(f"Updated user: {username}")
        return user
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error updating user {username}: {str(e)}")
        return None


def delete_user(db: Session, username: str) -> bool:
    """
    Delete a user.
    
    Args:
        db: Database session
        username: Username of the user to delete
        
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        # Get user
        user = get_user_by_username(db, username)
        if not user:
            logger.warning(f"User deletion failed: User {username} not found")
            return False
            
        # Delete user
        db.delete(user)
        db.commit()
        
        logger.info(f"Deleted user: {username}")
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error deleting user {username}: {str(e)}")
        return False


def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    """
    Get all users with pagination.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List[User]: List of users
    """
    try:
        users = db.query(User).offset(skip).limit(limit).all()
        logger.debug(f"Retrieved {len(users)} users")
        return users
    except SQLAlchemyError as e:
        logger.error(f"Error retrieving users: {str(e)}")
        return []


# Token operations
def get_user_tokens(
    db: Session,
    username: str,
    token_type: Optional[str] = None,
    active_only: bool = True
) -> List[Token]:
    """
    Get all tokens for a user.
    
    Args:
        db: Database session
        username: Username to get tokens for
        token_type: Filter by token type (session, access)
        active_only: Only include non-revoked and non-expired tokens
        
    Returns:
        List[Token]: List of token objects
    """
    try:
        # Get user
        user = get_user_by_username(db, username)
        if not user:
            logger.warning(f"Get tokens failed: User {username} not found")
            return []
            
        # Start query
        query = db.query(Token).filter(Token.user_id == user.id)
        
        # Filter by token type if specified
        if token_type:
            query = query.filter(Token.token_type == token_type)
            
        # Filter active tokens only if requested
        if active_only:
            now = datetime.utcnow()
            query = query.filter(
                (Token.revoked == False) &
                ((Token.expires_at.is_(None)) | (Token.expires_at > now))
            )
            
        # Execute query
        tokens = query.all()
        logger.debug(f"Retrieved {len(tokens)} tokens for user {username}")
        return tokens
    except SQLAlchemyError as e:
        logger.error(f"Error getting tokens for user {username}: {str(e)}")
        return []


def create_token_for_user(
    db: Session,
    username: str,
    token_value: str,
    token_type: str,
    scopes: List[str],
    expires_at: Optional[datetime] = None,
    metadata: Optional[Dict[str, Any]] = None,
    revoke_old_access_tokens: bool = True
) -> Optional[Token]:
    """
    Create a token record for a user.
    
    Args:
        db: Database session
        username: Username to create token for
        token_value: The token value (JWT)
        token_type: Type of token (session, access)
        scopes: List of scopes for the token
        expires_at: Expiration time for the token
        metadata: Additional metadata for the token
        revoke_old_access_tokens: Whether to revoke existing access tokens for the user
        
    Returns:
        Optional[Token]: Created token or None if creation failed
    """
    try:
        # Get user
        user = get_user_by_username(db, username)
        if not user:
            logger.warning(f"Token creation failed: User {username} not found")
            return None
        
        # If creating an access token and revoke_old_access_tokens is True, 
        # revoke all existing access tokens for this user
        if token_type == "access" and revoke_old_access_tokens:
            try:
                # Get all active access tokens for this user
                from sqlalchemy import and_
                existing_tokens = db.query(Token).filter(
                    and_(
                        Token.user_id == user.id,
                        Token.token_type == "access",
                        Token.revoked == False
                    )
                ).all()
                
                # Revoke all existing tokens
                for old_token in existing_tokens:
                    old_token.revoked = True
                    logger.debug(f"Revoking old access token (ID: {old_token.id}) for user {username}")
                
                if existing_tokens:
                    logger.info(f"Revoked {len(existing_tokens)} existing access tokens for user {username}")
                    
            except SQLAlchemyError as e:
                logger.warning(f"Error revoking old access tokens for user {username}: {str(e)}")
                # Continue creating the new token even if revocation fails
            
        # Create token        
        token = Token(
            token=token_value,
            token_type=token_type,
            user_id=user.id,
            scopes=scopes,
            expires_at=expires_at,
            token_metadata=metadata or {}
        )
        
        # Add to database
        db.add(token)
        db.commit()
        db.refresh(token)
        
        logger.info(f"Created {token_type} token for user {username}")
        return token
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creating token for user {username}: {str(e)}")
        return None


def revoke_user_token(db: Session, username: str, token_id: int) -> bool:
    """
    Revoke a user's token.
    
    Args:
        db: Database session
        username: Username of the token owner
        token_id: ID of the token to revoke
        
    Returns:
        bool: True if revocation was successful, False otherwise
    """
    try:
        # Get user
        user = get_user_by_username(db, username)
        if not user:
            logger.warning(f"Token revocation failed: User {username} not found")
            return False
            
        # Find token
        token = db.query(Token).filter(
            (Token.id == token_id) & (Token.user_id == user.id)
        ).first()
        
        if not token:
            logger.warning(f"Token revocation failed: Token {token_id} not found for user {username}")
            return False
            
        # Revoke token
        token.revoked = True
        db.commit()
        
        logger.info(f"Revoked token {token_id} for user {username}")
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error revoking token {token_id} for user {username}: {str(e)}")
        return False
        
        
def check_token_revoked(db: Session, token_value: str) -> bool:
    """
    Check if a token has been revoked in the database.
    
    Args:
        db: Database session
        token_value: The actual token string to check
        
    Returns:
        bool: True if the token is revoked, False if it's valid or not found
    """
    try:
        # Find token by value
        token = db.query(Token).filter(Token.token == token_value).first()
        
        if not token:
            logger.warning(f"Token check failed: Token not found in database")
            return False
            
        # Check if token is revoked
        if token.revoked:
            logger.info(f"Token check: Token is revoked for user_id {token.user_id}")
            return True
            
        logger.debug(f"Token check: Token is valid for user_id {token.user_id}")
        return False
    except SQLAlchemyError as e:
        logger.error(f"Error checking token revocation status: {str(e)}")
        return False
