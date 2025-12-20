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

echo "=== Resuming Staged Verification Case: $CASE_NAME ==="

cd $RUN_DIR

# Resume Phase 1 (Implicitly uses controlDict which we patched to startFrom latestTime)
echo "--- Resuming Phase 1: Stabilizing (Empty Load) to 0.5s ---"
mpirun -np 6 interFoam -parallel >> log.interFoam_phase1 2>&1
reconstructPar -latestTime >> log.reconstructPar_phase1 2>&1

echo "Phase 1 Complete."

# 3. Phase 2: Loading (Container Load) 0.5s -> 2.0s
echo "--- Phase 2: Container Load (0.5s to 2.0s) ---"

# Check if we already did setup for Phase 2 - probably not if Phase 1 crashed
# Just do it again, it's safe (cp overwrites)

# Update Dynamic Mesh Properties (Add Container Mass)
cp ../../$TEMPLATE/system/include/dynamicMesh.6dof.container system/include/dynamicMesh_active

# Update ControlDict: Start from latest, End at 2.0
sed -i 's/startFrom       latestTime;/startFrom       latestTime;/g' system/controlDict
sed -i 's/endTime         0.5;/endTime         2.0;/g' system/controlDict

# Resume Simulation
# Append to log.interFoam for continuous monitoring
mpirun -np 6 interFoam -parallel >> log.interFoam_phase2 2>&1
reconstructPar -newTimes >> log.reconstructPar_phase2 2>&1

# Combine logs for monitoring
cat log.interFoam_phase1 log.interFoam_phase2 > log.interFoam

echo "Phase 2 Complete."
