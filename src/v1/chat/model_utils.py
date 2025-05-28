"""
Utility functions for model handling in the chat module.
"""

from typing import List, Dict, Any, Optional
from config import get_config
from logger import get_logger

# Set up logger for this module
logger = get_logger(__name__)

def get_model_types(model_name: str) -> List[str]:
    """
    Get the types supported by a specific model from the config.
    
    Args:
        model_name: The name of the model to check
        
    Returns:
        A list of supported types for the model (e.g., ['chat', 'vision'])
    """
    try:
        # Use the config package to get configuration
        config = get_config()
        
        # Get model configuration
        models_config = config.get("models", {})
        
        if model_name in models_config:
            return models_config[model_name].get("type", ["chat"])
        else:
            logger.warning(f"Model {model_name} not found in configuration. Defaulting to ['chat']")
            return ["chat"]
            
    except Exception as e:
        logger.error(f"Error loading model types from config: {str(e)}")
        return ["chat"]  # Default to chat if we can't load the config
