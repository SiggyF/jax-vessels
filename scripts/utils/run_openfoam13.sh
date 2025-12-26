#!/bin/bash
# Wrapper to run commands inside the OpenFOAM 13 (Foundation) Docker container
# Usage: ./run_openfoam13_docker.sh <command>

IMAGE_NAME="jax-vessels:openfoam13" 
# Note: 'graphical' usually includes all tools. If unavailable, we might fail and need to adjust.

# Ensure we are in the project root
cd "$(dirname "$0")/../.." || exit 1
PROJECT_ROOT=$(pwd)

echo "Running in Docker ($IMAGE_NAME)..."

# Run Docker command with volume mounting
# We mount the current directory to /home/openfoam/run (standard for these images)
# We run as the default user 'openfoam' (usually UID 1000) inside.
docker run --rm -it \
    -v "$PROJECT_ROOT":/home/openfoam/run \
    -w /home/openfoam/run \
    "$IMAGE_NAME" \
    "$@"
