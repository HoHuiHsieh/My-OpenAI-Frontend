"""
Database Initialization Module

This module provides utilities for initializing the database schema.
It creates tables and initial data only if they don't exist.
"""
from sqlalchemy import MetaData, inspect, Table
from sqlalchemy.sql import text
from .database import engine, get_db, DBUser, Base, TABLE_PREFIX
from logger import get_logger

logger = get_logger(__name__)


def initialize_database():
    """
    Initialize database schema and create tables if they don't exist.
    """
    try:
        # Check if tables already exist before creating them
        inspector = inspect(engine)
        table_name = f"{TABLE_PREFIX}_users"
        tables_exist = inspector.has_table(table_name)
        
        if not tables_exist:
            # Create tables only if they don't exist
            Base.metadata.create_all(bind=engine)
            logger.info(f"Database tables created successfully")
        else:
            logger.info(f"Database tables already exist, skipping creation")

        # Add default admin user if not exists
        db = next(get_db())
        try:
            admin_user = db.query(DBUser).filter(
                DBUser.username == "admin").first()

            if not admin_user:
                default_admin = DBUser(
                    username="admin",
                    email="admin@example.com",
                    full_name="Admin User",
                    disabled=False,
                    # bcrypt hash for "secret" - change this in production!
                    hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
                    scopes=["models:read", "models:write", "chat:read",
                            "chat:write", "embeddings:read", "admin"]
                )
                db.add(default_admin)
                db.commit()
                logger.info("Default admin user created")
            else:
                logger.info("Admin user already exists")
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


def migrate_database():
    """
    Apply migrations to existing database schema.

    This function is maintained for backwards compatibility,
    but migrations are not needed if we're working with fresh databases
    and the initialize_database function is checking for table existence.
    """
    try:
        # Since we're initializing with tables that already have all columns,
        # and skipping if tables exist, no migrations are needed.
        logger.info("Database schema is already up to date, no migrations needed")
        
    except Exception as e:
        logger.error(f"Error during database migration: {e}")
        raise


if __name__ == "__main__":
    pass
