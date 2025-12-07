# OpenFOAM Base Case Template

This directory contains the template files for the ship hydrodynamics simulation using OpenFOAM.

## Modelling Approach

This simulation aims to model the hydrodynamic performance of a ship hull in a calm sea state using the Volume of Fluid (VOF) method to capture the free surface.

### Real World vs Model Representation

| Real World Element | Model Representation | Description |
|-------------------|----------------------|-------------|
| **Ship Hull** | **STL Surface (`hull.stl`)** | The hull geometry is imported as a triangulated surface. It is treated as a no-slip wall boundary. |
| **Ocean/Air** | **Multiphase Fluid (VOF)** | Two immiscible phases (water and air) are simulated. The interface is captured using the `alpha.water` phase fraction field (0 = air, 1 = water). |
| **Open Sea** | **Computational Domain** | A large rectangular domain surrounds the hull. Boundaries are placed far enough to minimize reflection and influence on the near-hull flow. |
| **Physics** | **RANS + k-Omega SST** | Reynolds-Averaged Navier-Stokes equations are solved. Turbulence is modeled using the k-Omega Shear Stress Transport (SST) model, which handles adverse pressure gradients well. |

### Domain Schematic

The computational domain is a rectangular box defined in `system/blockMeshDict`.

```mermaid
graph TD
    subgraph "Computational Domain Bounds"
    Top[Top (z=100m): Patch]
    Bottom[Bottom (z=-100m): Symmetry/Slip]
    Inlet[Inlet (x=-100m): Patch]
    Outlet[Outlet (x=400m): Patch]
    Left[Side Left (y=-150m): Symmetry]
    Right[Side Right (y=150m): Symmetry]
    end
    Hull[Hull Geometry: Center approx (0,0,0)] --> Domain
```

## Naming Scheme

The configuration files follow standard OpenFOAM naming conventions:

- **Dictionaries**: `camelCase` (e.g., `transportProperties`, `fvSchemes`).
- **Fields**:
  - `U`: Velocity vector.
  - `p_rgh`: Dynamic pressure (p - rho*g*h).
  - `p`: Total pressure.
  - `alpha.water`: Phase fraction (0 = air, 1 = water).
  - `k`: Turbulent kinetic energy.
  - `omega`: Specific turbulence dissipation rate.
- **Parameters**: `camelCase` (e.g., `maxCo`, `adjustTimeStep`).

## Detailed Configuration

The simulation is configured using standard OpenFOAM dictionaries. Below is a detailed description of all schemes, parameters, and quantities.

### 1. Physics Properties (`constant/`)

#### `transportProperties`
Defines the transport model and physical properties for the phases.
- **`phases`**: List of phases, `(water air)`.
- **`water`**:
  - `transportModel`: `Newtonian` (Constant viscosity).
  - `nu` (Kinematic Viscosity): $1 \times 10^{-6} m^2/s$.
  - `rho` (Density): $1025 kg/m^3$.
- **`air`**:
  - `transportModel`: `Newtonian`.
  - `nu` (Kinematic Viscosity): $1.48 \times 10^{-5} m^2/s$.
  - `rho` (Density): $1 kg/m^3$.
- **`sigma`**: Surface tension, $0.07 N/m$.

#### `turbulenceProperties`
- **`simulationType`**: `RAS` (Reynolds-Averaged Simulation).
- **`RAS` dictionary**:
  - `model`: `kOmegaSST`.
  - `turbulence`: `on`.
  - `printCoeffs`: `on` (Print model coefficients to log).

#### `g` (Gravity)
- **`dimensions`**: `[0 1 -2 0 0 0 0]` ($m/s^2$).
- **`value`**: `(0 0 -9.81)` (Standard gravity in negative Z).

### 2. Mesh Generation (`system/`)

#### `blockMeshDict`
- **`scale`**: `1` (Meters).
- **`vertices`**: 8 corners defining the background bounding box from $(-100, -150, -100)$ to $(400, 150, 100)$.
- **`blocks`**: `hex` mesh with $40 \times 20 \times 20$ cells. `simpleGrading (1 1 1)` implies uniform cell size distribution.
- **`boundary`**:
  - `inlet`, `outlet`, `top`: `patch`.
  - `bottom`, `side_left`, `side_right`: `symmetryPlane`.

#### `snappyHexMeshDict`
- **Process control**:
  - `castellatedMesh` (True): Create initial mesh from geometry.
  - `snap` (True): Snap points to surface.
  - `addLayers` (False): Do not add boundary layers (prism cells).
- **`geometry`**:
  - `hull.stl`: Tri-surface mesh input.
  - `refinementBox`: Box for mesh density control.
- **`castellatedMeshControls`**:
  - `maxLocalCells`: 100,000 (Limit per processor).
  - `maxGlobalCells`: 2,000,000 (Total limit).
  - `minRefinementCells`: 10.
  - `maxLoadUnbalance`: 0.10.
  - `nCellsBetweenLevels`: 3 (Buffer layers between refinement levels).
  - `features`: `hull.eMesh` at level 3 (Edge snapping).
  - `refinementSurfaces`: `hull` at level 3.
  - `resolveFeatureAngle`: 30 degrees (Detect edges sharper than this).
  - `refinementRegions`: `refinementBox` mode `inside`, levels `(1.0 2)` (Refine to level 2 inside box).
- **`snapControls`**:
  - `nSmoothPatch`: 3 (Smoothing iterations).
  - `tolerance`: 2.0 (Snap tolerance relative to local cell size).
  - `nSolveIter`: 30 (Displacement solver iterations).
  - `nRelaxIter`: 5.

### 3. Solver Control (`system/controlDict`)

- **`application`**: `interFoam`.
- **`startFrom`**: `startTime` (0).
- **`stopAt`**: `endTime` (0.05 s).
- **`deltaT`**: 0.01 s.
- **`runTimeModifiable`**: `true` (Allow on-the-fly edits).
- **`adjustTimeStep`**: `true`.
- **`maxCo`**: 1.0 (Courant number limit).
- **`maxAlphaCo`**: 1.0 (Alpha Courant limit).
- **`maxDeltaT`**: 1 s.
- **`writeControl`**: `timeStep` (Write every n steps).
- **`writeInterval`**: 1.
- **`writeFormat`**: `ascii`.

### 4. Discretization Schemes (`system/fvSchemes`)

Complete list of numerical schemes used for terms in the equations.

#### `ddtSchemes` (Time derivatives)
- **`default`**: `Euler` (First order implicit, bounded).

#### `gradSchemes` (Gradient terms $\nabla$)
- **`default`**: `Gauss linear` (Second order central).

#### `divSchemes` (Divergence terms $\nabla \cdot$)
- **`default`**: `none` (Forces explicit definition for all terms).
- **`div(rhoPhi,U)`**: `Gauss linearUpwind grad(U)`
  - Convection of velocity.
  - Second order upwind scheme. Discretizes $\nabla \cdot (\rho \phi U)$.
- **`div(phi,alpha)`**: `Gauss vanLeer`
  - Convection of phase fraction.
  - TVD (Total Variation Diminishing) scheme. Standard for VOF to preserve interface sharpness/boundedness.
- **`div(phirb,alpha)`**: `Gauss interfaceCompression`
  - Artificial compression term in VOF equation.
  - Sharpens the interface.
- **`div(((rho*nuEff)*dev2(T(grad(U)))))`**: `Gauss linear`
  - Viscous stress term.
- **`div((muEff*dev2(T(grad(U)))))`**: `Gauss linear`
  - Viscous stress term.
- **`div(phi,k)`**: `Gauss upwind`
  - Convection of $k$ (turbulence kinetic energy). First order for stability.
- **`div(phi,omega)`**: `Gauss upwind`
  - Convection of $\omega$ (turbulence frequency).

#### `laplacianSchemes` (Laplacian terms $\nabla^2$)
- **`default`**: `Gauss linear corrected`
  - Second order central with non-orthogonal correction.

#### `interpolationSchemes` (Cell to face interpolation)
- **`default`**: `linear` (Central difference).

#### `snGradSchemes` (Surface normal gradients)
- **`default`**: `corrected` (Explicit non-orthogonal correction).

#### `fluxRequired`
- Fields requiring flux calculation: `p_rgh`, `pcorr`, `alpha.water`.

#### `wallDist`
- **`method`**: `meshWave` (Calculate distance to wall for turbulence models).

### 5. Linear Solvers (`system/fvSolution`)

#### `solvers`
- **`alpha.water`** (Phase fraction):
  - `nAlphaCorr`: 1 (Corrections per time step).
  - `nAlphaSubCycles`: 2 (VOF sub-cycles within one time step).
  - `cAlpha`: 1 (Compression coefficient, 1 = active compression).
  - `MULESCorr`: `yes`.
  - `nLimiterIter`: 3.
  - `solver`: `smoothSolver`.
  - `smoother`: `symGaussSeidel`.
  - `tolerance`: `1e-8`.
- **`p_rgh`** (Pressure minus Hydrostatic):
  - `solver`: `GAMG` (Geometric-Algebraic Multi-Grid).
  - `smoother`: `GaussSeidel`.
  - `cacheAgglomeration`: `true`.
  - `nCellsInCoarsestLevel`: 10.
  - `agglomerator`: `faceAreaPair`.
  - `mergeLevels`: 1.
  - `tolerance`: `1e-7`.
  - `relTol`: `0.01` (Relative tolerance).
- **`U`** (Velocity):
  - `solver`: `smoothSolver`.
  - `smoother`: `symGaussSeidel`.
  - `tolerance`: `1e-06`.
- **`p_rghFinal`**: Tighter tolerance (`1e-06`) for the final correction loop.
- **`pcorr`**: Correction pressure solvers.

#### `PIMPLE` (Algorithm Control)
- **`momentumPredictor`**: `no` (Skipping the explicit momentum predictor step, common for multiphase to avoid stability issues).
- **`nOuterCorrectors`**: 1 (PISO mode essentially, since outer loop is 1).
- **`nCorrectors`**: 3 (Pressure correctors per time step).
- **`nNonOrthogonalCorrectors`**: 0 (Assume mesh is orthogonal enough).

## Directory Structure

- `0/`: Initial boundary conditions.
- `constant/`: Physical properties and mesh.
- `system/`: Simulation control and schemes.
