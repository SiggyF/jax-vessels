# Hull Geometry Requirements

To ensure successful simulation and mesh generation in JAX Vessels, custom hull geometries must adhere to the following specifications:

## 1. Geometry Topology
*   **Watertight (Manifold)**: The STL mesh must be completely closed with no holes, gaps, or non-manifold edges. `snappyHexMesh` requires a well-defined inside and outside to perform the castellation and snapping process correctly.
    *   *Symptom of failure*: Water appearing inside the hull, "leakage" warnings in logs.
*   **Feature Edges**: Sharp feature edges (e.g., transom stern, bow stem) should be captured clearly. The pipeline extracts features from the STL to snap the mesh to them.

## 2. Coordinate System & Orientation
*   **Orientation**:
    *   **X-axis**: Longitudinal (Bow points to +X, Stern to -X) or vice versa, but flow is typically defined along X. Our templates assume flow in +X direction (inlet at -X), so bow should face -X (into the flow) or be consistent with `blockMesh` setup. *Note: Check specific template for flow direction.*
    *   **Y-axis**: Transverse (Port/Starboard).
    *   **Z-axis**: Vertical (up).
*   **Origin (0,0,0)**:
    *   The origin should be placed at the **Aft Perpendicular (AP)** or **Midships**, and crucially at the **Design Waterline (DWL)** if the simulation assumes z=0 is the water surface.
    *   However, our `kcs_hull` template usually sets the water level `alpha.water` initial condition at specific Z-heights or assumes Z=0.
    *   **Draft**: The hull should be positioned vertically such that the desired draft is submerged.
        *   Example: If water surface is at Z=0 and draft is 20m, the keel should be at Z = -20m.

## 3. File Format
*   **STL (Stereolithography)**: Binary or ASCII STL. `binary` is preferred for file size.
*   **Naming**: The file is usually expected to be named `hull.stl` within the `constant/triSurface` directory.
