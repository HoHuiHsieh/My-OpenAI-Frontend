"""
Configuration manager class
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from .models import AuthenticationConfig, DatabaseConfig, LoggingConfig, ModelConfig
from .loader import ConfigLoader


class Config:
    """Configuration class that loads and manages application settings from config.yml."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration by loading from YAML file.
        
        Args:
            config_path: Path to config file. Defaults to asset/config.yml
        """
        if config_path is None:
            # load config with environment variable
            config_path = os.getenv("ASSET_PATH", "asset/config.yml")
            if not config_path:
                # Fallback to default path if environment variable is not set
                project_root = Path(__file__).parent.parent.parent
                config_path = project_root / "asset" / "config.yml"
        
        self._config_path = Path(config_path)
        self._raw_config: Dict[str, Any] = {}
        self._authentication: Optional[AuthenticationConfig] = None
        self._database: Optional[DatabaseConfig] = None
        self._logging: Optional[LoggingConfig] = None
        self._models: Dict[str, ModelConfig] = {}
        
        self.load()
    
    def load(self) -> None:
        """Load configuration from YAML file."""
        self._raw_config = ConfigLoader.load_from_file(self._config_path)
        self._parse_config()
    
    def reload(self) -> None:
        """Reload configuration from file."""
        self.load()
    
    def _parse_config(self) -> None:
        """Parse the raw configuration into structured objects."""
        self._authentication = ConfigLoader.parse_authentication_config(self._raw_config)
        self._database = ConfigLoader.parse_database_config(self._raw_config)
        self._logging = ConfigLoader.parse_logging_config(self._raw_config)
        self._models = ConfigLoader.parse_models_config(self._raw_config)
    
    # Authentication methods
    @property
    def authentication(self) -> Optional[AuthenticationConfig]:
        """Get authentication configuration."""
        return self._authentication
    
    def is_authentication_enabled(self) -> bool:
        """Check if authentication is enabled."""
        return self._authentication.enable if self._authentication else False
    
    def get_secret_key(self) -> str:
        """Get the secret key for JWT tokens."""
        return self._authentication.secret_key if self._authentication else ""
    
    def get_algorithm(self) -> str:
        """Get the JWT algorithm."""
        return self._authentication.algorithm if self._authentication else "HS256"
    
    def get_access_token_expire_time(self) -> int:
        """Get access token expiration time in seconds."""
        return self._authentication.access_token_expire_time if self._authentication else 3600
    
    def get_refresh_token_expire_time(self) -> int:
        """Get refresh token expiration time in seconds."""
        return self._authentication.refresh_token_expire_time if self._authentication else 2592000
    
    def get_default_admin(self) -> Dict[str, Any]:
        """Get default admin user configuration."""
        return self._authentication.default_admin if self._authentication else {}
    
    # Database methods
    @property
    def database(self) -> Optional[DatabaseConfig]:
        """Get database configuration."""
        return self._database
    
    def get_database_connection_string(self) -> str:
        """Get database connection string."""
        return self._database.connection_string if self._database else ""
    
    def get_database_host(self) -> str:
        """Get database host."""
        return self._database.host if self._database else "localhost"
    
    def get_database_port(self) -> int:
        """Get database port."""
        return self._database.port if self._database else 5432
    
    def get_database_name(self) -> str:
        """Get database name."""
        return self._database.database if self._database else ""
    
    def get_table_prefix(self) -> str:
        """Get table prefix."""
        return self._database.table_prefix if self._database else ""
    
    # Logging methods
    @property
    def logging(self) -> Optional[LoggingConfig]:
        """Get logging configuration."""
        return self._logging
    
    def get_logging_level(self) -> str:
        """Get global logging level."""
        return self._logging.level if self._logging else "INFO"
    
    def get_component_logging_level(self, component: str) -> str:
        """Get logging level for a specific component."""
        if self._logging and component in self._logging.components:
            return self._logging.components[component]
        return self.get_logging_level()
    
    def is_database_logging_enabled(self) -> bool:
        """Check if database logging is enabled."""
        return (self._logging.database.get('enabled', False) 
                if self._logging else False)
    
    def is_console_logging_enabled(self) -> bool:
        """Check if console logging is enabled."""
        return (self._logging.console.get('enabled', True) 
                if self._logging else True)
    
    def get_log_retention_days(self) -> int:
        """Get log retention period in days."""
        return (self._logging.database.get('retention_days', 365) 
                if self._logging else 365)
    
    # Model methods
    def get_models(self) -> Dict[str, ModelConfig]:
        """Get all model configurations."""
        return self._models
    
    def get_model(self, name: str) -> Optional[ModelConfig]:
        """Get a specific model configuration by name."""
        return self._models.get(name)
    
    def list_model_names(self) -> List[str]:
        """Get list of all model names."""
        return list(self._models.keys())
    
    def get_models_by_type(self, model_type: str) -> Dict[str, ModelConfig]:
        """Get models that support a specific type (e.g., 'chat:base', 'embedding:base')."""
        filtered_models = {}
        for name, model in self._models.items():
            if any(model_type in t for t in model.type):
                filtered_models[name] = model
        return filtered_models
    
    def get_model_endpoint(self, name: str) -> Optional[str]:
        """Get the full endpoint URL for a model."""
        model = self.get_model(name)
        if model:
            return f"{model.host}:{model.port}"
        return None
    
    # Raw config access
    def get_raw_config(self) -> Dict[str, Any]:
        """Get the raw configuration dictionary."""
        return self._raw_config.copy()
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key path (e.g., 'database.host')."""
        keys = key.split('.')
        value = self._raw_config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
