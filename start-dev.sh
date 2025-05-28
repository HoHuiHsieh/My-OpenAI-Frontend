#!/bin/bash
export CONTAINER_NAME="my_openai_frontend"

# Build the image
docker build -t my_openai_frontend:latest -f ./docker/Dockerfile . \

# Remove existing container with the same name if it exists
if [ "$(docker ps -aq -f name=^${CONTAINER_NAME}$)" ]; then
    docker rm -f ${CONTAINER_NAME}
fi

# Start the container
docker run -itd --rm \
    --name ${CONTAINER_NAME} \
    -v $PWD:/workspace \
    -w /workspace \
    -p 3000:3000 \
    my_openai_frontend:latest bash
