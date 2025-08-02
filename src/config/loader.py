"""
Configuration loader and parser
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from .models import AuthenticationConfig, DatabaseConfig, LoggingConfig, ModelConfig


class ConfigLoader:
    """Handles loading and parsing configuration from YAML files."""
    
    @staticmethod
    def load_from_file(config_path: Path) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    
    @staticmethod
    def parse_authentication_config(raw_config: Dict[str, Any]) -> Optional[AuthenticationConfig]:
        """Parse authentication configuration from raw config."""
        if 'oauth2' not in raw_config:
            return None
            
        auth_data = raw_config['oauth2']
        return AuthenticationConfig(
            enable=auth_data.get('enable', True),
            secret_key=auth_data.get('secret_key', ''),
            algorithm=auth_data.get('algorithm', 'HS256'),
            access_token_expire_time=auth_data.get('access_token_expire_time', 3600),
            refresh_token_expire_time=auth_data.get('refresh_token_expire_time', 2592000),
            default_admin=auth_data.get('default_admin', {})
        )
    
    @staticmethod
    def parse_database_config(raw_config: Dict[str, Any]) -> Optional[DatabaseConfig]:
        """Parse database configuration from raw config."""
        if 'database' not in raw_config:
            return None
            
        db_data = raw_config['database']
        return DatabaseConfig(
            host=db_data.get('host', 'localhost'),
            port=db_data.get('port', 5432),
            username=db_data.get('username', ''),
            password=db_data.get('password', ''),
            database=db_data.get('database', ''),
            table_prefix=db_data.get('table_prefix', '')
        )
    
    @staticmethod
    def parse_logging_config(raw_config: Dict[str, Any]) -> Optional[LoggingConfig]:
        """Parse logging configuration from raw config."""
        if 'logging' not in raw_config:
            return None
            
        log_data = raw_config['logging']
        return LoggingConfig(
            level=log_data.get('level', 'INFO'),
            database=log_data.get('database', {}),
            console=log_data.get('console', {}),
            components=log_data.get('components', {})
        )
    
    @staticmethod
    def parse_models_config(raw_config: Dict[str, Any]) -> Dict[str, ModelConfig]:
        """Parse models configuration from raw config."""
        models = {}
        
        if 'models' in raw_config:
            for model_name, model_data in raw_config['models'].items():
                models[model_name] = ModelConfig(
                    host=model_data.get('host', ''),
                    port=model_data.get('port', 8000),
                    type=model_data.get('type', []),
                    args=model_data.get('args'),
                    response=model_data.get('response')
                )
        
        return models
