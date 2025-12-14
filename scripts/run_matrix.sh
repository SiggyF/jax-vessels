#!/bin/bash
set -e
source /usr/lib/openfoam/openfoam2406/etc/bashrc || true
export LD_LIBRARY_PATH=/usr/lib/openfoam/openfoam2406/platforms/linuxARM64GccDPInt32Opt/lib:$LD_LIBRARY_PATH

# Usage: ./scripts/run_matrix.sh <variant>
# Variants:
#   1. static_still   (No Motion, No Waves)
#   2. static_waves   (No Motion, Dam Break)
#   3. dynamic_still  (6DoF, No Waves)
#   4. dynamic_waves  (6DoF, Dam Break)

VARIANT=$1
TEMPLATE="templates/floating_hull"
RUN_DIR="verification_run/matrix_$VARIANT"

echo "=== Setting up Verification Matrix Case: $VARIANT ==="

# 1. Copy Template
rm -rf $RUN_DIR
mkdir -p $(dirname $RUN_DIR)
cp -r $TEMPLATE $RUN_DIR

# 2. Configure Physics based on Variant
DYNAMIC_DICT="$RUN_DIR/constant/dynamicMeshDict"
SETFIELDS_DICT="$RUN_DIR/system/setFieldsDict"

case $VARIANT in
    static_still)
        echo "Config: Static Mesh, Still Water"
        cp $TEMPLATE/system/include/dynamicMesh.static $RUN_DIR/system/include/dynamicMesh_active
        cp $TEMPLATE/system/include/setFields.still $RUN_DIR/system/include/setFields_active
        cp $TEMPLATE/system/include/functions.static $RUN_DIR/system/include/functions_active
        ;;

    static_waves)
        echo "Config: Static Mesh, Dam Break Waves"
        cp $TEMPLATE/system/include/dynamicMesh.static $RUN_DIR/system/include/dynamicMesh_active
        cp $TEMPLATE/system/include/setFields.waves $RUN_DIR/system/include/setFields_active
        cp $TEMPLATE/system/include/functions.static $RUN_DIR/system/include/functions_active
        ;;

    dynamic_still)
        echo "Config: 6DoF Motion, Still Water"
        cp $TEMPLATE/system/include/dynamicMesh.6dof $RUN_DIR/system/include/dynamicMesh_active
        cp $TEMPLATE/system/include/setFields.still $RUN_DIR/system/include/setFields_active
        cp $TEMPLATE/system/include/functions.6dof $RUN_DIR/system/include/functions_active
        ;;

    dynamic_waves)
        echo "Config: 6DoF Motion, Dam Break Waves (Full)"
        cp $TEMPLATE/system/include/dynamicMesh.6dof $RUN_DIR/system/include/dynamicMesh_active
        cp $TEMPLATE/system/include/setFields.waves $RUN_DIR/system/include/setFields_active
        cp $TEMPLATE/system/include/functions.6dof $RUN_DIR/system/include/functions_active
        ;;
    *)
        echo "Invalid variant: $VARIANT"
        exit 1
        ;;
esac

MESH_CACHE="verification_run/mesh_cache"

# 3. Run Simulation (Wrapper)
cd $RUN_DIR

if [ -d "../../$MESH_CACHE/constant/polyMesh" ]; then
    echo "Mesh cache found. Copying mesh..."
    cp -r ../../$MESH_CACHE/constant/polyMesh constant/
    echo "Mesh copied. Skipping mesh generation."
else
    echo "Mesh cache not found. Generating mesh..."
    blockMesh > log.blockMesh 2>&1

    echo "DEBUG: Checking Environment for surfaceFeatureExtract" > debug_env.txt
    echo "LD_LIBRARY_PATH: $LD_LIBRARY_PATH" >> debug_env.txt
    echo "Path to executable: $(command -v surfaceFeatureExtract)" >> debug_env.txt
    ldd $(command -v surfaceFeatureExtract) >> debug_env.txt 2>&1 || true

    echo "Running surfaceFeatureExtract..."
    surfaceFeatureExtract > log.surfaceFeatureExtract 2>&1

    echo "Running snappyHexMesh..."
    snappyHexMesh -overwrite > log.snappyHexMesh 2>&1
    
    # Save to cache
    echo "Saving mesh to cache..."
    mkdir -p ../../$MESH_CACHE/constant
    cp -r constant/polyMesh ../../$MESH_CACHE/constant/
fi

echo "Running setFields..."
setFields > log.setFields 2>&1

echo "Running interFoam..."
interFoam > log.interFoam 2>&1

echo "Done. Log at $RUN_DIR/log.interFoam"
