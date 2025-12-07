# OpenFOAM Component

## Input Format
- **Geometry**: STL (Stereolithography) format.
    - Naming convention: `hull.stl`
    - Orientation: 
        - X: Longitudinal (Bow positive)
        - Y: Transverse (Port positive)
        - Z: Vertical (Up positive)
        - Origin: Midship, waterline (or keel, to be consistent).
    - Location: `openfoam/constant/triSurface/hull.stl`

## Output Parameters
The simulation pipeline will extract the following parameters for the linear model:
1. **Hydrostatics**:
    - Displacement ($\nabla$)
    - Center of Buoyancy ($LCB, VCB$)
    - Metacentric heights ($GM_T, GM_L$)
2. **Hydrodynamics (Frequency Domain -> Time Domain)**:
    - Added Mass matrix ($M_A$)
    - Damping matrix ($D$)
    - These are usually frequency dependent, but for the linear model we might take zero-frequency or characteristic frequency limits.

## Pipeline Structure
1. **Pre-processing**: `surfaceFeatureExtract`, `blockMesh`, `snappyHexMesh`
2. **Simulation**: `potentialFoam` (for fast estimates) or `interFoam` (for decay tests).
3. **Post-processing**: `forces` function object, custom Python scripts to parse logs.
