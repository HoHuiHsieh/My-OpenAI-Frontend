"""
Database initialization and table creation handler.

This module provides functionality to initialize database tables for all modules
(apikey, logger, oauth2, usage) if they don't already exist. It uses SQLAlchemy
to create tables based on the schema definitions.
"""

import sys
from typing import Optional
from sqlalchemy import MetaData, inspect
from sqlalchemy.exc import SQLAlchemyError
from .schema import Base, ApiKeyDB, LogDB, UserDB, RefreshTokenDB, UsageLogDB
from config import get_config


class DatabaseInitializer:
    """
    Handles database table initialization for all modules.
    
    This class checks for existing tables and creates only those that don't exist,
    ensuring no existing data is modified or lost.
    """
    
    def __init__(self, engine):
        """
        Initialize the database handler with a SQLAlchemy engine.
        
        Args:
            engine: SQLAlchemy engine instance
        """
        self.engine = engine
        self.config = get_config()
        self.table_prefix = self.config.get_table_prefix()
        
    def get_existing_tables(self) -> set:
        """
        Get a set of all existing table names in the database.
        
        Returns:
            Set of existing table names
        """
        try:
            inspector = inspect(self.engine)
            return set(inspector.get_table_names())
        except SQLAlchemyError as e:
            print(f"Error checking existing tables: {e}", file=sys.stderr)
            return set()
    
    def table_exists(self, table_name: str) -> bool:
        """
        Check if a specific table exists in the database.
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            True if table exists, False otherwise
        """
        existing_tables = self.get_existing_tables()
        return table_name in existing_tables
    
    def initialize_apikey_tables(self) -> bool:
        """
        Initialize API key module tables.
        
        Returns:
            True if successful, False otherwise
        """
        table_name = f"{self.table_prefix}_api_keys"
        
        if self.table_exists(table_name):
            print(f"Table '{table_name}' already exists, skipping creation", file=sys.stdout)
            return True
            
        try:
            print(f"Creating table '{table_name}'...", file=sys.stdout)
            ApiKeyDB.__table__.create(self.engine, checkfirst=True)
            print(f"Successfully created table '{table_name}'", file=sys.stdout)
            return True
        except SQLAlchemyError as e:
            print(f"Error creating table '{table_name}': {e}", file=sys.stderr)
            return False
    
    def initialize_logger_tables(self) -> bool:
        """
        Initialize logger module tables.
        
        Returns:
            True if successful, False otherwise
        """
        table_name = f"{self.table_prefix}_logs"
        
        if self.table_exists(table_name):
            print(f"Table '{table_name}' already exists, skipping creation", file=sys.stdout)
            return True
            
        try:
            print(f"Creating table '{table_name}'...", file=sys.stdout)
            LogDB.__table__.create(self.engine, checkfirst=True)
            print(f"Successfully created table '{table_name}'", file=sys.stdout)
            return True
        except SQLAlchemyError as e:
            print(f"Error creating table '{table_name}': {e}", file=sys.stderr)
            return False
    
    def initialize_oauth2_tables(self) -> bool:
        """
        Initialize OAuth2 module tables (users and refresh tokens).
        
        Returns:
            True if successful, False otherwise
        """
        users_table = f"{self.table_prefix}_users"
        tokens_table = f"{self.table_prefix}_refresh_tokens"
        
        success = True
        
        # Create users table
        if self.table_exists(users_table):
            print(f"Table '{users_table}' already exists, skipping creation", file=sys.stdout)
        else:
            try:
                print(f"Creating table '{users_table}'...", file=sys.stdout)
                UserDB.__table__.create(self.engine, checkfirst=True)
                print(f"Successfully created table '{users_table}'", file=sys.stdout)
            except SQLAlchemyError as e:
                print(f"Error creating table '{users_table}': {e}", file=sys.stderr)
                success = False
        
        # Create refresh tokens table
        if self.table_exists(tokens_table):
            print(f"Table '{tokens_table}' already exists, skipping creation", file=sys.stdout)
        else:
            try:
                print(f"Creating table '{tokens_table}'...", file=sys.stdout)
                RefreshTokenDB.__table__.create(self.engine, checkfirst=True)
                print(f"Successfully created table '{tokens_table}'", file=sys.stdout)
            except SQLAlchemyError as e:
                print(f"Error creating table '{tokens_table}': {e}", file=sys.stderr)
                success = False
        
        return success
    
    def initialize_usage_tables(self) -> bool:
        """
        Initialize usage module tables.
        
        Returns:
            True if successful, False otherwise
        """
        table_name = f"{self.table_prefix}_usage"
        
        if self.table_exists(table_name):
            print(f"Table '{table_name}' already exists, skipping creation", file=sys.stdout)
            return True
            
        try:
            print(f"Creating table '{table_name}'...", file=sys.stdout)
            UsageLogDB.__table__.create(self.engine, checkfirst=True)
            print(f"Successfully created table '{table_name}'", file=sys.stdout)
            return True
        except SQLAlchemyError as e:
            print(f"Error creating table '{table_name}': {e}", file=sys.stderr)
            return False
    
    def initialize_all_tables(self) -> bool:
        """
        Initialize all module tables.
        
        This method checks for existing tables and creates only those that don't exist.
        It does not modify existing table data.
        
        Returns:
            True if all tables were created or already exist, False if any creation failed
        """
        print("Initializing database tables...", file=sys.stdout)
        
        results = {
            'apikey': self.initialize_apikey_tables(),
            'logger': self.initialize_logger_tables(),
            'oauth2': self.initialize_oauth2_tables(),
            'usage': self.initialize_usage_tables(),
        }
        
        all_success = all(results.values())
        
        if all_success:
            print("All database tables initialized successfully", file=sys.stdout)
        else:
            failed = [module for module, success in results.items() if not success]
            print(f"Failed to initialize tables for modules: {', '.join(failed)}", file=sys.stderr)
        
        return all_success


def initialize_database_tables(engine) -> bool:
    """
    Convenience function to initialize all database tables.
    
    Args:
        engine: SQLAlchemy engine instance
        
    Returns:
        True if all tables were initialized successfully, False otherwise
    """
    initializer = DatabaseInitializer(engine)
    return initializer.initialize_all_tables()
