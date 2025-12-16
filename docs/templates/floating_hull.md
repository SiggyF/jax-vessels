# KCS Hull Simulation

This directory contains the template files for the KCS ship hull hydrodynamics simulation using OpenFOAM.

## Nuances and Specifics

This case represents the most complex tier in our test hierarchy: **Fluid-Structure Interaction with Turbulence**.

### Key Features
*   **Mesh**: Uses `snappyHexMesh` to conform to the `hull.stl` geometry.
*   **Turbulence**: Enables `kOmegaSST` RANS turbulence model.
*   **Forces**: Includes function objects to calculate drag and lift on the hull patches.

### Configuration Details

#### [Mesh](../../templates/floating_hull/system/snappyHexMeshDict) (`system/snappyHexMeshDict`)
*   **Refinement**: Level 3 on the hull surface.
*   **Features**: Explicit edge snapping using `surfaceFeatureExtract` (level 3).
*   **Layers**: Boundary layers are currently **disabled** for robustness in this template, but can be enabled by setting `addLayers` to `true`.

#### [Boundary Conditions](../../templates/floating_hull/0/) (`0/`)
*   **Hull**: `noSlip` for velocity, `zeroGradient` for pressure.
*   **Inlet**: Fixed velocity (body-fixed frame implies water moving past ship).
    *   *Note*: The current inlet BC in `0/alpha.water` sets a uniform 0 (air), which creates a non-physical interface at the inlet below the waterline. This manifests as a sharp drop in water surface elevation near x = -100m.

#### [Solvers](../../templates/floating_hull/system/controlDict) (`system/controlDict`)
*   **PIMPLE**: Configured in PISO mode (`nOuterCorrectors 1`) for speed, assuming small time steps.
*   **Courant Number**: Max Co = 1.0.

For general methodology (VOF, Frame of Reference) and running instructions, please refer to the [project root README](../../README.md).
