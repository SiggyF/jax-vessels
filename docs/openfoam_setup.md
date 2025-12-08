# OpenFOAM Base Case Documentation

> [!IMPORTANT]
> **Docker Requirement**: All OpenFOAM simulations and utilities MUST be run inside the project's Docker container. OpenFOAM is NOT expected to be installed on the host machine.

This document explains the configuration of the `templates/kcs_hull` directory and the workflow for running simulations.

## Workflow

We provide a helper script `scripts/run_docker.sh` to facilitate running commands inside the container.

### 1. Verification
To run verification tests (e.g., `still_water`):
```bash
./scripts/run_docker.sh ./scripts/verify_case.sh still_water
```

### 2. Manual Commands
To run arbitrary OpenFOAM commands:
```bash
./scripts/run_docker.sh blockMesh
```
or enter an interactive shell:
```bash
./scripts/run_docker.sh /bin/bash
```

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
