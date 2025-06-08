"""
"""
import random
import uuid
import asyncio
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
from .prepare import prepare_triton_inputs_with_seed
from .inference import setup_triton_stream, collect_stream_response
from .response import prepare_chat_completion_response
from .streaming import stream_generator


# Set up logger for this module
logger = get_logger(__name__)

# Safely load configuration with validation
config = get_config(force_reload=False)


class TritonConnection():
    def __init__(self, host: str, port: int, body: CreateChatCompletionRequest):
        self.host = host
        self.port = port
        self.body = body
        self.client: grpcclient.InferenceServerClient = None
        self.text_input: str = None
        self.encoded_files: bytes = None
        self.inputs: List[grpcclient.InferInput] = None
        self.outputs: List[grpcclient.InferRequestedOutput] = None

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
        self.inputs = prepare_triton_inputs_with_seed(
            body=self.body,  # No body needed here, we handle inputs directly
            text_input=self.text_input,
            seed=seed,
            encoded_files=self.encoded_files
        )

        # Prepare outputs
        self.outputs = [
            grpcclient.InferRequestedOutput("text_output"),
        ]

        return self

    @staticmethod
    async def infer(host: str, port: int, body: CreateChatCompletionRequest, user_id: str):
        """
        Perform inference using the prepared inputs and outputs.
        """
        # Create a list to hold tasks
        tasks = []
        # Create callbacks for each parallel request
        clients = []
        # Get the number of parallel requests from the body
        num_parallel_requests = body.n if hasattr(body, 'n') and body.n > 1 else 1

        # Start all the parallel requests
        for i in range(num_parallel_requests):
            try:
                infer = TritonConnection(host, port, body)
                infer.get_client().format().prepare()
                model = body.model
                client = infer.client
                inputs = infer.inputs
                outputs = infer.outputs
                request_id = f"{uuid.uuid4().hex}-{i}"

                # Configure stop sequences if provided
                if hasattr(body, 'stop') and body.stop:
                    if not isinstance(body.stop, list):
                        body.stop = [body.stop]
                else:
                    body.stop = []
                body.stop = [s.strip() for s in body.stop if s.strip()]

                # Set up the stream for this client
                callback = await setup_triton_stream(client, model, inputs, outputs, request_id)

                # Create a task to collect the response
                task = asyncio.create_task(
                    collect_stream_response(callback, client,
                                            timeout=120,
                                            stop_dict=body.stop)
                )

                clients.append(client)
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
        final_response = await prepare_chat_completion_response(responses, body, infer.text_input)

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
    async def async_infer(host: str, port: int, body: CreateChatCompletionRequest, user_id: str):
        """
        Asynchronously perform inference using the prepared inputs and outputs.
        """
        infer = TritonConnection(host, port, body)
        infer.get_client().format().prepare()
        model = body.model
        client = infer.client
        inputs = infer.inputs
        outputs = infer.outputs
        request_id = f"{uuid.uuid4().hex}"

        # Configure stop sequences if provided
        if hasattr(body, 'stop') and body.stop:
            if not isinstance(body.stop, list):
                body.stop = [body.stop]
        else:
            body.stop = []
        body.stop = [s.strip() for s in body.stop if s.strip()]

        # For streaming we need to generate one response at a time since parallelizing
        # would make the stream confusing to clients
        callback = await setup_triton_stream(client, model, inputs, outputs, request_id)

        return StreamingResponse(
            stream_generator(
                callback,
                client,
                body.model,
                infer.text_input,
                tools=body.tools if hasattr(body, 'tools') else None,
                parallel_tool_calls=body.parallel_tool_calls if hasattr(
                    body, 'parallel_tool_calls') else True,
                response_format=body.response_format.type if hasattr(
                    body, 'response_format') and hasattr(body.response_format, 'type') else 'text',
                timeout=120,
                stop_dict=body.stop
            ),
            media_type="text/event-stream"
        )
