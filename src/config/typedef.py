# -*- coding: utf-8 -*- 
"""
This module defines Pydantic data models for validating and managing configuration settings
for the application, including model endpoints, database connections, OAuth2 authentication,
and logging options. These models ensure type safety and provide convenient accessors for
various configuration sections.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


# Define Pydantic models for configuration validation
class ModelConfig(BaseModel):
    """Configuration for an individual model."""
    host: str
    port: int
    type: List[str] = []
    args: Dict[str, Any] = Field(default_factory=dict)
    response: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('port')
    def validate_port(cls, v):
        if not (1 <= v <= 65535):
            raise ValueError(f"Port must be between 1 and 65535, got {v}")
        return v

class ModelsConfig(BaseModel):
    """Configuration for all models."""
    model_dict: Dict[str, ModelConfig] = Field(default_factory=dict)

    # For backwards compatibility
    @property
    def host(self) -> List[str]:
        return [model.host for model in self.model_dict.values()]
    
    @property
    def port(self) -> List[int]:
        return [model.port for model in self.model_dict.values()]
    
    def get_model(self, name: str) -> Optional[ModelConfig]:
        """Get a specific model by name."""
        return self.model_dict.get(name)
    
    def list_models(self) -> List[str]:
        """List all available model names."""
        return list(self.model_dict.keys())

class DatabaseConfig(BaseModel):
    """Database connection configuration."""
    engine: str
    host: str
    port: int
    username: str
    password: str
    name: str
    ssl_mode: str = "prefer"
    
    @property
    def connection_string(self) -> str:
        """Generate database connection string."""
        return f"{self.engine}://{self.username}:{self.password}@{self.host}:{self.port}/{self.name}"

class OAuth2Config(BaseModel):
    """OAuth2 authentication configuration."""
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    user_token_expire_days: int = 180
    admin_token_never_expires: bool = True
    enable_authentication: bool = True
    exclude_paths: List[str] = Field(default_factory=list)

class LoggingComponentConfig(BaseModel):
    """Logging level configuration for individual components."""
    auth: str = "INFO"
    database: str = "INFO"
    middleware: str = "INFO"
    controller: str = "WARNING"

class ConsoleLoggingConfig(BaseModel):
    """Console logging configuration."""
    enabled: bool = True
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    use_database: bool = False
    async_logging: bool = True
    table_prefix: str = "oauth2"
    log_retention_days: int = 30
    console: ConsoleLoggingConfig = Field(default_factory=ConsoleLoggingConfig)
    components: LoggingComponentConfig = Field(default_factory=LoggingComponentConfig)

class AppConfig(BaseModel):
    """Main application configuration."""
    models: ModelsConfig
    database: Optional[DatabaseConfig] = None
    oauth2: Optional[OAuth2Config] = None
    logging: LoggingConfig = Field(default_factory=LoggingConfig)