# Configuration Management Documentation

## Overview

The configuration management module provides a centralized way to load, validate, and access configuration settings from YAML files and environment variables. It supports type validation through Pydantic models and offers convenience functions to access specific sections of the configuration.

## Configuration File

By default, the system looks for configuration in the file located at `/workspace/asset/config.yml`. An example configuration file looks like:

```yaml
# OAuth2 Authentication Configuration
oauth2:
  secret_key: "your-secret-key-placeholder"
  algorithm: "HS256"
  access_token_expire_minutes: 30
  user_token_expire_days: 180
  admin_token_never_expires: false
  enable_authentication: true
  exclude_paths:
    - "/token"
    - "/models"
    - "/docs"
    - "/redoc"
    - "/openapi.json"

# Database Configuration
database:
  engine: "postgresql"
  host: "localhost"
  port: 5432
  username: "postgres"
  password: "password"
  name: "ai_platform_auth"
  ssl_mode: "prefer"

# Model Configuration
models:
  llama-3.3-70b-instruct:
    host: localhost
    port: 8000
    type: ["chat", "completion"]
    response:
      id: "meta/llama-3.3-70b-instruct"
      created: 0
      object: "model"
      owned_by: "organization-owner"
  nv-embed-v2:
    host: localhost
    port: 8000
    type: ["embeddings"]
    args:
      instruction: "Given a question, retrieve passages that answer the question."
    response:
      id: "nvidia/nv-embed-v2"
      created: 0
      object: "model"
      owned_by: "organization-owner"

# Logging Configuration
logging:
  level: "INFO"
  use_database: true
  async_logging: true
  table_prefix: "oauth2"
  log_retention_days: 30
  console:
    enabled: true
    format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  components:
    auth: "INFO"
    database: "INFO"
    middleware: "INFO"
    controller: "WARNING"
```

## Using Environment Variables

The configuration system allows overriding values from the YAML file using environment variables. The format for environment variables is:

```
CONFIG_<SECTION>_<KEY>=<value>
```

For example:
- `CONFIG_DATABASE_HOST=localhost` 
- `CONFIG_OAUTH2_SECRET_KEY=mysecret`
- `CONFIG_LOGGING_LEVEL=DEBUG`

Environment variables take precedence over the values defined in the configuration file. The system automatically converts values to the appropriate types (booleans, integers, floats, etc.).

## API Reference

### Config Loading and Validation

#### `get_config(force_reload: bool = False) -> Dict[str, Any]`

Safely loads, validates, and returns the raw configuration from the YAML file.

- **Args**:
  - `force_reload`: If True, ignores the cache and reloads from file
- **Returns**: Dictionary containing the validated configuration
- **Raises**: 
  - `FileNotFoundError`: If the config file is not found
  - `yaml.YAMLError`: If the YAML file has syntax errors
  - `KeyError`: If required configuration keys are missing
  - `ValueError`: If configuration values are invalid

#### `get_app_config(force_reload: bool = False) -> AppConfig`

Get the application configuration as a validated Pydantic model.

- **Args**:
  - `force_reload`: If True, ignores the cache and reloads from file
- **Returns**: Validated `AppConfig` instance
- **Raises**: Various exceptions if configuration is invalid

#### `get_config_path() -> str`

Get the current configuration file path.

- **Returns**: Path to the current configuration file

### Convenience Functions

These functions provide direct access to specific sections of the configuration:

#### `get_models_config() -> ModelsConfig`

Get models configuration.

- **Returns**: Validated `ModelsConfig` instance

#### `get_database_config() -> Optional[DatabaseConfig]`

Get database configuration.

- **Returns**: Validated `DatabaseConfig` instance or `None` if not configured

#### `get_oauth2_config() -> Optional[OAuth2Config]`

Get OAuth2 configuration.

- **Returns**: Validated `OAuth2Config` instance or `None` if not configured

#### `get_logging_config() -> LoggingConfig`

Get logging configuration.

- **Returns**: Validated `LoggingConfig` instance

## Configuration Models

### `AppConfig`

Main application configuration.

- **Fields**:
  - `models`: `ModelsConfig` - Configuration for all models
  - `database`: `Optional[DatabaseConfig]` - Database connection configuration
  - `oauth2`: `Optional[OAuth2Config]` - OAuth2 authentication configuration
  - `logging`: `LoggingConfig` - Logging configuration

### `ModelsConfig`

Configuration for all models.

- **Fields**:
  - `model_dict`: `Dict[str, ModelConfig]` - Dictionary of model name to ModelConfig mapping

- **Properties**:
  - `host`: `List[str]` - List of all model hosts (for backwards compatibility)
  - `port`: `List[int]` - List of all model ports (for backwards compatibility)

- **Methods**:
  - `get_model(name: str) -> Optional[ModelConfig]`: Get a specific model by name
  - `list_models() -> List[str]`: List all available model names

### `ModelConfig`

Configuration for an individual model.

- **Fields**:
  - `host`: `str` - Hostname where the model service is running
  - `port`: `int` - Port number where the model service is running
  - `type`: `List[str]` - List of model capabilities (e.g., "chat", "completion", "embeddings")
  - `args`: `Dict[str, Any]` - Arguments to pass to the model
  - `response`: `Dict[str, Any]` - Custom response overrides

### `DatabaseConfig`

Database connection configuration.

- **Fields**:
  - `engine`: `str` - Database engine (e.g., "postgresql")
  - `host`: `str` - Database server hostname
  - `port`: `int` - Database server port
  - `username`: `str` - Database username
  - `password`: `str` - Database password
  - `name`: `str` - Database name
  - `ssl_mode`: `str` - SSL mode (default: "prefer")

- **Properties**:
  - `connection_string`: `str` - Generate database connection string

### `OAuth2Config`

OAuth2 authentication configuration.

- **Fields**:
  - `secret_key`: `str` - Secret key for token signing
  - `algorithm`: `str` - Token signing algorithm (default: "HS256")
  - `access_token_expire_minutes`: `int` - Short-lived token expiration in minutes (default: 30)
  - `user_token_expire_days`: `int` - User token expiration in days (default: 180)
  - `admin_token_never_expires`: `bool` - Whether admin tokens never expire (default: True)
  - `enable_authentication`: `bool` - Whether authentication is enabled (default: True)
  - `exclude_paths`: `List[str]` - Paths to exclude from authentication

### `LoggingConfig`

Logging configuration.

- **Fields**:
  - `level`: `str` - Default logging level (default: "INFO")
  - `use_database`: `bool` - Whether to log to the database (default: False)
  - `async_logging`: `bool` - Use asynchronous logging for better performance (default: True)
  - `table_prefix`: `str` - Prefix for log tables in the database (default: "oauth2")
  - `log_retention_days`: `int` - How many days to keep logs in the database (default: 30)
  - `console`: `ConsoleLoggingConfig` - Console logging configuration
  - `components`: `LoggingComponentConfig` - Component-specific logging levels

### `ConsoleLoggingConfig`

Console logging configuration.

- **Fields**:
  - `enabled`: `bool` - Whether console logging is enabled (default: True)
  - `format`: `str` - Log format string (default: "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

### `LoggingComponentConfig`

Logging level configuration for individual components.

- **Fields**:
  - `auth`: `str` - Authentication component logging level (default: "INFO")
  - `database`: `str` - Database component logging level (default: "INFO")
  - `middleware`: `str` - Middleware component logging level (default: "INFO")
  - `controller`: `str` - Controller component logging level (default: "WARNING")

## Best Practices

1. **Secret Management**: 
   - Don't commit sensitive information like passwords or secret keys in the config file.
   - Use environment variables to inject secrets in production environments.

2. **Configuration Validation**:
   - Always access configuration through the provided functions to ensure validation.
   - Handle potential configuration errors gracefully in your application.

3. **Caching**:
   - The configuration system implements caching to avoid repeated file reads.
   - Use `force_reload=True` only when you expect the configuration file might have changed.

4. **Environment Overrides**:
   - Use environment variables for deployment-specific configuration values.
   - Remember that all environment variable values will be strings initially, though the system attempts to convert to appropriate types.

## Example Usage

```python
from src.config import get_models_config, get_database_config, get_oauth2_config

# Get all available models
models_config = get_models_config()
available_models = models_config.list_models()
print(f"Available models: {available_models}")

# Get a specific model configuration
llm_model = models_config.get_model("llama-3.3-70b-instruct")
if llm_model:
    print(f"LLM Model host: {llm_model.host}:{llm_model.port}")
    print(f"Model types: {llm_model.type}")

# Get database connection string
db_config = get_database_config()
if db_config:
    conn_str = db_config.connection_string
    print(f"Database connection: {conn_str}")

# Check if authentication is enabled
oauth2_config = get_oauth2_config()
if oauth2_config and oauth2_config.enable_authentication:
    print("Authentication is enabled")
    print(f"Token expiration: {oauth2_config.access_token_expire_minutes} minutes")
    print(f"Excluded paths: {oauth2_config.exclude_paths}")
```