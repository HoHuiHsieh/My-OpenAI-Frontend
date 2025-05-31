"""
Database migrations for OAuth2 module.

This module provides functions to initialize and migrate the database.
It uses SQLAlchemy's metadata to create tables if they don't exist.
It also creates a default admin user if one doesn't exist.
"""

from logger import get_logger
from config import get_config
from .db import Base, engine, get_db
from .db.operations import get_user_by_username, create_user

# Initialize logger
logger = get_logger(__name__)

# Load configuration
config = get_config()
oauth2_config = config.get("oauth2", {})
default_admin_config = oauth2_config.get("default_admin", {})


def initialize_database():
    """
    Initialize the database by creating tables if they don't exist.
    
    This is a compatibility function that uses SQLAlchemy's metadata
    to create all tables defined in the models.
    It also creates a default admin user if one doesn't exist.
    """
    try:
        if engine:
            logger.info("Creating database tables if they don't exist...")
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables initialized successfully")
            
            # Create default admin user if configured
            create_default_admin()
        else:
            logger.warning("Database engine not initialized, skipping table creation")
            
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise


def create_default_admin():
    """
    Create a default admin user if one doesn't exist.
    
    Uses the configuration from oauth2.default_admin in config.yml.
    """
    # Skip if default admin is not configured
    if not default_admin_config:
        logger.info("Default admin configuration not found, skipping creation.")
        return
    
    # Get required configuration values
    username = default_admin_config.get("username")
    password = default_admin_config.get("password")
    
    # Skip if required fields are missing
    if not username or not password:
        logger.warning("Default admin username or password not configured, skipping creation.")
        return
    
    # Get optional configuration values with defaults
    email = default_admin_config.get("email")
    full_name = default_admin_config.get("full_name")
    disabled = default_admin_config.get("disabled", False)
    
    try:
        # Get a database session
        db_generator = get_db()
        db = next(db_generator)
        
        # Check if admin user already exists
        existing_admin = get_user_by_username(db, username)
        
        if not existing_admin:
            logger.info(f"Creating default admin user: {username}")
            
            # Create admin user
            admin_user = create_user(
                db=db,
                username=username,
                password=password,
                email=email,
                full_name=full_name,
                role="admin",
                disabled=disabled
            )
            
            if admin_user:
                logger.info(f"Default admin user '{username}' created successfully.")
            else:
                logger.error(f"Failed to create default admin user '{username}'.")
        else:
            logger.info(f"Default admin user '{username}' already exists, skipping creation.")
            
    except Exception as e:
        logger.error(f"Error creating default admin user: {str(e)}")
    finally:
        # Close the database session
        try:
            db_generator.close()
        except:
            pass
