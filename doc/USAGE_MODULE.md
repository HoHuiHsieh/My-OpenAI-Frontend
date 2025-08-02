# USAGE Module Documentation

## Overview

The USAGE module provides comprehensive usage tracking and analytics for API operations. It logs detailed usage statistics to a PostgreSQL database and offers both user-facing and administrative endpoints for retrieving usage data, token consumption, and cost analysis.

## Features

- **Comprehensive Usage Tracking**: Records token usage, request counts, and metadata
- **PostgreSQL Integration**: Persistent storage with automatic table creation and indexing
- **Multi-API Support**: Tracks usage for chat, embeddings, and audio APIs
- **User and Admin Analytics**: Separate interfaces for users and administrators
- **Time-Based Analytics**: Support for daily, weekly, monthly, and custom time periods
- **Cost Estimation**: Built-in cost calculation based on token usage
- **Dependency Injection**: Clean architecture with testable components
- **Batch Processing**: Efficient database writes with batching support
- **Data Validation**: Comprehensive input validation with Pydantic models

## Module Structure

```
src/usage/
├── __init__.py          # Module initialization and public API
├── models.py            # Pydantic data models and validation
├── manager.py           # UsageManager class for data operations
├── handler.py           # Database logging handler implementation
├── routes.py            # FastAPI endpoints for user and admin access
└── dependencies.py      # Dependency injection utilities
```

## Data Models

### APIType Enum
Supported API types for usage tracking:
```python
class APIType(str, Enum):
    CHAT = "chat"
    EMBEDDINGS = "embeddings"
    AUDIO = "audio"
```

### TimePeriod Enum
Supported time periods for statistics:
```python
class TimePeriod(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    ALL = "all"
```

### TokenUsage Model
Token usage statistics with validation:
```python
class TokenUsage(BaseModel):
    prompt_tokens: int           # Tokens in the input prompt
    completion_tokens: int       # Tokens in the completion (optional)
    total_tokens: int           # Total tokens used
    efficiency_ratio: float     # Completion to prompt token ratio
```

### UsageEntry Model
Individual usage log entry:
```python
class UsageEntry(BaseModel):
    id: Optional[int]                    # Unique identifier
    timestamp: datetime                  # When usage occurred
    api_type: str                       # Type of API used
    user_id: str                        # User who made the request
    model: str                          # Model that was used
    request_id: Optional[str]           # Unique request identifier
    prompt_tokens: int                  # Input tokens
    completion_tokens: Optional[int]    # Output tokens
    total_tokens: int                   # Total tokens
    input_count: Optional[int]          # Number of inputs (embeddings)
    extra_data: Optional[Dict[str, Any]] # Additional metadata
    cost_estimate: float                # Estimated cost
    usage_type: str                     # Usage pattern classification
```

### UsageResponse Model
Response for usage statistics queries:
```python
class UsageResponse(BaseModel):
    time_period: Optional[str]          # Period identifier
    prompt_tokens: int                  # Total prompt tokens
    completion_tokens: int              # Total completion tokens
    total_tokens: int                   # Total tokens used
    request_count: int                  # Number of requests
    model: Optional[str]                # Model name if filtered
    start_date: Optional[datetime]      # Period start
    end_date: Optional[datetime]        # Period end
    user_count: Optional[int]           # Unique users (admin only)
    average_tokens_per_request: float   # Average tokens per request
    completion_ratio: float             # Completion to total ratio
    estimated_cost: float               # Total estimated cost
```

### UsageSummary Model
High-level usage summary:
```python
class UsageSummary(BaseModel):
    total_users: int                    # Total registered users
    active_users_today: int             # Users active today
    requests_today: int                 # Requests made today
    tokens_today: int                   # Tokens used today
    user_activity_ratio: float         # Activity percentage
    avg_tokens_per_request_today: float # Daily average tokens
```

## Database Schema

The module automatically creates a usage table with comprehensive fields:

```sql
CREATE TABLE {prefix}_usage (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    api_type VARCHAR(50) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    model VARCHAR(255) NOT NULL,
    request_id VARCHAR(255),
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    input_count INTEGER,
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### Indexes
Optimized indexes for common queries:
- `idx_{prefix}_usage_timestamp` - Timestamp descending
- `idx_{prefix}_usage_user_id` - User ID lookup
- `idx_{prefix}_usage_api_type` - API type filtering
- `idx_{prefix}_usage_model` - Model filtering
- `idx_{prefix}_usage_composite` - Combined timestamp, user, API type

## Usage Examples

### Basic Usage Logging
```python
from usage import initialize_usage_logger, get_usage_logger

# Initialize the usage logging system
if initialize_usage_logger():
    # Get a logger for chat API
    chat_logger = get_usage_logger("chat")
    
    # Log usage data
    usage_data = {
        "user_id": "user123",
        "model": "llama-3.3-70b-instruct",
        "request_id": "req_abc123",
        "prompt_tokens": 150,
        "completion_tokens": 75,
        "total_tokens": 225,
        "extra_data": {"temperature": 0.7}
    }
    
    chat_logger.log(25, json.dumps(usage_data))  # 25 = USAGE level
```

### Using the UsageManager Directly
```python
from usage.manager import UsageManager
from config import get_config

# Create and initialize manager
config = get_config()
usage_manager = UsageManager(config)
usage_manager.initialize()

# Get usage data for a user
usage_data = usage_manager.get_usage_data(
    user_id="user123",
    time="week",
    period=4,
    model="llama-3.3-70b-instruct"
)

# Get usage summary
summary = usage_manager.get_usage_summary()
print(f"Active users today: {summary.active_users_today}")
```

### Dependency Injection in FastAPI
```python
from fastapi import Depends
from usage.dependencies import get_usage_manager
from usage.manager import UsageManager

@app.get("/my-usage")
async def get_my_usage(
    usage_manager: UsageManager = Depends(get_usage_manager)
):
    # Use the injected usage manager
    data = usage_manager.get_usage_data(user_id="current_user")
    return data
```

## API Endpoints

### User Endpoints

#### GET /usage/{time}
Get usage statistics for the current authenticated user.

**Parameters:**
- `time`: Time period (`day`, `week`, `month`, `all`)
- `period`: Number of periods to retrieve (default: 7)
- `model`: Filter by specific model (default: `all`)

**Response:** List of `UsageResponse` objects

**Example:**
```http
GET /usage/week?period=4&model=llama-3.3-70b-instruct
Authorization: Bearer <token>

Response:
[
    {
        "time_period": "2025-01-20T00:00:00Z",
        "prompt_tokens": 1500,
        "completion_tokens": 750,
        "total_tokens": 2250,
        "request_count": 15,
        "average_tokens_per_request": 150.0,
        "completion_ratio": 0.333,
        "estimated_cost": 0.00225
    }
]
```

### Admin Endpoints

#### GET /admin/usage/user/{username}/{time}
Get usage statistics for a specific user (admin only).

**Parameters:**
- `username`: Target user's username
- `time`: Time period (`day`, `week`, `month`, `all`)
- `period`: Number of periods (default: 7)
- `model`: Filter by model (default: `all`)

**Authentication:** Requires `admin` scope

#### GET /admin/usage/summary
Get overall usage summary (admin only).

**Response:** `UsageSummary` object with system-wide statistics

## Configuration Integration

The USAGE module integrates with the CONFIG module:

### Required Configuration
```yaml
database:
  host: "postgres"
  port: 5432
  username: "postgresql"
  password: "password"
  database: "ai_platform_auth"
  table_prefix: "myopenaiapi"

logging:
  level: "INFO"
  database:
    enabled: true
    retention_days: 365
```

## Advanced Features

### Cost Estimation
Automatic cost calculation based on token usage:
- **Rate**: $0.001 per 1K tokens (configurable)
- **Model-Specific Pricing**: Can be extended for different models
- **Real-time Calculation**: Computed fields in response models

### Usage Pattern Analysis
Automatic classification of usage patterns:
- **input_only**: Embeddings and similar APIs
- **generation_only**: Pure text generation
- **high_generation**: Long completions relative to prompts
- **low_generation**: Short completions
- **balanced**: Normal prompt-to-completion ratio

### Batch Processing
Efficient database operations:
- **Batch Size**: Configurable batch sizes for writes
- **Queue Management**: Non-blocking queues with overflow handling
- **Background Processing**: Dedicated worker threads

### Data Validation
Comprehensive validation with Pydantic:
- **Token Consistency**: Ensures total = prompt + completion tokens
- **Timestamp Validation**: Prevents future timestamps
- **Range Validation**: Non-negative values for counts
- **Type Safety**: Strong typing throughout the system

## Performance Optimization

### Database Indexing
Strategic indexes for common query patterns:
- Time-based queries (timestamp descending)
- User-specific queries (user_id)
- Model filtering queries
- Composite queries combining multiple filters

### Query Optimization
Efficient SQL queries with:
- **Aggregation Functions**: SUM, COUNT, MIN, MAX for statistics
- **Date Functions**: date_trunc for time-based grouping
- **Proper Filtering**: WHERE clauses with indexed columns
- **Result Limiting**: LIMIT clauses for pagination

### Connection Management
Robust database connections:
- **Connection Pooling**: Reuse connections across requests
- **Retry Logic**: Exponential backoff for failed connections
- **Health Checks**: Connection validation before use
- **Automatic Reconnection**: Transparent reconnection on failures

## Monitoring and Analytics

### Usage Metrics
Track key performance indicators:
- **Token Consumption**: Monitor total and per-user usage
- **Request Patterns**: Analyze request frequency and timing
- **Model Popularity**: Track which models are used most
- **Cost Trends**: Monitor spending patterns over time

### System Health
Monitor system performance:
- **Database Performance**: Query execution times
- **Queue Health**: Batch processing metrics
- **Error Rates**: Failed operations and fallbacks
- **Resource Usage**: Memory and connection usage

## Error Handling

### Database Errors
- **Connection Failures**: Automatic retry with exponential backoff
- **Schema Issues**: Automatic table creation and updates
- **Write Failures**: Logging and graceful degradation
- **Query Errors**: Validation and error reporting

### Validation Errors
- **Input Validation**: Comprehensive Pydantic validation
- **Business Logic Validation**: Token consistency checks
- **Type Safety**: Prevention of type-related errors
- **Range Validation**: Ensuring non-negative values

## Integration with Other Modules

### CONFIG Module
- Database connection parameters
- Table prefix configuration
- Logging settings and levels

### OAuth2 Module
- User authentication for endpoints
- User ID extraction for tracking
- Admin permission validation

### APIKEY Module
- Alternative authentication method
- User identification from API keys
- Scope-based access control

### Logger Module
- Shared database configuration
- Consistent logging patterns
- Error reporting and debugging

## Testing

### Unit Testing
```python
from usage.dependencies import create_usage_manager
from config import Config

def test_usage_tracking():
    # Create test manager with test config
    test_config = Config("test_config.yml")
    manager = create_usage_manager(test_config)
    
    # Test usage logging
    logger = manager.get_usage_logger("test_api")
    # ... test logging operations
```

### Integration Testing
```python
from fastapi.testclient import TestClient
from usage.dependencies import UsageManagerFactory

def test_usage_endpoints():
    # Reset singleton for testing
    UsageManagerFactory.reset()
    
    # Test API endpoints
    with TestClient(app) as client:
        response = client.get("/usage/day")
        assert response.status_code == 200
```

## Troubleshooting

### Common Issues

**Database Connection Problems**
- Verify PostgreSQL server is running
- Check database credentials in config.yml
- Confirm database permissions for table creation

**Missing Usage Data**
- Check if usage logging is properly initialized
- Verify log handler configuration
- Monitor for connection errors in system logs

**Performance Issues**
- Adjust batch size and processing intervals
- Monitor database query performance
- Consider connection pool tuning

**Validation Errors**
- Check token count consistency
- Verify timestamp formats
- Ensure non-negative values for counts