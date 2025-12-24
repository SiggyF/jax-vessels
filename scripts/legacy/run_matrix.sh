#!/bin/bash
set -e
# Environment should be loaded by the caller/entrypoint

# Defaults
WAVES="still"       # still, solitary
MOTION="static"     # static, 6dof
LOAD="container"    # container, empty

# Parse Arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --waves) WAVES="$2"; shift ;;
        --motion) MOTION="$2"; shift ;;
        --load) LOAD="$2"; shift ;;
        --help) echo "Usage: $0 [--waves still|solitary] [--motion static|6dof] [--load container|empty]"; exit 0 ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

TEMPLATE="templates/floating_hull"
CASE_NAME="matrix_${MOTION}_${WAVES}_${LOAD}"
RUN_DIR="verification_run/$CASE_NAME"

echo "=== Setting up Verification Case: $CASE_NAME ==="
echo "Configuration: Waves=$WAVES, Motion=$MOTION, Load=$LOAD"

# 1. Copy Template
rm -rf $RUN_DIR
mkdir -p $(dirname $RUN_DIR)
cp -r $TEMPLATE $RUN_DIR

# 2. Configure Physics
DYNAMIC_DICT="$RUN_DIR/constant/dynamicMeshDict"
SETFIELDS_DICT="$RUN_DIR/system/setFieldsDict"
FUNCTIONS_DICT="$RUN_DIR/system/include/functions_active"

# Configure Motion & Load
if [ "$MOTION" == "static" ]; then
    cp $TEMPLATE/system/include/dynamicMesh.static $RUN_DIR/system/include/dynamicMesh_active
    cp $TEMPLATE/system/include/functions.static $RUN_DIR/system/include/functions_active
    echo "  > Motion: Static (No Load configuration needed)"
elif [ "$MOTION" == "6dof" ]; then
    cp $TEMPLATE/system/include/functions.6dof $RUN_DIR/system/include/functions_active
    
    if [ "$LOAD" == "empty" ]; then
        cp $TEMPLATE/system/include/dynamicMesh.6dof.empty $RUN_DIR/system/include/dynamicMesh_active
        echo "  > Motion: 6DoF (Load: Empty, Mass=2.01M)"
    else
        cp $TEMPLATE/system/include/dynamicMesh.6dof.container $RUN_DIR/system/include/dynamicMesh_active
        echo "  > Motion: 6DoF (Load: Container, Mass=2.04M)"
    fi
else
    echo "Error: Invalid motion '$MOTION'"
    exit 1
fi

# Configure Waves
if [ "$WAVES" == "still" ]; then
    cp $TEMPLATE/system/include/setFields.still $RUN_DIR/system/include/setFields_active
    echo "  > Waves: Still Water"
elif [ "$WAVES" == "solitary" ]; then
    cp $TEMPLATE/system/include/setFields.waves $RUN_DIR/system/include/setFields_active
    echo "  > Waves: Solitary (Single Wave)"
else
    echo "Error: Invalid waves '$WAVES'"
    exit 1
fi

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
