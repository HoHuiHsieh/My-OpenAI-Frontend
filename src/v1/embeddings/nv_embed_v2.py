"""
NVIDIA Embed V2 Model Utilities

Provides helper functions for the NVIDIA Embed V2 model, including model detection
and input formatting.
"""

from typing import List, Optional


def is_nv_embed_v2_model(model_name: str) -> bool:
    """
    Check if the given model name is an NVIDIA Embed V2 model.
    
    Args:
        model_name: Name of the model to check
        
    Returns:
        True if the model is an NVIDIA Embed V2 model, False otherwise
    """
    return model_name.lower() in ["nv-embed-v2", "nvidia/nv-embed-v2", "nvidia/embed-v2"]
