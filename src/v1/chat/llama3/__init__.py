"""
Llama 3 Model Family Support Module.

This module defines types and functions that are specific to the Llama 3 model family.
It supports various Llama 3 formats including:

1. Instruct Model: For standard text generation
2. Tool Use: For function/tool calling capabilities
3. Code Interpreter: For Python code generation

The module is organized into submodules for better code organization:
- constants.py: Special tokens and format markers
- formatting.py: Functions for formatting messages in Llama 3 format
- extraction.py: Functions for extracting responses from Llama 3 models
- utils.py: Utility functions for working with Llama 3 models
"""

# Import all relevant components
from .constants import (
    BEGIN_OF_TEXT, END_OF_TEXT, START_HEADER, END_HEADER,
    END_OF_MESSAGE, END_OF_TURN, PYTHON_TAG
)

from .formatting import format_messages_for_llama3, format_tools_for_llama3
from .extraction import extract_assistant_response
from .utils import is_llama3_model

# Make the imports available at the module level
__all__ = [
    # Constants
    'BEGIN_OF_TEXT', 'END_OF_TEXT', 'START_HEADER', 'END_HEADER',
    'END_OF_MESSAGE', 'END_OF_TURN', 'PYTHON_TAG',
    
    # Functions
    'format_messages_for_llama3', 'extract_assistant_response',
    'is_llama3_model', 'format_tools_for_llama3'
]
