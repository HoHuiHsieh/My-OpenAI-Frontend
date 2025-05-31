#!/bin/bash
# filepath: /workspace/start.sh

# Check if an argument is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 [dev|serve|react-dev|compose-dev]"
    echo "  dev         - Start in development mode (interactive bash shell)"
    echo "  serve       - Start the service (run python3 src/main.py)"
    echo "  react-dev   - Start Next.js development server (React app)"
    echo "  compose-dev - Start all services using docker-compose in dev mode"
    exit 1
fi

export CONTAINER_NAME="my_openai_frontend"


# Start the container based on the argument
case "$1" in
  dev)
    echo "Starting container in development mode..."
    # Build the image
    docker build -t my_openai_frontend:latest -f ./docker/Dockerfile .
    # Remove existing container with the same name if it exists
    if [ "$(docker ps -aq -f name=^${CONTAINER_NAME}$)" ]; then
        docker rm -f ${CONTAINER_NAME}
    fi
    # Run the container in interactive mode with a bash shell
    docker run -itd --rm \
        --name ${CONTAINER_NAME} \
        -v $PWD:/workspace \
        -w /workspace \
        -p 3000:3000 \
        my_openai_frontend:latest bash
    ;;

  react-dev)
    echo "Starting container with Next.js development server..."
    export CONTAINER_NAME="my_openai_frontend-react-dev"
    # Build the image
    docker build -t my_openai_frontend:tsdev -f ./docker/Dockerfile.ts .
    # Remove existing container with the same name if it exists
    if [ "$(docker ps -aq -f name=^${CONTAINER_NAME}$)" ]; then
        docker rm -f ${CONTAINER_NAME}
    fi
    # Run the container in interactive mode with a bash shell for React development
    docker run -itd --rm \
        --name ${CONTAINER_NAME} \
        -v $PWD:/workspace \
        -w /workspace/react-app \
        -p 8080:8080 \
        my_openai_frontend:tsdev bash
    ;;
    
  serve)
    echo "Starting container in service mode..."
    # Build the image
    docker build -t my_openai_frontend:latest -f ./docker/Dockerfile .
    # Remove existing container with the same name if it exists
    if [ "$(docker ps -aq -f name=^${CONTAINER_NAME}$)" ]; then
        docker rm -f ${CONTAINER_NAME}
    fi
    # Run the container to serve the application
    docker run -itd --rm \
        --name ${CONTAINER_NAME} \
        -v $PWD:/workspace \
        -w /workspace \
        -p 3000:3000 \
        my_openai_frontend:latest python3 src/main.py
    ;;

  compose-dev)
    echo "Starting all services using docker-compose in development mode..."
    # Navigate to docker directory and run docker-compose
    docker compose -f docker/docker-compose.yml up -d --build
    echo "All services started with docker-compose in development mode"
    ;;

  *)
    echo "Invalid argument: $1"
    echo "Usage: $0 [dev|serve|react-dev|compose-dev]"
    exit 1
    ;;
esac

echo "Container ${CONTAINER_NAME} started successfully!"
