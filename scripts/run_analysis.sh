#!/bin/bash
# Standard wrapper to initialize OpenFOAM environment and run analysis

# Source OpenFOAM environment
if [ -f /usr/lib/openfoam/openfoam*/etc/bashrc ]; then
    source /usr/lib/openfoam/openfoam*/etc/bashrc
    echo "OpenFOAM environment sourced."
else
    echo "Warning: OpenFOAM environment not found."
fi

# Execute the command passed as arguments in the OpenFOAM environment
exec "$@"
