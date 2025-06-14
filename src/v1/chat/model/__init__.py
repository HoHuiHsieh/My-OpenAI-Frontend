"""
"""
import random
import uuid
import asyncio
import numpy as np
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from tritonclient.utils import InferenceServerException
import tritonclient.grpc as grpcclient
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR, HTTP_400_BAD_REQUEST
from logger import get_logger, UsageLogger
from config import get_config
from typing import List
from ..typedef import CreateChatCompletionRequest
from ..llama3 import is_llama3_model, format_messages_for_llama3
from ..agent import is_home_made_agent_model, format_messages_for_home_made_agent
from .prepare import prepare_triton_inputs_with_seed, prepare_my_agent_inputs
from .stream_processor import setup_triton_stream, StreamingResponseCallback
from .collector import collect_stream_response
from .response import prepare_chat_completion_response
from .streamer import stream_generator


# Set up logger for this module
logger = get_logger(__name__)

# Safely load configuration with validation
config = get_config(force_reload=False)


class TritonConnection():
    def __init__(self, host: str, port: int, body: CreateChatCompletionRequest, api_key: str):
        self.host = host
        self.port = port
        self.body = body
        self.api_key = api_key
        self.client: grpcclient.InferenceServerClient = None
        self.text_input: str = None
        self.encoded_files: bytes = None
        self.inputs: List[grpcclient.InferInput] = None
        self.outputs: List[grpcclient.InferRequestedOutput] = None
        self.model_type: str = None  # Model type to determine capabilities

    @property
    def url(self):
        return f"{self.host}:{self.port}"

    def get_client(self):
        """
        Create a gRPC client for the Triton server.
        """
        try:
            # Create a gRPC client for Triton server
            url = self.url
            logger.info(f"Connecting to Triton server at {url}")
            client = grpcclient.InferenceServerClient(url=url, verbose=False)

            # Check if the server is ready
            if not client.is_server_ready():
                raise HTTPException(
                    status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Model server is not ready"
                )
            self.client = client
            return self

        except InferenceServerException as e:
            logger.error(f"Error connecting to Triton server: {e}")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to connect to model server"
            )

    def format(self):
        """
        Format the request body for the Triton server.
        """
        # Get model types from config to determine if vision is supported
        model_types = self.body.model_config.get("type", ["chat"])

        # Call formatter with model types to handle content based on capabilities
        if is_llama3_model(self.body.model):
            self.text_input, self.encoded_files = format_messages_for_llama3(
                self.body.messages, self.body.tools, self.body.response_format, model_types)
            self.model_type = "llama3"
        elif is_home_made_agent_model(self.body.model):
            self.text_input, self.encoded_files = format_messages_for_home_made_agent(
                self.body.messages)
            self.model_type = "home_made_agent"
        else:
            self.text_input = None
            self.encoded_files = None

        if not self.text_input:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"No specific formatter defined for model {self.body.model}."
            )
        return self

    def prepare(self):
        """
        Prepare the Triton inputs and outputs for inference.
        """
        if not self.text_input:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Text input is required for inference"
            )
        # Generate a random seed for reproducibility
        seed = random.randint(0, 2**31 - 1)

        # Prepare inputs with the generated seed
        if is_llama3_model(self.body.model):
            self.inputs = prepare_triton_inputs_with_seed(
                body=self.body,
                text_input=self.text_input,
                seed=seed,
                encoded_files=self.encoded_files
            )
            self.outputs = [
                grpcclient.InferRequestedOutput("text_output"),
            ]
        elif is_home_made_agent_model(self.body.model):
            self.inputs = prepare_my_agent_inputs(
                text_input=self.text_input,
                api_key=self.api_key
            )
            self.outputs = [
                grpcclient.InferRequestedOutput("text_output"),
            ]
        else:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"No specific input preparation defined for model {self.body.model}."
            )

        return self

    def tokenizor(self, tokens: List[int]) -> str:
        """
        Tokenize the input text using Triton server's postprocessing model.
        This method sends the tokens to the Triton server for tokenization and returns the tokenized text.
        
        Note: This method doesn't close the client connection because the connection is reused.
        The connection will be closed elsewhere when processing is complete.
        """
        # Ensure the client is initialized
        if not self.client:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Triton client is not initialized"
            )
        client = self.client

        # Prepare the inputs for tokenization
        inputs = [
            grpcclient.InferInput("tokens", [len(tokens)], "INT32"),
        ]
        inputs[0].set_data_from_numpy(np.array(tokens, dtype=np.int32))

        # Prepare the outputs for tokenization
        outputs = [
            grpcclient.InferRequestedOutput("output")
        ]

        # Get the stored request_id if available, otherwise generate a new one
        req_id = getattr(self, 'request_id', None) or str(uuid.uuid4())
        
        # Perform inference to get the tokenized text
        try:
            response = client.infer(
                model_name="tokenize",
                inputs=inputs,
                outputs=outputs,
                request_id=req_id
            )
            # Extract the tokenized text from the response
            tokenized_text = response.as_numpy("output")[0].decode('utf-8')
            return tokenized_text
        except InferenceServerException as e:
            logger.error(f"Error during tokenization: {e}")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to tokenize input: {str(e)}"
            )

    @staticmethod
    def _setup_triton_connection(host: str, port: int, body: CreateChatCompletionRequest, api_key: str = None):
        """
        Common setup for both infer and async_infer methods.
        Sets up the TritonConnection and prepares it for inference.
        
        Args:
            host: The host address of the Triton server
            port: The port of the Triton server
            body: The request body
            api_key: Optional API key
            
        Returns:
            A tuple containing (infer, model, client, inputs, outputs)
        """
        infer = TritonConnection(host, port, body, api_key)
        infer.get_client().format().prepare()
        model = body.model
        client = infer.client
        inputs = infer.inputs
        outputs = infer.outputs
        
        return infer, model, client, inputs, outputs
    
    @staticmethod
    def _normalize_stop_sequences(body):
        """
        Normalize stop sequences from the request body.
        
        Args:
            body: The request body containing stop sequences
            
        Returns:
            Normalized list of stop sequences
        """
        if hasattr(body, 'stop') and body.stop:
            if not isinstance(body.stop, list):
                body.stop = [body.stop]
        else:
            body.stop = []
        return [s.strip() for s in body.stop if s.strip()]
    
    @staticmethod
    def _get_max_tokens(body):
        """
        Get max tokens from the request body if available.
        
        Args:
            body: The request body
            
        Returns:
            Max tokens or None if not specified
        """
        return body.max_completion_tokens if hasattr(body, 'max_completion_tokens') else None
    
    @staticmethod
    async def infer(host: str, port: int, body: CreateChatCompletionRequest, user_id: str, api_key: str = None):
        """
        Perform inference using the prepared inputs and outputs.
        Supports parallel requests and aggregates responses.
        """
        # Create a list to hold tasks and clients
        tasks = []
        clients = []
        infer = None

        # Get the number of parallel requests from the body
        num_parallel_requests = body.n if hasattr(body, 'n') and body.n > 1 else 1

        # Normalize stop sequences
        body.stop = TritonConnection._normalize_stop_sequences(body)
        max_tokens = TritonConnection._get_max_tokens(body)
        
        # Generate a base request ID to use across all parallel requests
        base_request_id = uuid.uuid4().hex

        # Start all the parallel requests
        for i in range(num_parallel_requests):
            try:
                # Setup connection for this request
                conn, model, client, inputs, outputs = TritonConnection._setup_triton_connection(
                    host, port, body, api_key
                )
                # Store the first connection to access its properties later
                if infer is None:
                    infer = conn
                    
                request_id = f"{base_request_id}-{i}"
                
                # Set up the stream for this client
                callback = await setup_triton_stream(client, model, inputs, outputs, request_id)

                # Create tokenizor function
                tokenizor_infer = TritonConnection(host, port, body, api_key)
                tokenizor_infer.request_id = request_id  # Store the request ID in the tokenizor client

                # Create a task to collect the response
                task = asyncio.create_task(
                    collect_stream_response(
                        callback, 
                        client, 
                        tokenizor_infer,
                        timeout=120,
                        stop_dict=body.stop,
                        max_tokens=max_tokens,
                        request_id=request_id
                    )
                )

                clients.append(client)
                tasks.append((task, client))

            except Exception as e:
                logger.error(f"Failed to start parallel request {i}: {e}")
                # Clean up any clients we've created
                for client in clients:
                    try:
                        client.stop_stream()
                        client.close()
                        logger.debug(f"Closed client during error handling")
                    except Exception as close_error:
                        logger.debug(f"Error closing client: {close_error}")
                        pass
                # Close the tokenizor_infer client if it exists
                if 'tokenizor_infer' in locals() and tokenizor_infer and tokenizor_infer.client:
                    try:
                        tokenizor_infer.client.close()
                        logger.debug("Closed tokenizor_infer client during error handling")
                    except Exception as close_error:
                        logger.debug(f"Error closing tokenizor_infer client: {close_error}")
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
                        logger.warning("Empty response from parallel request")
                except Exception as e:
                    logger.error(f"Error collecting parallel response: {e}")
                finally:
                    # Note: client closing is handled by collect_stream_response via StreamCollector.cleanup_resources
                    # This is a backup mechanism in case that fails
                    try:
                        client.stop_stream()
                        client.close()
                        logger.debug("Backup client cleanup in finally block")
                    except Exception as close_error:
                        logger.debug(f"Error in backup client cleanup: {close_error}")
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
        ignore_usage = infer.model_type == "home_made_agent"
        # Use the same base request ID that was used for the parallel requests
        final_response = await prepare_chat_completion_response(
            responses, 
            body, 
            infer.text_input, 
            ignore_usage=ignore_usage,
            request_id=base_request_id
        )
        logger.debug(f"Final infer response: {final_response}")

        # Log the usage information
        UsageLogger.log_chat_usage(
            user_id=user_id,
            model=body.model,
            prompt_tokens=final_response.usage.prompt_tokens,
            completion_tokens=final_response.usage.completion_tokens,
            total_tokens=final_response.usage.total_tokens,
            request_id=final_response.id
        )

        return final_response

    @staticmethod
    async def async_infer(host: str, port: int, body: CreateChatCompletionRequest, user_id: str, api_key: str = None):
        """
        Asynchronously perform inference using the prepared inputs and outputs.
        Returns a streaming response for immediate consumption by clients.
        """
        # Setup connection
        infer, model, client, inputs, outputs = TritonConnection._setup_triton_connection(host, port, body, api_key)
        
        # Normalize stop sequences
        body.stop = TritonConnection._normalize_stop_sequences(body)
        max_tokens = TritonConnection._get_max_tokens(body)
        
        # Generate a single request ID - use a consistent format with the infer method
        request_id = f"{uuid.uuid4().hex}-0"

        # For streaming we need to generate one response at a time since parallelizing
        # would make the stream confusing to clients
        callback = await setup_triton_stream(client, model, inputs, outputs, request_id)

        # Create tokenizor function
        tokenizor_client = TritonConnection(host, port, body, api_key)

        # Get tools configuration if available
        tools = body.tools if hasattr(body, 'tools') else None
        parallel_tool_calls = body.parallel_tool_calls if hasattr(body, 'parallel_tool_calls') else True
        
        # Get response format if available
        response_format = 'text'
        if hasattr(body, 'response_format') and hasattr(body.response_format, 'type'):
            response_format = body.response_format.type
            
        # Check if we should ignore usage stats based on model type
        ignore_usage = infer.model_type == "home_made_agent"

        return StreamingResponse(
            stream_generator(
                callback,
                client,
                tokenizor_client,
                body.model,
                infer.text_input,
                tools=tools,
                parallel_tool_calls=parallel_tool_calls,
                response_format=response_format,
                timeout=120,
                stop_dict=body.stop,
                max_tokens=max_tokens,
                ignore_usage=ignore_usage,
                request_id=request_id
            ),
            media_type="text/event-stream"
        )
