#!/bin/bash
set -e

# Usage hint
if [ -z "$1" ]; then
    echo "Usage: ./scripts/utils/check_hydrostatics.sh <path_to_stl> [water_density] [zg]"
    echo "Example: ./scripts/utils/check_hydrostatics.sh templates/kcs_hull/constant/triSurface/hull.stl 1025 0"
    exit 1
fi

STL_FILE=$1
RHO=${2:-1025}
ZG=${3:-0}

# Locate meshmagick via uv
MESHMAGICK_CMD="uv run meshmagick"

echo "Checking hydrostatics for $STL_FILE"
echo "  Density: $RHO kg/m^3"
echo "  Vertical Center of Gravity (Zg): $ZG m"
echo "----------------------------------------"

$MESHMAGICK_CMD "$STL_FILE" -hs -wd "$RHO" -zg "$ZG"
