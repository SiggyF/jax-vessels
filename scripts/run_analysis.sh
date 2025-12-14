#!/bin/bash
# Standard wrapper to initialize OpenFOAM environment and run analysis

# Source OpenFOAM environment
if [ -f /usr/lib/openfoam/openfoam*/etc/bashrc ]; then
    source /usr/lib/openfoam/openfoam*/etc/bashrc
    echo "OpenFOAM environment sourced."
else
    echo "Warning: OpenFOAM environment not found."
fi

# Source Virtual Environment
if [ -f /app/.venv/bin/activate ]; then
    source /app/.venv/bin/activate
fi

# Execute the command passed as arguments in the OpenFOAM environment
exec "$@"
