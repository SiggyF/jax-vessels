# OpenFOAM Base Case Documentation

This document explains the configuration of the `templates/base_case` directory, which serves as the standard template for ship resistance simulations.

## Directory Structure

The case follows the standard OpenFOAM directory structure:

### 1. `0/` (Initial Conditions)
Contains the initial values and boundary conditions for all fields.

-   **`U`** (Velocity):
    -   Initialized to `(10 0 0)` m/s (approx 19.4 knots).
    -   Boundary `inlet`: Fixed value.
    -   Boundary `hull`: `noSlip` (stationary wall) or `movingWallVelocity` (if moving reference frame).
-   **`p_rgh`** (Dynamic Pressure):
    -   Used instead of `p` for VOF solvers to subtract hydrostatic pressure.
    -   Boundary `hull`: `fixedFluxPressure` (standard for buoyancy).
-   **`alpha.water`** (Phase Fraction):
    -   Scalar field (0 = air, 1 = water).
    -   Initialized to 0 (air), usually set later by `setFields`.
-   **Turbulence Fields** (`k`, `omega`, `nut`):
    -   Standard Wall Functions (`kqRWallFunction`, `omegaWallFunction`, `nutkWallFunction`) are applied at the hull to model the boundary layer without resolving it down to $y^+ < 1$.

### 2. `constant/` (Physical Properties & Mesh)
-   **`transportProperties`**: Defines density (`rho`) and viscosity (`nu`) for `water` and `air`.
-   **`turbulenceProperties`**: Sets simulation type to `RAS` (RANS) and model to `kOmegaSST` (standard for marine hydrodynamics).
-   **`g`**: Gravity vector `(0 0 -9.81)`.
-   **`triSurface/`**: Directory where the `hull.stl` will be placed.

### 3. `system/` (Solver & Mesh Control)
#### Meshing
-   **`blockMeshDict`**: Defines the background "Wind Tunnel" domain.
    -   Bounds: `[-100, -150, -100]` to `[400, 150, 100]`.
    -   Generates the base hexahedral mesh.
-   **`surfaceFeatureExtractDict`**: Extracts sharp edges (feature lines) from the STL file. Essential for maintaining the sharp corners of the "Box" hull or the transom of a ship.
-   **`snappyHexMeshDict`**: Controls the body-fitted meshing process.
    -   **CastellatedMesh**: Refines the background grid near the hull (Level 3-4).
    -   **Snap**: Snaps grid points to the STL surface.
    -   **Layers**: (Optional) Adds boundary layer prism cells.

#### Solver
-   **`controlDict`**: Main simulation controller.
    -   Application: `interFoam`.
    -   `timeStep`: Controlled automatically based on `maxCo` (Courant number).
    -   `functions`: Includes a `forces` object to log Lift/Drag (resistance) on the `hull` patch at every time step.
-   **`fvSchemes`**: Numerical schemes. Uses `vanLeer` for phase interface (`alpha`) to keep it sharp.
-   **`fvSolution`**: Linear solvers. `GAMG` (Geometric Multi-Grid) for pressure, `smoothSolver` for velocity.

## Running a Case
The typical workflow orchestrated by `run_simulation_docker.py` is:
1.  **Preparation**: Copy template to run dir, copy STL.
2.  **`blockMesh`**: Create background grid.
3.  **`surfaceFeatureExtract`**: Find hull edges.
4.  **`snappyHexMesh -overwrite`**: Cut the hull out of the background grid.
5.  **`checkMesh`**: Verify mesh quality.
6.  **`topoSet` / `setFields`**: Initialize the water level (Not yet implemented in current template).
7.  **`interFoam`**: Run the simulation.
