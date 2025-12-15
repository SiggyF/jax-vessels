#!/bin/bash

# Idempotent OpenFOAM environment loader
if [ -z "$FOAM_LOADED" ]; then
    if [ -f "/usr/lib/openfoam/openfoam2406/etc/bashrc" ]; then
        source /usr/lib/openfoam/openfoam2406/etc/bashrc
        export FOAM_LOADED=1
        # echo "OpenFOAM environment loaded."
    else
        echo "Warning: OpenFOAM bashrc not found."
    fi
else
    # echo "OpenFOAM environment already loaded."
    :
fi
