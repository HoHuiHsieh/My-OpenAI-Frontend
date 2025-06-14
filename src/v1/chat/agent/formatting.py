"""
Formatting utilities for Home Made Agent models.
"""
import json
from typing import List, Dict, Any, Optional, Union, Tuple
from ..typedef import ChatMessage
from logger import get_logger

# Set up logger for this module
logger = get_logger(__name__)


def format_messages_for_home_made_agent(
        messages: List[ChatMessage],
) -> Tuple[str, Optional[List[Dict[str, Any]]]]:
    """
    """
    formatted_messages = []
    encoded_files = []

    for msg in messages:
        # # Skip system messages
        # if msg.role == 'system' or msg.role == 'developer':
        #     logger.debug("Skipping system message.")
        #     continue

        content = ""

        if isinstance(msg.content, str):
            # Simple string content
            content = msg.content
        elif isinstance(msg.content, list):
            # Process list content
            text_parts = []

            for part in msg.content:
                if isinstance(part, str):
                    # String item in list
                    text_parts.append(part)
                elif hasattr(part, 'type'):
                    # Content part object
                    if part.type == 'text':
                        text_parts.append(part.text)
                    elif part.type == 'file':
                        # Extract file info and add to encoded_files
                        file_data = getattr(part.file, 'file_data', None)
                        filename = getattr(part.file, 'filename', None)
                        if file_data and filename:
                            encoded_files.append({
                                "data": file_data,
                                "filename": filename
                            })
                            # Add reference to the file in the content
                            text_parts.append(f"[File: {filename}]")

            # Join all text parts into a single string
            content = "\n".join(text_parts)

        formatted_message = {
            "role": msg.role,
            "content": content
        }
        formatted_messages.append(formatted_message)

    stringifyed_messages = json.dumps({"messages": formatted_messages},
                                      ensure_ascii=False)
    logger.debug(f"Formatted messages: {stringifyed_messages}")

    return stringifyed_messages, None


# role: str = Field(
#         description="The role of the message author. One of 'developer', 'system', 'user', 'assistant', or 'tool'."
#     )
#     content: Optional[Union[
#         str,
#         List[str],
#         List[TextContentPart | FileContentPart],
#     ]] = Field(
#         des


# class TextContentPart(BaseModel):
#     """
#     Represents a text content part of a message.
#     """
#     type: Literal["text"] = Field(
#         default="text",
#         description="The type of content. Currently only 'text' is supported."
#     )
#     text: str = Field(
#         description="The text content."
#     )


# class FileObject(BaseModel):
#     """
#     Represents a file object.
#     """
#     file_data: Optional[str] = Field(
#         default=None,
#         description="The base64 encoded file data, used when passing the file to the model as a string."
#     )
#     file_id: Optional[str] = Field(
#         default=None,
#         description="The ID of an uploaded file to use as input."
#     )
#     filename: Optional[str] = Field(
#         default=None,
#         description="The name of the file, used when passing the file to the model as a string."
#     )


# class FileContentPart(BaseModel):
#     """
#     Represents a file content part of a message.
#     """
#     type: str = Field(
#         default="file",
#         description="The type of content. Currently only 'file' is supported."
#     )
#     file: FileObject = Field(
#         description="The file content."
#     )
