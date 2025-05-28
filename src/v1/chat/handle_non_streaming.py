""""""
import asyncio
import time
import uuid
import numpy as np
from fastapi import HTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
import tritonclient.grpc as grpcclient

from logger import get_logger, UsageLogger
from config import get_config
from .triton_client import (
    prepare_triton_inputs_with_seed, 
    _setup_triton_stream, 
    collect_stream_response
)
from .response_processing import process_triton_response
from .typedef import CreateChatCompletionResponse
from .token_counter import create_usage_info

# Set up logger for this module
logger = get_logger(__name__)

# Safely load configuration with validation
config = get_config(force_reload=False)


async def handle_non_streaming_response(model_name, outputs, body, input_data_bytes, encoded_files=None, user_id=""):
    """Handle non-streaming responses for both single and parallel completion requests.
    
    Args:
        model_name: Name of the model
        outputs: The requested outputs from Triton
        body: The request body
        input_data_bytes: The input data bytes
        encoded_files: Optional list of encoded file data for vision models
        
    Returns:
        A chat completion response with one or more choices
    """
    # Default n to 1 if not specified or less than 1
    n = max(1, body.n)
    
    # Process multiple completions in parallel
    if n > 1:
        logger.info(f"Processing {n} parallel completions for request")
    
    # Create a list to hold tasks
    tasks = []
    # Create callbacks for each parallel request
    clients = []
    
    # Start all the parallel requests
    for i in range(n):
        try:
            # Extract the server URL from the model configuration
            model_config = config.get("models", {}).get(body.model, {})
            host = model_config.get("host", "localhost")
            port = model_config.get("port", 8001)
            server_url = f"{host}:{port}"
            
            # For each parallel request, we need a new client to avoid conflicts
            client = grpcclient.InferenceServerClient(url=server_url, verbose=False)
            clients.append(client)
            
            # Set up the stream for this client
            # Create new inputs with a different seed for each request
            # We need to pass the original input_data_bytes directly instead of trying to extract it from inputs
            request_inputs = prepare_triton_inputs_with_seed(
                body, 
                input_data_bytes,  # Use the original input_data_bytes from the parent function
                int(time.time() * 1000) + i * 1000,
                encoded_files  # Pass encoded_files if any
            )
            
            callback = await _setup_triton_stream(
                client, 
                model_name, 
                request_inputs,
                outputs, 
                request_id=f"{uuid.uuid4().hex}-{i}"
            )
            
            # Create a task to collect the response
            task = asyncio.create_task(
                collect_stream_response(callback, client, timeout=120)
            )
            tasks.append((task, client))
            
        except Exception as e:
            logger.error(f"Failed to start parallel request {i}: {e}")
            # Clean up any clients we've created
            for client in clients:
                try:
                    client.stop_stream()
                except Exception:
                    pass
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process parallel request: {str(e)}"
            )
    
    # Wait for all tasks to complete
    responses = []
    try:
        # Gather all responses
        for task, client in tasks:
            try:
                complete_response = await task
                if complete_response:
                    responses.append(complete_response)
                else:
                    logger.warning(f"Empty response from parallel request")
            except Exception as e:
                logger.error(f"Error collecting parallel response: {e}")
            finally:
                try:
                    client.stop_stream()
                except Exception:
                    pass
    
    except Exception as e:
        logger.error(f"Error gathering parallel responses: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing parallel requests: {str(e)}"
        )
    
    # Check if we got any responses
    if not responses:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="All parallel requests failed to produce responses"
        )
    
    # Process all successful responses into a single response with multiple choices
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created_time = int(time.time())
    
    all_choices = []
    tool_calls_list = []
    
    # Get input text from request body for token counting
    input_text = ""
    if hasattr(body, 'messages'):
        for msg in body.messages:
            if hasattr(msg, 'content') and msg.content:
                input_text += msg.content + "\n"
    
    # Process each response text
    for i, response_text in enumerate(responses):
        synthetic_response = type('obj', (object,), {'as_numpy': lambda name: np.array(
            [response_text.encode('utf-8')]) if name == 'output' else None})
        
        # Process the individual response to get the choice
        individual_response = await process_triton_response(synthetic_response, body.model, body.model_dump())
        
        # Extract the choice and update its index
        for choice in individual_response.choices:
            choice.index = i
            all_choices.append(choice)
            
            # Collect tool calls for token counting
            if choice.message and choice.message.tool_calls:
                tool_calls_list.extend([t for t in choice.message.tool_calls])
    
    # Get actual completions to count
    completions = [choice.message.content for choice in all_choices if choice.message and choice.message.content]

    # Create an accurate usage info with token counting - use completion_id as request_id for independent tracking
    usage = await create_usage_info(
        model=body.model,
        input_text=input_text,
        completion=completions,
        tool_calls=tool_calls_list if len(tool_calls_list) > 0 else None,
        request_id=completion_id
    )
    
    # Create the final response
    final_response = CreateChatCompletionResponse(
        id=completion_id,
        created=created_time,
        model=body.model,
        choices=all_choices,
        usage=usage
    )
    
    # Log the usage information
    UsageLogger.log_chat_usage(
        user_id=user_id,
        model=body.model,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        total_tokens=usage.total_tokens,
        request_id=completion_id
    )

    return final_response

