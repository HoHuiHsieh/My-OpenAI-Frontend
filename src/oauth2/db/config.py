"""
Database configuration module for OAuth2.

This module provides configuration values for the database
to avoid circular imports between base.py and __init__.py.
"""

from config import get_config
from logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Load configuration
config = get_config()
db_config = config.get("database", {})

# Database connection configuration
DB_ENGINE = db_config.get("engine", "postgresql")
DB_HOST = db_config.get("host", "localhost")
DB_PORT = db_config.get("port", 5432)
DB_USER = db_config.get("username", "postgres")
DB_PASS = db_config.get("password", "password")
DB_NAME = db_config.get("name", "ai_platform_auth")
DB_SSL_MODE = db_config.get("ssl_mode", "prefer")
DB_TABLE_PREFIX = db_config.get("table_prefix", "myopenaiapi")

# Function to generate table name with prefix
def generate_table_name(name: str) -> str:
    """
    Generate a table name with the configured prefix.
    
    Args:
        name: Base table name
        
    Returns:
        str: Table name with prefix
    """
    return f"{DB_TABLE_PREFIX}_{name}" if DB_TABLE_PREFIX else name
