#!/bin/bash
set -e

# Source OpenFOAM environment variables
# The path might vary slightly depending on version, glob handles it
if [ -f /usr/lib/openfoam/openfoam*/etc/bashrc ]; then
    source /usr/lib/openfoam/openfoam*/etc/bashrc
else
    echo "Warning: OpenFOAM bashrc not found."
fi

# Run the analysis tool via uv
# "$@" passes all arguments from the docker command
exec uv run openfoam-run "$@"
