"""
User management logic
"""

import os
import bcrypt
from typing import List, Optional
from sqlalchemy.orm import Session
from . import models
from . import scopes
from .database import UserDB, get_database_session
from config import get_config


class UserManager:
    """User management functionality"""
    
    def __init__(self):
        """Initialize user manager with default database configuration"""
        # Note: Database tables are initialized in main.py lifespan
        # No need to call init_database() here to avoid duplicate initialization
        
        # Create admin user if not exists
        self._create_default_admin_if_not_exists()
    
    def _create_default_admin_if_not_exists(self):
        """Create default admin user if not exists"""
        SessionLocal = get_database_session()
        db = SessionLocal()
        try:
            admin_user = db.query(UserDB).filter(UserDB.username == "admin").first()
            if not admin_user:
                # Get admin credentials from config
                config = get_config()
                default_admin = config.get_default_admin()
                
                admin_username = default_admin.get("username", "")
                admin_password = default_admin.get("password", "")
                admin_email = default_admin.get("email", "")
                admin_fullname = default_admin.get("full_name", "")
                if not admin_username or not admin_password or not admin_email or not admin_fullname:
                    raise ValueError("Default admin credentials are not properly configured.")
                
                # Create admin user with all scopes
                admin = UserDB(
                    username=admin_username,
                    email=admin_email,
                    fullname=admin_fullname,
                    hashed_password=self.get_password_hash(admin_password),
                    active=True,
                    scopes=list(scopes.SCOPES.keys())
                )
                db.add(admin)
                db.commit()
        finally:
            db.close()
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password using bcrypt"""
        # bcrypt requires bytes input
        password_bytes = password.encode('utf-8')
        # Generate salt and hash
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        # Return as string for database storage
        return hashed.decode('utf-8')
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash using bcrypt"""
        # Convert both to bytes
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        # Verify
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    
    def get_user(self, db: Session, username: str) -> Optional[models.User]:
        """Get user by username"""
        user = db.query(UserDB).filter(UserDB.username == username).first()
        if not user:
            return None
        return self._map_to_user_model(user)
    
    def get_user_by_id(self, db: Session, user_id: int) -> Optional[models.User]:
        """Get user by ID"""
        user = db.query(UserDB).filter(UserDB.id == user_id).first()
        if not user:
            return None
        return self._map_to_user_model(user)
    
    def get_users(self, db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
        """Get all users with pagination"""
        users = db.query(UserDB).offset(skip).limit(limit).all()
        return [self._map_to_user_model(user) for user in users]
    
    def create_user(self, db: Session, user: models.UserCreate) -> models.User:
        """Create a new user"""
        db_user = UserDB(
            username=user.username,
            email=user.email,
            fullname=user.fullname,
            hashed_password=self.get_password_hash(user.password),
            active=user.active,
            scopes=user.scopes
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return self._map_to_user_model(db_user)
    
    def update_user(self, db: Session, username: str, user_update: models.UserUpdate) -> Optional[models.User]:
        """Update a user"""
        db_user = db.query(UserDB).filter(UserDB.username == username).first()
        if not db_user:
            return None
            
        # Update fields if they are provided
        update_data = user_update.dict(exclude_unset=True)
        if "password" in update_data:
            update_data["hashed_password"] = self.get_password_hash(update_data.pop("password"))
            
        for key, value in update_data.items():
            setattr(db_user, key, value)
            
        db.commit()
        db.refresh(db_user)
        return self._map_to_user_model(db_user)
    
    def delete_user(self, db: Session, username: str) -> bool:
        """Delete a user"""
        db_user = db.query(UserDB).filter(UserDB.username == username).first()
        if not db_user:
            return False
        db.delete(db_user)
        db.commit()
        return True
    
    def authenticate_user(self, db: Session, username: str, password: str) -> Optional[models.User]:
        """Authenticate a user by username and password"""
        user = db.query(UserDB).filter(UserDB.username == username).first()
        if not user or not self.verify_password(password, user.hashed_password):
            return None
        if not user.active:
            return None
        return self._map_to_user_model(user)
    
    def _map_to_user_model(self, db_user: UserDB) -> models.User:
        """Map DB user to Pydantic model"""
        return models.User(
            id=db_user.id,
            username=db_user.username,
            email=db_user.email,
            fullname=db_user.fullname,
            active=db_user.active,
            scopes=db_user.scopes,
            hashed_password=db_user.hashed_password,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at
        )
