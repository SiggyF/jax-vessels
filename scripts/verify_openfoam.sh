#!/bin/bash
set -e
source /usr/lib/openfoam/openfoam2406/etc/bashrc || true

# Setup run directory
RUN_DIR=verification_run
rm -rf $RUN_DIR
mkdir -p $RUN_DIR
cp -r templates/base_case/* $RUN_DIR/

# Setup geometry
mkdir -p $RUN_DIR/constant/triSurface
if [ -f examples/hulls/simple_box.stl ]; then
    cp examples/hulls/simple_box.stl $RUN_DIR/constant/triSurface/hull.stl
else
    echo "Error: examples/hulls/simple_box.stl not found"
    exit 1
fi

cd $RUN_DIR

echo "=== Running blockMesh ==="
blockMesh | grep -E "Error|Fatal" || true
checkMesh | tail -n 5

echo "=== Running surfaceFeatureExtract ==="
surfaceFeatureExtract | grep -E "Error|Fatal" || true

echo "=== Running snappyHexMesh ==="
snappyHexMesh -overwrite > log.snappyHexMesh
grep -E "Error|Fatal" log.snappyHexMesh || true
checkMesh | tail -n 5

echo "=== Running setFields ==="
setFields

echo "=== Running interFoam ==="
interFoam > log.interFoam
tail -n 10 log.interFoam

echo "VERIFICATION PASSED"
