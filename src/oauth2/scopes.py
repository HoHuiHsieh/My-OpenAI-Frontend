"""
API scope definitions and management.

This module defines the available API scopes and provides
functionality for scope management.
"""

from typing import Dict, List, Set
from enum import Enum, auto
from logger import get_logger

# Initialize logger
logger = get_logger(__name__)

class Scopes(str, Enum):
    """Enumeration of available API scopes."""
    ADMIN = "admin"
    MODELS_READ = "models:read"
    CHAT_READ = "chat:read"
    EMBEDDINGS_READ = "embeddings:read"


# Get available scopes
available_scopes = [
    Scopes.ADMIN,
    Scopes.MODELS_READ,
    Scopes.CHAT_READ,
    Scopes.EMBEDDINGS_READ
]

# Define admin scopes
admin_scopes = available_scopes

# Define user scopes
user_scopes = [
    Scopes.MODELS_READ,
    Scopes.CHAT_READ,
    Scopes.EMBEDDINGS_READ
]

# Map of scope to description for documentation
scope_descriptions: Dict[str, str] = {
    Scopes.ADMIN: "Full administrative access",
    Scopes.MODELS_READ: "Read access to model endpoints",
    Scopes.CHAT_READ: "Read access to chat endpoints",
    Scopes.EMBEDDINGS_READ: "Read access to embedding endpoints"
}


def get_scope_description(scope: str) -> str:
    """
    Get the description for a specific scope.
    
    Args:
        scope: The scope name
        
    Returns:
        str: The scope description or a default message if not found
    """
    return scope_descriptions.get(scope, "No description available")


def validate_scopes(scopes: List[str]) -> List[str]:
    """
    Validate a list of scopes against available scopes.
    
    Args:
        scopes: List of scopes to validate
        
    Returns:
        List[str]: List of valid scopes (invalid scopes are removed)
    """
    valid_scopes = []
    for scope in scopes:
        if scope in available_scopes:
            valid_scopes.append(scope)
        else:
            logger.warning(f"Invalid scope requested: {scope}")
    
    return valid_scopes
