# OpenFOAM Base Case Template

This directory contains the template files for the ship hydrodynamics simulation.

- `0/`: Initial boundary conditions (U, p, alpha.water).
- `constant/`: Physical properties and mesh configuration (transportProperties, g, dynamicMeshDict).
- `system/`: Solver control and discretization schemes (controlDict, fvSchemes, fvSolution).

The `openfoam-runner` will copy these files when setting up a new analysis case.
