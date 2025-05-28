"""
Utility functions for Llama 3 models.

This module provides helper functions for working with Llama 3 models,
such as model identification and validation.
"""

from logger import get_logger

# Set up logger for this module
logger = get_logger(__name__)


def is_llama3_model(model_name: str) -> bool:
    """
    Determine if a model is a Llama 3 model based on its name.

    Args:
        model_name: The name of the model

    Returns:
        True if the model is a Llama 3 model, False otherwise
    """
    # Check if the model name contains llama-3, llama3, or other Llama 3 identifiers
    model_name_lower = model_name.lower()
    llama3_identifiers = ["llama-3", "llama3", "meta/llama-3"]
    return any(identifier in model_name_lower for identifier in llama3_identifiers)
