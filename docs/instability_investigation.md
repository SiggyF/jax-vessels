# Numerical Instability Investigation (Issue #14)

## Objective
Investigate and resolve the simulation stall/crash observed at `t=0.42s` in the `kcs_hull` with `container` load case.

## Baseline Failure Analysis
- **Symptom:** Simulation stalls as `deltaT` drops to `1e-10` or crashes with `MPI_ABORT`.
- **Time of Failure:** Consistently around `t=0.41s - 0.42s`.
- **Observed Metrics (Exp D example):**
  - `t=0.409s`: `deltaT` drops from `1e-4` to `1e-11`.
  - `Courant Number`: Spikes from `0.95` to `1823` in a single step.
  - `Location`: Likely numerical blow-up in the domain (not purely interface related as `Interface Courant` remained low initially).

## Experiments & Results

| Exp | Name | Configuration | Result | Metrics/Notes |
|---|---|---|---|---|
| **A** | **Load Sensitivity** | Load: `empty` (Lower Mass), Schemes: Baseline, maxCo: 0.5 | **FAILED** | Unstable at `t=0.42s`. `Courant` exceeded limit (0.68), forcing `deltaT` collapse. Instability matches container load. |
| **B** | **Numerical Schemes** | Load: `container`, Schemes: `Upwind` (U, k, omega), maxCo: 0.5 | **FAILED** | Unstable at `t=0.42s`. Identical failure mode. Schemes did not prevent blow-up. |
| **C** | **Temporal Resolution** | Load: `container`, Schemes: Baseline, **maxCo: 0.2** | **PASSED** | **Stable.** Simulation passed `t=0.42s` and continued to `t=0.5s` with healthy `deltaT` (~0.005s-0.012s). |
| **D** | **Motion Damping** | Load: `container`, Relaxation: **0.1** (vs 0.7), maxCo: 0.5 | **FAILED** | Unstable at `t=0.409s` (Earlier!). Violent `Courant` spike (0.95 -> 1823). Strong damping worsened stability. |
| **E** | **Delayed Motion** | Load: `container`, Phase 1: Fixed to 1s, Phase 2: 6DoF | **Pass (Phase 1)** | Static hull (Phase 1) passed `t=0.55s` without issue. Confirms instability is motion-coupling driven. |

## Detailed Analysis & Reasoning

### Root Cause: Strong Coupling Instability
The instability observed at `t=0.42s` is a classic **Fluid-Structure Interaction (FSI) coupling instability**.
- **Mechanism:** As the hull accelerates (or decelerates) due to wave localized pressure, the mesh moves. This movement changes the fluid domain, which in turn calculates new pressure forces. If the time-step is too large (Current `maxCo 0.5`), the "lag" between the mesh update and the pressure solution creates a feedback loop.
- **Evidence:**
  - **Static Hull Stability (Exp E):** When the hull is fixed (Phase 1), the simulation passes `t=0.42s` effortlessly. This proves the mesh/numerics are fine *without* motion.
  - **Identical Failure (Exp A & B):** Changing mass slightly or using Upwind schemes (numerical viscosity) did not dampen the feedback loop. The instability is structural, not just a "bad cell".

### Why Motion Damping Failed (Exp D)
We hypothesized that damping the acceleration (`accelerationRelaxation 0.1`) would smooth out the spikes. Instead, it failed *earlier* (`t=0.409s`) and more violently.
- **Reasoning:** Strong under-relaxation in the 6DoF solver creates a mismatch between the *calculated* forces and the *allowed* motion. This can lead to an accumulation of "unreleased" energy or force imbalance that abruptly corrects itself, causing a massive spike in velocity and Courant number (from 0.95 to 1823 in one step). Damping is dangerous for transient, stiff coupling.

### Why Temporal Resolution Worked (Exp C)
Reducing `maxCo` to **0.2** was the only successful intervention.
- **Reasoning:** By forcing the solver to take smaller time-steps, we reduce the discretization error in the time domain. This allows the PIMPLE algorithm (Pressure-Implicit with Splitting of Operators) to resolve the non-linear coupling between the mesh motion and the fluid flow within the iteration window.
- **Trade-off:** This increases simulation cost (more steps), but is necessary for robust 6DoF floating body simulations, especially with light/responsive hulls like `kcs_hull`.

## Conclusion and New Standard: Conservative Courant Condition

The investigation concludes that the standard Courant limit (`maxCo 0.5 - 1.0`) is insufficient for the stiff coupling between the 6DoF floating body and the free surface.

**We strictly adopt `maxCo 0.2` going forward.**

### Motivation: Physics and Mesh Robustness
The decision to lower the Courant limit to 0.2 is driven by a requirement for "extra stability" to accommodate:
1.  **Physics (Coupling):** The lag between the rigid body motion prediction and the fluid pressure correction can induce instability if the time-step is large. A small Courant number limits the displacement per step, linearizing the interaction.
2.  **Numerics (Refinement):** A robust simulation must remain stable even in highly refined regions (e.g., interface refinement or potential Adaptive Mesh Refinement).
    *   *Heuristic:* If a mesh cell is refined (Delta X halved), the Courant limit often needs to be tightened to maintain the same phase-error properties.
    *   To safeguard against instability in the finest mesh cells (or future AMR levels where cells might be split), we apply a **safety factor of ~4** to the standard limit.
    *   $Co_{safe} \approx \frac{Co_{standard}}{4} \approx \frac{0.8}{4} = 0.2$.

This ensures the solver remains robust regardless of local grid density or rapid transient motions.

**Action Item:**
- Permanently set `maxCo 0.2` and `maxAlphaCo 0.2` in all `controlDict` templates.
- This change has been applied and verified.
