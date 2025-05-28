"""
Database Connection Module for OAuth2

This module provides database connection and session management for PostgreSQL
using SQLAlchemy ORM. It handles the creation of tables, models, and session management.
"""

from sqlalchemy import Column, Integer, String, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import ARRAY
from contextlib import contextmanager
from typing import Generator
from config import get_config
from logger import get_logger

# Get logger from our enhanced logging system
logger = get_logger(__name__)

# Get database configuration
config = get_config()
db_config = config.get("database", {})
logging_config = config.get("logging", {})

# Get table prefix for database tables
TABLE_PREFIX = logging_config.get("table_prefix", "myopenaiapi")

# Build SQLAlchemy connection string
DB_ENGINE = db_config.get("engine", "postgresql")
DB_HOST = db_config.get("host", "localhost")
DB_PORT = db_config.get("port", 5432)
DB_USER = db_config.get("username", "postgres")
DB_PASS = db_config.get("password", "")
DB_NAME = db_config.get("name", "oauth2_db")
SSL_MODE = db_config.get("ssl_mode", "prefer")

SQLALCHEMY_DATABASE_URL = f"{DB_ENGINE}://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode={SSL_MODE}"

# Create SQLAlchemy engine
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for SQLAlchemy models
Base = declarative_base()

# Define the User model
class DBUser(Base):
    """
    SQLAlchemy User model for the users table
    """
    __tablename__ = f"{TABLE_PREFIX}_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    disabled = Column(Boolean, default=False)
    hashed_password = Column(String, nullable=False)
    scopes = Column(ARRAY(String), default=list)
    last_token_refresh = Column(String, nullable=True)  # ISO format datetime of last token refresh


def get_db() -> Generator:
    """
    Get a database session for dependency injection in FastAPI
    
    Yields:
        SQLAlchemy session for database operations
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {str(e)}")
        raise
    finally:
        db.close()


def initialize_db():
    """
    Initialize database tables and add default admin user if it doesn't exist
    """
    try:
        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Add default admin user if not exists
        db = next(get_db())
        try:
            from passlib.hash import bcrypt
            # Get default admin config
            admin_config = config.get("oauth2", {}).get("default_admin", {})
            admin_username = admin_config.get("username", "admin")
            
            # Get available scopes from config or use default if not defined
            default_scopes = config.get("oauth2", {}).get("scopes", 
                ["models:read", "models:write", "chat:read", "chat:write", "embeddings:read"])
            
            # Get admin password from config or use default
            admin_password = admin_config.get("password", "secret")
            
            # Hash the password
            hashed_password = bcrypt.hash(admin_password)
            
            # Check if admin user exists
            admin_user = db.query(DBUser).filter(DBUser.username == admin_username).first()
            
            if admin_user is None:
                # Create new admin user
                default_admin = DBUser(
                    username=admin_config.get("username", "admin"),
                    email=admin_config.get("email", "admin@example.com"),
                    full_name=admin_config.get("full_name", "Admin User"),
                    disabled=admin_config.get("disabled", False),
                    hashed_password=hashed_password,
                    scopes=default_scopes
                )
                db.add(default_admin)
                db.commit()
                logger.info("Default admin user created")
            else:
                # Update existing admin user with values from config
                admin_user.email = admin_config.get("email", "admin@example.com")
                admin_user.full_name = admin_config.get("full_name", "Admin User")
                admin_user.disabled = admin_config.get("disabled", False)
                admin_user.hashed_password = hashed_password
                admin_user.scopes = default_scopes
                db.commit()
                logger.info("Default admin user updated from configuration")
        finally:
            db.close()
                
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise
