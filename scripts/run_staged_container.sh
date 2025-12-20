#!/bin/bash
set -e

# Source Environment
set +e
if [ -f "/usr/local/bin/load-openfoam.sh" ]; then
    source /usr/local/bin/load-openfoam.sh
fi
set -e

CASE_NAME="matrix_6dof_staged"
RUN_DIR="verification_run/$CASE_NAME"
TEMPLATE="templates/floating_hull"

echo "=== Setting up Staged Verification Case: $CASE_NAME ==="

# 1. Setup Base Case
rm -rf $RUN_DIR
mkdir -p $(dirname $RUN_DIR)
cp -r $TEMPLATE $RUN_DIR

# 2. Phase 1: Stability (Empty Load) 0 -> 0.5s
echo "--- Phase 1: Stabilizing (Empty Load) 0 to 0.5s ---"
cp $TEMPLATE/system/include/dynamicMesh.6dof.empty $RUN_DIR/system/include/dynamicMesh_active
cp $TEMPLATE/system/include/functions.6dof $RUN_DIR/system/include/functions_active
cp $TEMPLATE/system/include/setFields.still $RUN_DIR/system/include/setFields_active

# Set endTime to 0.5
sed -i 's/endTime         30.0;/endTime         0.5;/g' $RUN_DIR/system/controlDict

cd $RUN_DIR

# Mesh Generation (Quick)
blockMesh > log.blockMesh 2>&1
surfaceFeatureExtract > log.surfaceFeatureExtract 2>&1
snappyHexMesh -overwrite > log.snappyHexMesh 2>&1
setFields > log.setFields 2>&1

# Run Phase 1
# RenumberMesh for parallel efficiency
decomposePar -force > log.decomposePar 2>&1
mpirun -np 6 renumberMesh -parallel -overwrite > log.renumberMesh 2>&1
mpirun -np 6 interFoam -parallel > log.interFoam_phase1 2>&1
reconstructPar -latestTime > log.reconstructPar_phase1 2>&1

echo "Phase 1 Complete."

# 3. Phase 2: Loading (Container Load) 0.5s -> 2.0s
echo "--- Phase 2: Container Load (0.5s to 2.0s) ---"

# Update Dynamic Mesh Properties (Add Container Mass)
cp ../../$TEMPLATE/system/include/dynamicMesh.6dof.container system/include/dynamicMesh_active

# Update ControlDict: Start from latest, End at 2.0
sed -i 's/startFrom       startTime;/startFrom       latestTime;/g' system/controlDict
sed -i 's/endTime         0.5;/endTime         2.0;/g' system/controlDict

# Resume Simulation
# Append to log.interFoam for continuous monitoring
mpirun -np 6 interFoam -parallel >> log.interFoam_phase2 2>&1
reconstructPar -newTimes >> log.reconstructPar_phase2 2>&1

# Combine logs for monitoring
cat log.interFoam_phase1 log.interFoam_phase2 > log.interFoam

echo "Phase 2 Complete."
echo "Combined log available at $RUN_DIR/log.interFoam"
