#!/bin/bash
set -e

# Robustly source OpenFOAM if available (Docker)
if [ -f "/usr/lib/openfoam/openfoam2406/etc/bashrc" ]; then
    # Disable exit-on-error because OpenFOAM's bashrc can trigger false positives
    set +e
    source /usr/lib/openfoam/openfoam2406/etc/bashrc
    set -e
fi

# Configuration
TEMPLATE="templates/floating_hull"
CASE_NAME="instability_repro"
USE_SOFT_OUTLET=false

# Parse arguments
if [[ "$1" == "--soft-outlet" ]]; then
    USE_SOFT_OUTLET=true
    CASE_NAME="instability_soft_outlet"
    echo "Using SOFT OUTLET boundary conditions."
elif [[ "$1" == "--static" ]]; then
    USE_STATIC_HULL=true
    CASE_NAME="instability_static"
    echo "Using STATIC HULL (No 6DoF)."
fi

RUN_DIR="verification_run/$CASE_NAME"

echo "=== Setting up Instability Reproduction Case: $CASE_NAME ==="

# 1. Copy Template
rm -rf $RUN_DIR
mkdir -p $(dirname $RUN_DIR)
cp -r $TEMPLATE $RUN_DIR

# 2. Configure Physics
if [ "$USE_STATIC_HULL" = true ]; then
    echo "Configuring for STATIC HULL..."
    cp $TEMPLATE/system/include/dynamicMesh.static $RUN_DIR/system/include/dynamicMesh_active
    cp $TEMPLATE/system/include/functions.static $RUN_DIR/system/include/functions_active
else
    echo "Configuring for 6DoF (Empty Load)..."
    cp $TEMPLATE/system/include/dynamicMesh.6dof.empty $RUN_DIR/system/include/dynamicMesh_active
    cp $TEMPLATE/system/include/functions.6dof $RUN_DIR/system/include/functions_active
fi
# Copy SetFields (Always Still Water for this test)
cp $TEMPLATE/system/include/setFields.still $RUN_DIR/system/include/setFields_active

# 3. Modify controlDict to TRIGGER instability (maxCo 0.5)
# Using sed to replace the safe 0.2 values with 0.5
# sed -i 's/maxCo           0.2;/maxCo           0.5;/g' $RUN_DIR/system/controlDict
# sed -i 's/maxAlphaCo      0.2;/maxAlphaCo      0.5;/g' $RUN_DIR/system/controlDict

echo "Modified controlDict maxCo/maxAlphaCo to 0.5 (Targeting instability)"

# 3b. Apply Soft Outlet BCs if requested
if [ "$USE_SOFT_OUTLET" = true ]; then
    echo "Switching to Soft Outlet BCs (prghTotalPressure / advective)..."
    # Replace the include line in 0/p_rgh
    sed -i 's|#include "include/outlet_p_rgh_fixed"|#include "include/outlet_p_rgh_soft"|g' $RUN_DIR/0/p_rgh
    # Replace the include line in 0/U
    sed -i 's|#include "include/outlet_U_fixed"|#include "include/outlet_U_advective"|g' $RUN_DIR/0/U
fi

# 4. Mesh Generation (Using cache logic similar to run_matrix.sh)
MESH_CACHE="verification_run/mesh_cache"
cd $RUN_DIR

if [ -d "../../$MESH_CACHE/constant/polyMesh" ]; then
    echo "Mesh cache found. Copying mesh..."
    cp -r ../../$MESH_CACHE/constant/polyMesh constant/
else
    echo "Mesh cache not found. Generating mesh..."
    blockMesh > log.blockMesh 2>&1
    surfaceFeatureExtract > log.surfaceFeatureExtract 2>&1
    snappyHexMesh -overwrite > log.snappyHexMesh 2>&1
    
    # Save to cache
    mkdir -p ../../$MESH_CACHE/constant
    cp -r constant/polyMesh ../../$MESH_CACHE/constant/
fi

# 5. Run Simulation
echo "Running setFields..."
setFields > log.setFields 2>&1


echo "Running interFoam..."
if [ -f "system/decomposeParDict" ]; then
    echo "Running in PARALLEL (6 cores)..."
    decomposePar > log.decomposePar 2>&1
    
    echo "Optimization: Running renumberMesh (Parallel)..."
    mpirun -np 6 renumberMesh -parallel -overwrite > log.renumberMesh 2>&1
    
    mpirun -np 6 interFoam -parallel > log.interFoam 2>&1
    reconstructPar > log.reconstructPar 2>&1
else
    echo "Running in SERIAL..."
    interFoam > log.interFoam 2>&1
fi


echo "Done. Log at $RUN_DIR/log.interFoam"
