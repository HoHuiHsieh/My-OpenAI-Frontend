# -*- coding: utf-8 -*-
"""
Configuration management module for the application.

Provides a centralized way to load, validate, and access configuration 
from YAML files and environment variables.
"""
import yaml
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from constant import DEFAULT_CONFIG_PATH
from .typedef import ModelsConfig, DatabaseConfig, OAuth2Config, LoggingConfig, AppConfig

# Set up a basic logger for this module to avoid circular imports with logger module
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Configuration cache
_config_cache: Optional[Dict[str, Any]] = None
_pydantic_config_cache: Optional["AppConfig"] = None


def _get_config_internal(force_reload: bool = False) -> Dict[str, Any]:
    """
    Internal function to load configuration without validation.
    Used by logger to avoid circular imports.

    Args:
        force_reload: If True, ignores the cache and reloads from file

    Returns:
        Dict[str, Any]: The configuration object or empty dict if loading fails
    """
    global _config_cache

    if _config_cache is not None and not force_reload:
        return _config_cache

    # Get config path from environment variable or use default
    config_path = Path(DEFAULT_CONFIG_PATH)

    try:
        if not config_path.exists():
            logger.warning(f"Configuration file not found at {config_path}")
            return {}

        with config_path.open("r") as file:
            config = yaml.safe_load(file)

        if config is None:
            logger.warning("Configuration file is empty")
            return {}

        # Store in cache
        _config_cache = config
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        return {}


def get_config(force_reload: bool = False) -> Dict[str, Any]:
    """
    Safely loads, validates and returns the raw configuration from the YAML file.

    Implements caching to avoid unnecessary file operations on subsequent calls.

    Args:
        force_reload: If True, ignores the cache and reloads from file

    Returns:
        Dict[str, Any]: The validated configuration object

    Raises:
        FileNotFoundError: If the config file is not found
        yaml.YAMLError: If the YAML file has syntax errors
        KeyError: If required configuration keys are missing
        ValueError: If configuration values are invalid
    """
    try:
        # Use the internal function to load the config
        config = _get_config_internal(force_reload)

        # Handle empty config
        if not config:
            config_path = Path(DEFAULT_CONFIG_PATH)
            if not config_path.exists():
                raise FileNotFoundError(
                    f"Configuration file not found at {config_path}")
            raise ValueError("Configuration file is empty")

        # Validate required configuration fields
        if not all(key in config for key in ["models"]):
            raise KeyError("Missing 'models' section in configuration")

        # Check if models dictionary is not empty
        if not config["models"]:
            raise ValueError("Models configuration is empty")

        # We now expect each model to have host and port attributes
        # Transform the config into the expected structure for backwards compatibility
        models_config = config["models"]
        hosts = []
        ports = []

        for model_name, model_config in models_config.items():
            if isinstance(model_config, dict) and all(key in model_config for key in ["host", "port"]):
                hosts.append(model_config["host"])
                ports.append(model_config["port"])

        # Store hosts and ports lists in a separate section for backwards compatibility
        # instead of adding them directly to the models dictionary
        config["_backwards_compatibility"] = {
            "hosts": hosts,
            "ports": ports
        }

        # Cache the validated config
        global _config_cache
        _config_cache = config
        logger.debug("Configuration loaded successfully")
        return config

    except (FileNotFoundError, yaml.YAMLError, KeyError, ValueError) as e:
        logger.error(f"Configuration error: {str(e)}")
        raise


def get_app_config(force_reload: bool = False) -> AppConfig:
    """
    Get the application configuration as a validated Pydantic model.

    Args:
        force_reload: If True, ignores the cache and reloads from file

    Returns:
        AppConfig: Validated application configuration

    Raises:
        Various exceptions if configuration is invalid
    """
    global _pydantic_config_cache

    if _pydantic_config_cache is not None and not force_reload:
        return _pydantic_config_cache

    # Load raw config
    raw_config = get_config(force_reload)

    # Apply environment variable overrides
    raw_config = _apply_env_overrides(raw_config)

    try:
        # Handle the models section conversion from dict to ModelsConfig
        if "models" in raw_config:
            models_dict = raw_config["models"].copy()
            # Remove host and port lists added for backwards compatibility
            if "host" in models_dict:
                del models_dict["host"]
            if "port" in models_dict:
                del models_dict["port"]
            # Create a ModelsConfig with the model_dict property
            raw_config["models"] = {"model_dict": models_dict}

        # Validate with Pydantic
        config = AppConfig(**raw_config)
        _pydantic_config_cache = config
        return config
    except Exception as e:
        logger.error(f"Configuration validation error: {str(e)}")
        raise


def _apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Override configuration values with environment variables.

    Environment variables should be in the format:
    CONFIG_<section>_<key> (all uppercase)

    For example:
    - CONFIG_DATABASE_HOST=localhost
    - CONFIG_OAUTH2_SECRET_KEY=mysecret

    Args:
        config: Raw configuration dictionary

    Returns:
        Dict[str, Any]: Configuration with environment overrides applied
    """
    # Create a copy to avoid modifying the original
    config = config.copy()

    # Process all environment variables
    for env_name, env_value in os.environ.items():
        if env_name.startswith("CONFIG_"):
            parts = env_name.split("_")
            if len(parts) < 3:
                continue

            # Extract section and key
            section = parts[1].lower()
            key = "_".join(parts[2:]).lower()

            # Skip if section doesn't exist in config
            if section not in config:
                continue

            # Convert env_value to the appropriate type
            try:
                # Handle boolean values
                if env_value.lower() in ("true", "yes", "1"):
                    env_value = True
                elif env_value.lower() in ("false", "no", "0"):
                    env_value = False
                # Handle numeric values
                elif env_value.isdigit():
                    env_value = int(env_value)
                elif env_value.replace(".", "", 1).isdigit() and env_value.count(".") == 1:
                    env_value = float(env_value)

                # Update config
                if isinstance(config[section], dict):
                    if key in config[section]:
                        logger.debug(
                            f"Overriding config[{section}][{key}] with environment variable {env_name}")
                        config[section][key] = env_value
            except Exception as e:
                logger.warning(
                    f"Failed to apply environment override {env_name}: {str(e)}")

    return config


def get_config_path() -> str:
    """
    Get the current configuration file path.

    Returns:
        str: Path to the current configuration file
    """
    return os.environ.get("CONFIG_PATH", DEFAULT_CONFIG_PATH)

# Convenience functions to access specific sections of the config


def get_models_config() -> ModelsConfig:
    """Get models configuration."""
    return get_app_config().models


def get_database_config() -> Optional[DatabaseConfig]:
    """Get database configuration."""
    return get_app_config().database


def get_oauth2_config() -> Optional[OAuth2Config]:
    """Get OAuth2 configuration."""
    return get_app_config().oauth2


def get_logging_config() -> LoggingConfig:
    """Get logging configuration."""
    return get_app_config().logging
