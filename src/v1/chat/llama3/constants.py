"""
Constants for the Llama 3 model family.

This module defines the special tokens and constants used by the Llama 3 models
in their prompt format and response structure.
"""

# Start of the prompt
BEGIN_OF_TEXT = "<|begin_of_text|>"

# End of generation - generated only by base models
END_OF_TEXT = "<|end_of_text|>"

# Message role header markers
START_HEADER = "<|start_header_id|>"
END_HEADER = "<|end_header_id|>"

# End of a message - stopping point for tool calls
END_OF_MESSAGE = "<|eom_id|>"

# End of turn - marks the completion of interaction with a user message
END_OF_TURN = "<|eot_id|>"

# Special tag for Python code in responses
PYTHON_TAG = "<|python_tag|>"

# Special tag for image content in responses
IMAGE_TAG = "<|image|>"