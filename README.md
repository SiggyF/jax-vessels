# JAX Vessels

A high-performance optimization and simulation framework for ship hull geometries using JAX and OpenFOAM. This project aims to use differentiable programming to optimize ship efficiency.

## Overview

This repository contains tools for:
1.  **Procedural Hull Generation**: Creating parametric ship geometries (Tankers, Barges) using Python and Blender.
2.  **CFD Integration**: Automated mesh generation and resistance simulation using OpenFOAM.
3.  **Optimization**: Using JAX to learn and minimize resistance surrogates.

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
