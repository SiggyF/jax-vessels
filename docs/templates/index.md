# OpenFOAM Simulation Templates

This directory contains the standard OpenFOAM case templates used for verification and production runs.

## Template Hierarchy

The templates are organized by increasing physical complexity. This hierarchy allows for systematic verification of the numerical setup.

| Template | Description | Key Physics | Usage |
| :--- | :--- | :--- | :--- |
| **[still_water](./still_water.md)** | Static box of water and air. | Hydrostatic stability, Phase conservation. | Verification of `interFoam` stability and settings. |
| **[inverse_barometer](./inverse_barometer.md)** | Static box with pressure gradient. | Pressure-Elevation coupling. | Verifying atmospheric pressure handling. |
| **[wave_tank](./wave_tank.md)** | Channel with propagating waves. | Momentum advection, VOF interface capturing. | Verifying wave propagation accuracy. |
| **[kcs_hull](./kcs_hull.md)** | Ship hull in open water. | Fluid-Structure Interaction, Turbulence (`kOmegaSST`). | **production** - The main ship resistance simulation. |
| **- [Physics Verification](verification_matrix.md)
- [Instability Investigation (Issue #14)](../instability_investigation.md)** | Configurable floating hull. | Variable (Static/6DoF, Still/Waves). | Flexible verification of physics components. |

## Usage

These templates are not meant to be run directly in place. They should be copied to a run directory (e.g., `verification_run/` or `analysis_runs/`) to avoid modifying the clean source.

### Running a Verification Test

The project includes a helper script to copy and run a specific case inside the Docker container:

    setFields  # Initializes water/air phases (not needed for kcs_hull if using stl typically, but check specific case)
    # If starting kcs_hull with ship:
    # surfaceFeatureExtract
    # snappyHexMesh -overwrite
```bash
# General syntax
./scripts/run_docker.sh ./scripts/run_matrix.sh --waves <type> --motion <type>

# Example: Run static still water test
./scripts/run_docker.sh ./scripts/run_matrix.sh --waves solitary --motion static
```

### Developing a New Case

1.  Copy the most similar template to a new directory.
2.  Modify the OpenFOAM dictionaries (`system/`, `constant/`).
3.  Test using the docker runner.
