#!/bin/bash


# Source OpenFOAM environment
if [ -f "/usr/lib/openfoam/openfoam2406/etc/bashrc" ]; then
    source /usr/lib/openfoam/openfoam2406/etc/bashrc
fi

# Execute the provided command
exec "$@"
