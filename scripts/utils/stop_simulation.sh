#!/bin/bash

# Do not exit on error to ensure we try to kill everything
set +e

echo "Stopping Snakemake workflows..."
# Find and kill snakemake processes (uv run snakemake or python3 ... snakemake)
pids=$(pgrep -f "snakemake")
if [ -n "$pids" ]; then
    echo "Killing Snakemake PIDs: $pids"
    echo "$pids" | xargs kill -9
else
    echo "No Snakemake processes found."
fi

echo "Stopping Python monitors..."
pids=$(pgrep -f "monitor_floating.py")
if [ -n "$pids" ]; then
    echo "Killing Monitor PIDs: $pids"
    echo "$pids" | xargs kill -9
else
    echo "No monitor processes found."
fi

echo "Stopping Docker containers..."
# Get all running container IDs that are using the jax-vessels or jax-vessels-openfoam image
containers=$(docker ps -q --filter ancestor=jax-vessels-openfoam)
if [ -z "$containers" ]; then
    # Fallback/Check for the base name too just in case
    containers=$(docker ps -q --filter ancestor=jax-vessels)
fi
if [ -n "$containers" ]; then
    docker kill $containers
    echo "Stopped containers: $containers"
else
    echo "No jax-vessels containers running."
fi

echo "Cleanup complete."
