#!/bin/bash
# filepath: /workspace/start.sh

# Check if an argument is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 [dev]"
    echo "  dev         - Start all services using docker-compose in dev mode"
    exit 1
fi

export CONTAINER_NAME="my_openai_frontend"


# Start the container based on the argument
case "$1" in
  dev)
    echo "Starting all services using docker-compose in development mode..."
    # Navigate to docker directory and run docker-compose
    docker compose -f docker-compose.dev.yml up -d --build --remove-orphans
    echo "All services started with docker-compose in development mode"
    ;;

  *)
    echo "Error: Invalid argument '$1'"
    echo "Usage: $0 [dev|serve|react-dev|compose-dev]"
    echo "  dev         - Start all services using docker-compose in dev mode"
    exit 1
    ;;
esac

echo "Container ${CONTAINER_NAME} started successfully!"
