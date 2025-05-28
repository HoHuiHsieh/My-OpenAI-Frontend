# My OpenAI Frontend

A proxy server to enhance OpenAI compatible frontend for Triton Inference Server. This project provides an OpenAI API-compatible interface for Triton Inference Server, enhancing it with authentication, logging, usage tracking, and user management capabilities.

> **Note:** This project is currently under construction. Features and documentation are actively being developed.

This is an AI-assisted (GitHub Copilot) development project for learning purposes.

## Features

- **OAuth2-based Authentication and Authorization**: Secure token-based authentication system with role-based access control
- **Fine-grained Role-based Access Control**: Customizable permission scopes for different user roles
- **Enhanced Logging System**: Structured logging with contextual information across console, file, and database outputs
- **Usage Tracking and Statistics**: Comprehensive tracking of API consumption with detailed analytics
- **Admin Interface**: Web-based interface for user management and system monitoring
- **Comprehensive Error Handling**: Robust error handling and detailed error reporting
- **OpenAI API Compatibility**: Seamless integration for applications using OpenAI client libraries
- **Configuration Management**: Flexible configuration through YAML files and environment variables
- **Security Features**: Password security with bcrypt hashing and token revocation capabilities 
- **Triton Inference Server Integration**: Efficient proxy to Triton Inference Server for model inference

## Quick Start

### Prerequisites

#### System Requirements
- **Docker**: Latest stable version
- **Python**: Version 3.10 or higher (for development outside Docker)
- **PostgreSQL**: Version 14 or higher (for user management and usage tracking)
- **Triton Inference Server Setup**: Version 25.03 or higher

#### Required AI Models
1. **Language Model**
   - Llama-3.1 family model deployed on Triton Inference Server
   - Model must support chat completions format
   - Recommended: Llama-3.1-8B-Instruct or similar

2. **Token Counter Model**
   - A dedicated model named 'usage_counter' in Triton Inference Server
   - Purpose: Accurately counts tokens in text for usage tracking
   - Interface:
     - Input: 'prompt' [string] - Text to analyze
     - Output: 'num_tokens' [int] - Number of tokens in the input text
   - Note: This model is dedicated to the Language Model.

3. **Embedding Model** 
   - Any embedding model compatible with Triton Inference Server
   - Recommended: NVIDIA NV-Embed v2 or similar
   - Interface:
     - Inputs: 
       - 'input_text' [string] - Text to embed
       - 'input_type' [string] - Either "query" or "passage"
     - Outputs:
       - 'embeddings' [List[float]] - Vector representation
       - 'prompt_tokens' [int] - Number of tokens processed


### Running in Development Mode

1. Clone this repository:

2. Configure your settings:
   ```bash
   # Copy the example configuration file (if available)
   cp asset/config.example.yml asset/config.yml
   
   # Edit the configuration file to set your preferences
   nano asset/config.yml
   ```
   
   Key configuration options:
   - `models`: Configure model definitions including host, port, and capabilities
     - Define individual model settings for chat, embeddings, and other AI capabilities
     - Customize model response properties and arguments
   - `oauth2`: Set up authentication and authorization
     - Secret keys and token algorithms
     - Token expiration settings
     - Authentication exclusion paths
     - Role-based access control
   - `database`: Configure database connections
     - Connection parameters (host, port, credentials)
     - Database name and SSL settings
   - `logging`: Configure the logging system
     - Log levels (global and component-specific)
     - Console, file, and database logging options
     - Usage tracking and retention policies

3. Start the development environment:
   ```bash
   ./start-dev.sh
   ```
   
   This script builds a Docker image based on Python 3.10, creates a container named "my_openai_frontend", and mounts your local directory to /workspace.

4. Once inside the container, start the application:
   ```bash
   python3 src/main.py
   ```

### Running in Service Mode

To start the service directly:

```bash
./start-serve.sh
```

This script builds the Docker image, creates the container, and automatically starts the application.

### Accessing the Portal

After starting the service, you can access the AI Platform Portal at:

```
http://localhost:3000/share/index.html
```

The portal offers a comprehensive user interface that includes:

- **Login Functionality**: Secure user authentication using OAuth2, allowing users to sign in and access personalized features.
- **Usage Statistics**: Real-time dashboards and detailed analytics to monitor API usage, track consumption, and view historical trends.
- **Bulletin Board System**: An announcement board for important updates, system notifications, and community messages.
- **Admin Panel**: A dedicated interface for administrators to manage users, roles, and monitor system activity logs.

## Documentation

Detailed documentation is available in the `doc` folder:

- [Configuration Guide](doc/CONFIG.md)
- [Logging System](doc/LOGGER.md)
- [OAuth2 Authentication](doc/OAUTH2.md)
- [System Architecture](doc/SYSTEM_CONTEXT_DIAGRAM.md)
- [Usage Statistics](doc/USAGE_STATISTICS.md)
- [V1 API Reference](doc/V1.md)

## References

- [Triton Inference Server](https://github.com/triton-inference-server/server) - The backend inference server used by this project

## About

This project was developed for personal research to explore building a proxy server that enhances Triton Inference Server with additional features while maintaining OpenAI API compatibility.

## Contact

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue)](https://www.linkedin.com/in/hohuihsieh)
