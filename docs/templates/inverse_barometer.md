# OpenFOAM Inverse Barometer Test Case

This directory contains the template files for the "Inverse Barometer" verification case.

## Case Description

This case verifies the correct coupling between the pressure boundary condition and the free surface elevation, known as the Inverse Barometer effect.

**Objective:** Verify that the water surface elevation adjusts correctly to a steady atmospheric pressure gradient.
*   **Physics:** High atmospheric pressure should depress the water level; low pressure should raise it. $\Delta \eta = - \frac{\Delta P_{atm}}{\rho g}$.

## Geometry and Mesh

*   **Domain:** Rectangular box, similar to `still_water`.
*   **Mesh:** `blockMesh` generated hex mesh.

## Key Physics

*   **Solver:** `interFoam`.
*   **Boundary Condition:** The top boundary uses a non-uniform `totalPressure` or `prghTotalPressure` (or `codedFixedValue`) to impose a pressure gradient (e.g., linear ramp in X).

## Configuration Details

### [0/](../../templates/inverse_barometer/0/)
*   **`p_rgh`**: At the boundary, configured to represent the varying atmospheric pressure.

## Verification Criteria

1.  **Water Level Sloping**: The final steady-state water surface should slope in opposition to the pressure gradient.
2.  **Magnitude**: The slope should match the analytical prediction.
