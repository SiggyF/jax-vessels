# JAX Vessels

A high-performance optimization and simulation framework for ship hull geometries using JAX and OpenFOAM. This project aims to use differentiable programming to optimize ship efficiency.

## Overview

This repository contains tools for:
1.  **Procedural Hull Generation**: Creating parametric ship geometries (Tankers, Barges) using Python and Blender.
2.  **CFD Integration**: Automated mesh generation and resistance simulation using OpenFOAM.
3.  **Optimization**: Using JAX to learning and minimize resistance surrogates.

## Documentation
*   [OpenFOAM Case Setup](docs/openfoam_setup.md): Explanation of the simulation template.
*   [Test Case Templates](templates/base_case/README.md): Detailed documentation of the available OpenFOAM templates (`still_water`, `inverse_barometer`, `wave_tank`, `base_case`).

## Running Test Cases

The `templates/` directory contains standard OpenFOAM cases. To run a test case (e.g., `wave_tank`):

1.  **Copy the template** to a run directory to keep the original clean:
    ```bash
    cp -r templates/wave_tank simulations/my_wave_test
    cd simulations/my_wave_test
    ```

2.  **Generate Mesh and Fields**:
    ```bash
    blockMesh
    setFields  # Initializes water/air phases (not needed for base_case if using stl typically, but check specific case)
    # If starting base_case with ship:
    # surfaceFeatureExtract
    # snappyHexMesh -overwrite
    ```

3.  **Run Simulation**:
    ```bash
    interFoam
    ```

4.  **Visualize (ParaView)**:
    Convert results to VTK format:
    ```bash
    foamToVTK
    ```
    Open the generated `.vtk` files in the `VTK/` directory using ParaView.
    *   **What to look for**:
        *   **still_water**: Confirm `alpha.water` (phase fraction) is 1.0 at the bottom and 0.0 at the top, and velocity `U` is effectively zero.
        *   **inverse_barometer**: Check that the water level is tilted (lower at inlet where pressure is high, higher at outlet).
        *   **wave_tank**: Observe the `alpha.water` field to see the wave pulse traveling from inlet to outlet over time.
        *   **base_case**: Visualize the Kelvin wake pattern behind the ship hull in `alpha.water` and pressure distribution on the hull.

## Validation

We provide an automated test suite using `pytest` to verify the physical correctness of the templates.

```bash
# Run physics verification tests
pytest tests/test_physics.py
```
This checks for:
*   Hydrostatic stability in `still_water`.
*   Wave propagation causality in `wave_tank`.
*   Positive drag forces in `base_case`.


## Installation
This project uses `uv` for dependency management.

```bash
# Install dependencies
uv sync
```

## Hull Generation

We provide two methods for generating hull geometries:

### 1. Blender Geometry Nodes (Recommended)
Produces high-quality, organic, and simulation-ready meshes using Blender's procedural node system.

```bash
# Generate KVLCC2 Tanker (320m) with Bulbous Bow
blender -b -P examples/scripts/blender_ship_geonodes.py
```

### 2. Python Procedural Script
Fast, standalone generation of basic shapes without Blender dependency.

```bash
# Generate Tanker
python examples/scripts/generate_hull.py --type tanker --out examples/hulls/tanker_kvlcc2_like.stl

# Generate Inland Barge
python examples/scripts/generate_hull.py --type barge --out examples/hulls/barge_inland.stl
```

## Running with Docker
We recommend using Docker to ensure a consistent OpenFOAM environment with all dependencies.

1.  **Build the Image**:
    ```bash
    docker build -t jax-vessels .
    ```

2.  **Run a Simulation**:
    Mount the current directory to `/app` (or whatever the WORKDIR is) to persist outputs.
    ```bash
    docker run --rm -it \
        -v $(pwd):/app \
        jax-vessels \
        run-analysis examples/hulls/simple_box.stl --out-dir analysis_runs
    ```
    *   **Note**: We purposely invoke the `run-analysis` script explicitly.
    *   **Arguments**: Provide the path to one or more STL files.

    This will:
    *   Setup the case.
    *   Run `blockMesh`, `snappyHexMesh`.
    *   Run `interFoam`.
    *   **Automatically run `foamToVTK`** for visualization (output in `analysis_runs/case_.../VTK`).

3.  **Run Tests**:
    ```bash
    docker run --rm -it -v $(pwd):/app --entrypoint pytest jax-vessels tests/
    ```

### Manual Execution in Docker
If you want to run specific OpenFOAM commands manually (debugging):
```bash
# Start a shell with OpenFOAM environment sourced
docker run --rm -it -v $(pwd):/app jax-vessels run-analysis bash
```
Then, inside the container:
```bash
# Example: Run explicit steps on a test case
cd simulations/my_test_case
blockMesh
checkMesh
foamToVTK
```

## Example Hulls

The `examples/hulls/` directory contains generated STL files ready for simulation.

### `tanker_geometry_node.stl`
**Type**: KVLCC2-like VLCC Tanker  
**Dimensions**: 320m x 58m x 30m  
**Features**:
*   **High-Fidelity Bulbous Bow**: Generated via volumetric fusion of an ellipsoidal primitive and the hull body, resulting in a smooth, organic transition.
*   **CFD-Ready Topology**: Remeshed using a uniform Voxel Grid (0.5m) to produce a structured, quad-dominant mesh ideal for `snappyHexMesh`.
*   **Watertight**: Guaranteed manifold geometry due to the volume-to-mesh workflow.

### `tanker_kvlcc2_like.stl`
**Type**: KVLCC2-like Tanker Representation  
**Dimensions**: ~320m length  
**Features**:
*   Generated using pure Python/Numpy mathematical profiles.
*   Explicit mesh construction with a parametric bulbous bow.
*   Good for quick iterate-and-test loops where Blender is not available.

### `barge_inland.stl`
**Type**: CEMT Type IIa Inland Push Barge  
**Dimensions**: 76.5m x 11.4m x 3.5m  
**Features**:
*   Standardized European inland waterway dimensions.
*   Box-shaped midbody with parameterized bow and stern rakes.
*   Suitable for shallow water resistance studies.

### `simple_box.stl`
**Type**: Simple Cuboid  
**Dimensions**: 100m x 20m x 10m (Default)  
**Features**:
*   Pure rectangular geometry ("Shoebox"), ideal for initial verification of the OpenFOAM numerical setup without complex mesh features.
*   Generated via `python examples/scripts/generate_hull.py --type box`.
