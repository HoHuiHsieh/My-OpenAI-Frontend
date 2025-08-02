"""
Configuration data models
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class AuthenticationConfig:
    """OAuth2 configuration settings."""
    enable: bool
    secret_key: str
    algorithm: str
    access_token_expire_time: int
    refresh_token_expire_time: int
    default_admin: Dict[str, Any]


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    host: str
    port: int
    username: str
    password: str
    database: str
    table_prefix: str
    
    @property
    def connection_string(self) -> str:
        """Generate database connection string."""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class LoggingConfig:
    """Logging configuration settings."""
    level: str
    database: Dict[str, Any]
    console: Dict[str, Any]
    components: Dict[str, str]


@dataclass
class ModelConfig:
    """Individual model configuration."""
    host: str
    port: int
    type: List[str]
    args: Optional[Dict[str, Any]] = None
    response: Optional[Dict[str, Any]] = None
