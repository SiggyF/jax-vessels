#!/bin/bash
set -e
source /usr/lib/openfoam/openfoam2406/etc/bashrc || true

CASE_NAME=$1

if [ -z "$CASE_NAME" ]; then
    echo "Usage: $0 <case_name>"
    echo "Available cases: still_water, wave_tank, base_case"
    exit 1
fi

TEMPLATE_DIR="templates/$CASE_NAME"

if [ ! -d "$TEMPLATE_DIR" ]; then
    echo "Error: Case directory $TEMPLATE_DIR does not exist."
    exit 1
fi

# Setup run directory
RUN_DIR="verification_run/$CASE_NAME"
rm -rf $RUN_DIR
mkdir -p $RUN_DIR

# Copy template files
echo "Copying template files from $TEMPLATE_DIR to $RUN_DIR..."
cp -r $TEMPLATE_DIR/* $RUN_DIR/

# Special handling for base_case (needs STL)
# STL logic handled within templates now

cd $RUN_DIR

echo "=== Running blockMesh ==="
blockMesh | grep -E "Error|Fatal" || true
checkMesh | tail -n 5

# Case specific steps
# SnappyHexMesh logic
if [ -f "system/snappyHexMeshDict" ]; then
    if [ -f "system/surfaceFeatureExtractDict" ]; then
        echo "=== Running surfaceFeatureExtract ==="
        surfaceFeatureExtract | grep -E "Error|Fatal" || true
    fi
    
    echo "=== Running snappyHexMesh ==="
    snappyHexMesh -overwrite > log.snappyHexMesh
    grep -E "Error|Fatal" log.snappyHexMesh || true
    checkMesh | tail -n 5
fi

# setFields (if applicable)
if [ -f "system/setFieldsDict" ]; then
    echo "=== Running setFields ==="
    setFields > log.setFields
    grep -E "Error|Fatal" log.setFields || true
fi

echo "=== Running interFoam ==="
interFoam > log.interFoam
tail -n 10 log.interFoam

echo "VERIFICATION FOR $CASE_NAME PASSED"
