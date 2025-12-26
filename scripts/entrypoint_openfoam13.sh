#!/bin/bash


# Source OpenFOAM environment (handled by BASH_ENV -> /etc/bash.bashrc)
# Source OpenFOAM 13 environment
if [ -f "/opt/openfoam13/etc/bashrc" ]; then
    . "/opt/openfoam13/etc/bashrc"
fi

# Execute the provided command
exec "$@"
