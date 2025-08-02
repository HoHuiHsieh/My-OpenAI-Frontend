# CONFIG Module Documentation

## Overview

The CONFIG module provides a structured configuration management system for the application. It loads settings from YAML files and provides typed access to authentication, database, logging, and model configurations through a centralized configuration manager.

## Features

- **YAML Configuration**: Load settings from `config.yml` files
- **Type-Safe Access**: Strongly typed configuration models using dataclasses
- **Global Instance**: Singleton pattern for application-wide configuration access
- **Hot Reload**: Runtime configuration reloading capability
- **Modular Design**: Separate configuration sections for different components
- **Default Values**: Fallback values for missing configuration options

## Module Structure

```
src/config/
├── __init__.py          # Module exports and initialization
├── loader.py            # YAML file loading and parsing logic
├── manager.py           # Main Config class and methods
├── models.py            # Configuration data models (dataclasses)
└── utils.py             # Global instance management utilities
```

## Configuration Sections

### Authentication (OAuth2)
- JWT token settings and secrets
- Token expiration times
- Default admin user configuration

### Database (PostgreSQL)
- Connection parameters
- Table prefixes
- Connection string generation

### Logging
- Global and component-specific log levels
- Database and console logging settings
- Log retention policies

### Models
- AI model endpoint configurations
- Model types and capabilities
- Custom arguments and responses

## Data Models

### AuthenticationConfig
```python
@dataclass
class AuthenticationConfig:
    enable: bool                        # Enable/disable authentication
    secret_key: str                     # JWT secret key
    algorithm: str                      # JWT algorithm (e.g., HS256)
    access_token_expire_time: int       # Access token expiration (seconds)
    refresh_token_expire_time: int      # Refresh token expiration (seconds)
    default_admin: Dict[str, Any]       # Default admin user settings
```

### DatabaseConfig
```python
@dataclass
class DatabaseConfig:
    host: str                           # Database host
    port: int                           # Database port
    username: str                       # Database username
    password: str                       # Database password
    database: str                       # Database name
    table_prefix: str                   # Table prefix
    
    @property
    def connection_string(self) -> str  # PostgreSQL connection string
```

### LoggingConfig
```python
@dataclass
class LoggingConfig:
    level: str                          # Global logging level
    database: Dict[str, Any]            # Database logging settings
    console: Dict[str, Any]             # Console logging settings
    components: Dict[str, str]          # Component-specific log levels
```

### ModelConfig
```python
@dataclass
class ModelConfig:
    host: str                           # Model server host
    port: int                           # Model server port
    type: List[str]                     # Supported model types
    args: Optional[Dict[str, Any]]      # Model-specific arguments
    response: Optional[Dict[str, Any]]  # Model response metadata
```

## Usage Examples

### Getting Global Configuration
```python
from config import get_config

# Get the global configuration instance
config = get_config()

# Access authentication settings
if config.is_authentication_enabled():
    secret_key = config.get_secret_key()
    algorithm = config.get_algorithm()
```

### Database Configuration
```python
from config import get_config

config = get_config()

# Get database connection details
db_host = config.get_database_host()
db_port = config.get_database_port()
connection_string = config.get_database_connection_string()

# Example: postgresql://postgresql:password@postgres:5432/ai_platform_auth
print(f"Database: {connection_string}")
```

### Model Configuration
```python
from config import get_config

config = get_config()

# Get all available models
models = config.get_models()

# Get specific model
llama_model = config.get_model("llama-3.3-70b-instruct")
if llama_model:
    endpoint = config.get_model_endpoint("llama-3.3-70b-instruct")
    print(f"LLaMA endpoint: {endpoint}")

# Get models by type
chat_models = config.get_models_by_type("chat:base")
embedding_models = config.get_models_by_type("embeddings:base")
```

### Logging Configuration
```python
from config import get_config

config = get_config()

# Get logging settings
global_level = config.get_logging_level()
auth_level = config.get_component_logging_level("authentication")

# Check logging capabilities
db_logging_enabled = config.is_database_logging_enabled()
console_logging_enabled = config.is_console_logging_enabled()
```

### Configuration Reloading
```python
from config import reload_config, reset_config

# Reload configuration from file
reload_config()

# Reset configuration instance (useful for testing)
reset_config()
```

### Direct Configuration Access
```python
from config import get_config

config = get_config()

# Access raw configuration
raw_config = config.get_raw_config()

# Get specific values by key path
db_host = config.get_config_value("database.host", "localhost")
oauth_enabled = config.get_config_value("oauth2.enable", True)
```

## Configuration File Format

The module expects a YAML configuration file at `asset/config.yml`:

```yaml
# Authentication Configuration
oauth2:
  enable: true
  secret_key: "my-secret-key"
  algorithm: "HS256"
  access_token_expire_time: 3600
  refresh_token_expire_time: 2592000
  default_admin:
    username: "admin"
    email: "admin@example.com"
    password: "secret"

# Database Configuration
database:
  host: "postgres"
  port: 5432
  username: "postgresql"
  password: "password"
  database: "ai_platform_auth"
  table_prefix: "myopenaiapi"

# Logging Configuration
logging:
  level: "DEBUG"
  database:
    enabled: true
    retention_days: 365
  console:
    enabled: true
  components:
    authentication: "DEBUG"
    database: "INFO"

# Model Configuration
models:
  llama-3.3-70b-instruct:
    host: "hostaddress"
    port: 8001
    type: ["chat:base"]
  nv-embed-v2:
    host: "hostaddress"
    port: 9001
    type: ["embeddings:base"]
```

## API Reference

### Main Config Class Methods

#### Authentication Methods
- `is_authentication_enabled() -> bool`
- `get_secret_key() -> str`
- `get_algorithm() -> str`
- `get_access_token_expire_time() -> int`
- `get_refresh_token_expire_time() -> int`
- `get_default_admin() -> Dict[str, Any]`

#### Database Methods
- `get_database_connection_string() -> str`
- `get_database_host() -> str`
- `get_database_port() -> int`
- `get_database_name() -> str`
- `get_table_prefix() -> str`

#### Logging Methods
- `get_logging_level() -> str`
- `get_component_logging_level(component: str) -> str`
- `is_database_logging_enabled() -> bool`
- `is_console_logging_enabled() -> bool`
- `get_log_retention_days() -> int`

#### Model Methods
- `get_models() -> Dict[str, ModelConfig]`
- `get_model(name: str) -> Optional[ModelConfig]`
- `list_model_names() -> List[str]`
- `get_models_by_type(model_type: str) -> Dict[str, ModelConfig]`
- `get_model_endpoint(name: str) -> Optional[str]`

#### Utility Methods
- `load() -> None` - Load configuration from file
- `reload() -> None` - Reload configuration
- `get_raw_config() -> Dict[str, Any]` - Get raw configuration
- `get_config_value(key: str, default: Any) -> Any` - Get value by key path

### Global Functions
- `get_config(config_path: Optional[str]) -> Config` - Get global instance
- `reload_config() -> None` - Reload global configuration
- `reset_config() -> None` - Reset global instance

## Integration

The CONFIG module is used by:
- **APIKEY Module**: For JWT secrets and algorithms
- **OAuth2 Module**: For authentication settings
- **Database Modules**: For connection parameters
- **Logger Module**: For logging configuration
- **Model Endpoints**: For AI model configurations

## Error Handling

- **FileNotFoundError**: Raised when configuration file is missing
- **yaml.YAMLError**: Raised for invalid YAML syntax
- **KeyError**: Handled gracefully with default values
- **TypeError**: Prevented through type validation in dataclasses