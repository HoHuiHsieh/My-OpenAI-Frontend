"""
Utility functions for Home Made Agent models.

This module provides helper functions for working with Home Made Agent models,
such as model identification and validation.
"""

from logger import get_logger

# Set up logger for this module
logger = get_logger(__name__)


def is_home_made_agent_model(model_name: str) -> bool:
    """
    Determine if a model is a home made AI agent based on its name.

    Args:
        model_name: The name of the model

    Returns:
        True if the model is a home made AI agent  model, False otherwise
    """
    model_name_lower = model_name.lower()
    identifiers = ["my-agent-for-test", "my-doc-agent"]
    return any(identifier in model_name_lower for identifier in identifiers)
