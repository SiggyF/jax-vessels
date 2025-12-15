# Simulation Stalls at t=0.42s with Container Load

## Description
The OpenFOAM stability simulation (`matrix_dynamic_still`) stalls at approximately `t=0.42s` when simulating the container load.

## Steps to Reproduce
1. Run the container validation case: `scripts/run_matrix.sh dynamic_still`
2. Observe `log.interFoam` output.
3. Simulation time step decreases rapidly and stalls around `Time = 0.420825`.

## Configuration
- **Mass**: 2.04e6 kg
- **CentreOfMass**: (67.5 0 2.5)
- **Relaxation**: `accelerationRelaxation 0.3`

## Expected Behavior
Simulation should proceed to `t=2.0s` and show stable heave decay.

## Current Behavior
Solver reduces `deltaT` to infinitesimal values to maintain Courant number limits, effectively halting progress. Force oscillation at this point is significant.

## Possible Causes
- PIMPLE solver stability with high mass/inertia changes.
- Mesh deformation limits (check `checkMesh`).
- `maxCo` or `maxAlphaCo` constraints in `system/controlDict`.
