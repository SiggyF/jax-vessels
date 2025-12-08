#!/bin/bash
set -e

# Docker image name
IMAGE_NAME="jax-vessels"

# Check if image exists, if not build it
if [[ "$(docker images -q $IMAGE_NAME 2> /dev/null)" == "" ]]; then
    echo "Image $IMAGE_NAME not found. Building..."
    docker build -t $IMAGE_NAME .
fi

# Run the container with the current directory mounted
# We mount to /app because that is the WORKDIR in the Dockerfile
echo "Running in Docker ($IMAGE_NAME)..."
docker run --rm -it \
    -v "$(pwd):/app" \
    -u $(id -u):$(id -g) \
    $IMAGE_NAME \
    "$@"
