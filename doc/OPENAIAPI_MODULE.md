# OPENAIAPI Module Documentation (v1)

## Overview

The OPENAIAPI module (v1) provides OpenAI-compatible API endpoints for various AI services including chat completions, text embeddings, and audio transcriptions. It implements the OpenAI API specification while allowing integration with custom model backends and authentication systems.

## Features

- **OpenAI API Compatibility**: Full compliance with OpenAI API specifications
- **Multi-Service Support**: Chat completions, embeddings, and audio transcription
- **Model Management**: Dynamic model discovery and filtering based on capabilities
- **Authentication Integration**: API key validation with scope-based authorization
- **Streaming Support**: Real-time streaming for chat completions
- **Usage Tracking**: Comprehensive logging of API usage and token consumption
- **Error Handling**: Robust error handling with proper HTTP status codes
- **File Upload Support**: Audio file processing for transcription services

## Module Structure

```
src/v1/
├── __init__.py              # Module initialization and exports
├── routes/
│   ├── __init__.py         # Router initialization and aggregation
│   ├── models.py           # Model listing endpoint
│   ├── chat.py             # Chat completion endpoints
│   ├── embeddings.py       # Embedding generation endpoints
│   └── audio.py            # Audio transcription endpoints
├── chat/
│   ├── __init__.py         # Chat package exports
│   ├── models/             # Chat completion data models
│   ├── action/             # Chat completion business logic
│   └── llama3/             # Model-specific implementations
├── embeddings/
│   ├── __init__.py         # Embeddings package exports
│   ├── models.py           # Embedding data models
│   ├── action.py           # Embedding business logic
│   └── util.py             # Utility functions
└── audio/
    ├── __init__.py         # Audio package exports
    ├── models.py           # Audio transcription models
    ├── action.py           # Transcription business logic
    └── util.py             # Audio processing utilities
```

## API Endpoints

### Model Management

#### GET /v1/models
List all available models with user scope filtering.

**Authentication:** Requires API key with `models:read` scope

**Response:**
```json
[
    {
        "id": "llama-3.3-70b-instruct",
        "created": 1749095099,
        "object": "model",
        "owned_by": "organization-owner"
    },
    {
        "id": "nv-embed-v2",
        "created": 1749095099,
        "object": "model", 
        "owned_by": "organization-owner"
    }
]
```

**Features:**
- Dynamic model filtering based on user scopes
- Model capabilities matching (chat, embeddings, audio)
- Configuration-driven model discovery

### Chat Completions

#### POST /v1/chat/completions
Create chat completions with support for streaming and non-streaming modes.

**Authentication:** Requires API key with `chat:base` scope

**Request Body:**
```json
{
    "model": "llama-3.3-70b-instruct",
    "messages": [
        {
            "role": "system",
            "content": "You are a helpful assistant."
        },
        {
            "role": "user", 
            "content": "Hello, how are you?"
        }
    ],
    "temperature": 0.7,
    "max_tokens": 150,
    "stream": false
}
```

**Response (Non-streaming):**
```json
{
    "id": "chatcmpl-abc123",
    "object": "chat.completion",
    "created": 1677649420,
    "model": "llama-3.3-70b-instruct",
    "usage": {
        "prompt_tokens": 20,
        "completion_tokens": 30,
        "total_tokens": 50
    },
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Hello! I'm doing well, thank you for asking."
            },
            "finish_reason": "stop"
        }
    ]
}
```

**Response (Streaming):**
```
data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1677649420,"model":"llama-3.3-70b-instruct","choices":[{"index":0,"delta":{"role":"assistant","content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1677649420,"model":"llama-3.3-70b-instruct","choices":[{"index":0,"delta":{"content":"!"},"finish_reason":null}]}

data: [DONE]
```

**Supported Message Types:**
- **System Messages**: Instructions and context
- **User Messages**: User input with text, images, audio, or files
- **Assistant Messages**: AI responses with optional tool calls
- **Tool Messages**: Tool execution results
- **Developer Messages**: Development and debugging context

**Features:**
- Multiple content types (text, image, audio, file)
- Tool calling support with function definitions
- Streaming and non-streaming modes
- Temperature and token limit controls
- Usage tracking and logging

### Embeddings

#### POST /v1/embeddings
Generate text embeddings for input text or text arrays.

**Authentication:** Requires API key with `embeddings:base` scope

**Request Body:**
```json
{
    "model": "nv-embed-v2",
    "input": [
        "The quick brown fox jumps over the lazy dog",
        "Machine learning is transforming technology"
    ],
    "encoding_format": "float",
    "dimensions": 1024
}
```

**Response:**
```json
{
    "object": "list",
    "data": [
        {
            "object": "embedding",
            "index": 0,
            "embedding": [0.1, -0.2, 0.3, ...]
        },
        {
            "object": "embedding", 
            "index": 1,
            "embedding": [0.4, -0.1, 0.5, ...]
        }
    ],
    "model": "nv-embed-v2",
    "usage": {
        "prompt_tokens": 15,
        "total_tokens": 15
    }
}
```

**Features:**
- Batch processing for multiple inputs
- Configurable encoding formats (float, base64)
- Dimension specification support
- Token usage tracking
- Input validation and sanitization

### Audio Transcription

#### POST /v1/audio/transcriptions
Transcribe audio files to text using speech-to-text models.

**Authentication:** Requires API key with `audio:transcribe` scope

**Request (multipart/form-data):**
```
file: [audio file binary data]
model: whisper-large-v3-turbo
```

**Response:**
```json
{
    "text": "Hello, this is a test transcription of the audio file."
}
```

**Supported Formats:**
- WAV, MP3, MP4, MPEG, MPGA, M4A, WEBM
- Maximum file size: 25MB
- Various sample rates and bit rates

**Features:**
- Multiple audio format support
- Automatic format detection
- High-quality transcription models
- File validation and processing

## Data Models

### Chat Completion Models

#### ChatCompletionRequest
Comprehensive request model supporting all OpenAI chat completion features:
```python
class ChatCompletionRequest(BaseModel):
    model: str                              # Model identifier
    messages: List[ChatCompletionMessages]  # Conversation messages
    temperature: Optional[float] = 1.0      # Randomness control (0-2)
    max_tokens: Optional[int] = None        # Maximum response tokens
    stream: Optional[bool] = False          # Enable streaming mode
    tools: Optional[List[Tool]] = None      # Available function tools
    tool_choice: Optional[ToolChoice] = None # Tool selection strategy
    user: Optional[str] = None              # End-user identifier
```

#### Message Types
Support for various message content types:
- **TextContentPart**: Plain text content
- **ImageContentPart**: Image URLs or base64 data
- **AudioContentPart**: Audio data in WAV or MP3
- **FileContentPart**: File attachments with metadata
- **RefusalContentPart**: Model refusal responses

#### ChatCompletionResponse
Standard and streaming response models with usage tracking:
```python
class ChatCompletionResponse(BaseModel):
    id: str                    # Unique completion ID
    object: str               # Response type ("chat.completion")
    created: int              # Unix timestamp
    model: str                # Model used
    choices: List[Choice]     # Generated completions
    usage: UsageInfo         # Token consumption data
```

### Embedding Models

#### EmbeddingsRequest
```python
class EmbeddingsRequest(BaseModel):
    model: str                              # Embedding model name
    input: Union[str, List[str]]           # Text(s) to embed
    encoding_format: Optional[str] = "float" # Output format
    dimensions: Optional[int] = None        # Output dimensions
    user: Optional[str] = None             # End-user identifier
```

#### EmbeddingsResponse
```python
class EmbeddingsResponse(BaseModel):
    object: str = "list"              # Response type
    data: List[EmbeddingData]        # Embedding vectors
    model: str                       # Model used
    usage: Usage                     # Token usage info
```

### Audio Models

#### TranscriptionRequest
```python
class TranscriptionRequest(BaseModel):
    file: UploadFile            # Audio file upload
    model: str                  # Transcription model
```

#### TranscriptionResponse
```python
class TranscriptionResponse(BaseModel):
    text: str                   # Transcribed text
```

## Authentication and Authorization

### API Key Authentication
All endpoints require Bearer token authentication:
```http
Authorization: Bearer <api_key>
```

### Scope-Based Authorization
Different endpoints require specific scopes:
- **models:read**: Access to model listing
- **chat:base**: Chat completion access
- **embeddings:base**: Embedding generation access  
- **audio:transcribe**: Audio transcription access

### Scope Validation
Automatic scope validation ensures users can only access authorized services:
```python
@Security(validate_api_key, scopes=["chat:base"])
async def chat_completion(...)
```

## Usage Tracking and Logging

### Automatic Usage Logging
All API calls are automatically logged with:
- User identification from API key
- Token consumption (prompt, completion, total)
- Model usage and request metadata
- Timestamps and request IDs

### Usage Data Structure
```python
{
    "user_id": "user123",
    "api_type": "chat",
    "model": "llama-3.3-70b-instruct",
    "prompt_tokens": 20,
    "completion_tokens": 30,
    "total_tokens": 50,
    "request_id": "req_abc123",
    "timestamp": "2025-01-15T10:30:00Z"
}
```

## Error Handling

### HTTP Status Codes
- **200**: Successful request
- **400**: Bad request (invalid parameters)
- **401**: Unauthorized (invalid API key)
- **403**: Forbidden (insufficient scopes)
- **404**: Not found (invalid model)
- **413**: Payload too large (file size limits)
- **429**: Rate limit exceeded
- **500**: Internal server error

### Error Response Format
```json
{
    "error": {
        "code": "invalid_request_error",
        "message": "The model 'invalid-model' does not exist",
        "param": "model",
        "type": "invalid_request_error"
    }
}
```

### Common Error Scenarios
- Invalid model names or unavailable models
- Insufficient API key permissions
- Malformed request bodies or parameters
- File upload size or format restrictions
- Rate limiting and quota exceeded

## Configuration Integration

### Model Configuration
Models are configured through the CONFIG module:
```yaml
models:
  llama-3.3-70b-instruct:
    host: "<llama_host_ip>"
    port: 8001
    type: ["chat:base"]
    response:
      id: "llama-3.3-70b-instruct"
      object: "model"
      owned_by: "<organization-owner>"
```

### Service Configuration
Each service can be configured with:
- Model endpoints and ports
- Supported capabilities and types
- Response metadata and formatting
- Custom arguments and parameters

## Streaming Implementation

### Server-Sent Events (SSE)
Chat completions support real-time streaming using SSE:
```python
return StreamingResponse(
    stream_generator,
    media_type="text/event-stream"
)
```

### Stream Format
```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk",...}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk",...}

data: [DONE]
```

### Stream Handling
- Automatic connection management
- Error handling in streams
- Proper stream termination
- Client disconnection handling

## Integration with Other Modules

### APIKEY Module
- API key validation and user identification
- Scope-based authorization enforcement
- Token extraction from headers

### CONFIG Module
- Model configuration and discovery
- Service endpoint configuration
- Feature flags and settings

### USAGE Module
- Automatic usage logging for all requests
- Token consumption tracking
- User activity monitoring

### Logger Module
- Request and response logging
- Error logging and debugging
- Performance monitoring

## Performance Considerations

### Model Management
- Lazy loading of model configurations
- Efficient model filtering based on scopes
- Caching of model metadata

### Request Processing
- Asynchronous processing for all endpoints
- Streaming support for long-running requests
- Efficient memory usage for large inputs

### File Handling
- Streaming file uploads for audio processing
- Temporary file management and cleanup
- Size and format validation

## Development and Testing

### Request Validation
Comprehensive input validation using Pydantic:
- Type checking and conversion
- Field validation and constraints
- Custom validators for complex logic

### Response Formatting
Consistent response formatting:
- OpenAI API compliance
- Proper error response structure
- Usage information inclusion

### Testing Support
- Model mocking for development
- Request/response validation
- Integration testing capabilities

## Troubleshooting

### Common Issues

**Model Not Found**
- Check model configuration in config.yml
- Verify model is available and running
- Confirm user has appropriate scopes

**Authentication Failures**
- Verify API key format and validity
- Check required scopes for endpoint
- Confirm API key is not expired

**File Upload Issues**
- Check file size limits (25MB for audio)
- Verify supported file formats
- Ensure proper multipart/form-data encoding

**Streaming Problems**
- Check client SSE support
- Verify network connectivity
- Monitor for connection timeouts

### Debug Mode
Enable detailed logging for troubleshooting:
```python
import logging
logging.getLogger("v1").setLevel(logging.DEBUG)
```