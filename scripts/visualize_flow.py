
import pyvista as pv
import argparse
import os
import glob

def visualize(case_dir, output_file="docs/showcase_streamlines.png"):
    print(f"Searching for VTK data in: {case_dir}")
    
    # 1. Load the Hull Surface
    # Recursive search for hull files
    boundary_dir = os.path.join(case_dir, "VTK")
    hull_files = sorted(glob.glob(os.path.join(boundary_dir, "**", "hull.vtp"), recursive=True))
    if not hull_files:
        hull_files = sorted(glob.glob(os.path.join(boundary_dir, "**", "hull_*.vtp"), recursive=True))

    if not hull_files:
        print("Error: Could not find hull.vtp files")
        return
    else:
        hull_file = hull_files[-1] # Last timestep
        
    print(f"Loading Hull: {hull_file}")
    hull = pv.read(hull_file)
    
    # 2. Load the Internal Field (Fluid)
    internal_files = sorted(glob.glob(os.path.join(boundary_dir, "**", "internal.vtu"), recursive=True))
    if not internal_files:
        internal_files = sorted(glob.glob(os.path.join(boundary_dir, "**", "internal_*.vtu"), recursive=True))

    if not internal_files:
        print("Error: Could not find internal.vtu files")
        return
    internal_file = internal_files[-1]
    print(f"Loading Internal Field: {internal_file}")
    fluid = pv.read(internal_file)
    
    # 3. Create Streamlines
    # Use U for streamlines
    fluid.set_active_vectors("U")
    
    # Seed a line source in front of the hull
    # User request: depth -2m, width -10 to +10m.
    # We place it slightly upstream of the hull min-x
    b = hull.bounds
    upstream_x = b[0] - 5
    
    streamlines = fluid.streamlines(
        pointa=(upstream_x, -10, -2),
        pointb=(upstream_x, 10, -2),
        n_points=40,
        integration_direction='forward',
        max_time=100.0
    )
    
    # 4. Plotting
    plotter = pv.Plotter(off_screen=True)
    plotter.add_mesh(hull, color="tan", pbr=True, metallic=0.5, smooth_shading=True)
    plotter.add_mesh(streamlines.tube(radius=0.1), scalars="U", cmap="turbo", clim=[0, 3])
    
    # Add water surface (alpha.water = 0.5 contour)
    try:
        # Only show water surface near the hull to avoid clutter
        water_surface = fluid.contour([0.5], scalars="alpha.water")
        plotter.add_mesh(water_surface, color="azure", opacity=0.2, smooth_shading=True)
    except Exception as e:
        print(f"Could not extract water surface: {e}")

    # Camera setup - User requested "Zoom out"
    # Position camera to see the bow and flow
    # Center focus on seed area + some offset
    center = [upstream_x + 20, 0, 0] 
    plotter.camera_position = [
        (upstream_x - 30, -40, 30), # Upstream-Side-Top view
        center,                     # Focus near bow
        (0, 0, 1)                   # Up
    ]
    # No explicit zoom (default is usually fit or 1.0)
    
    print(f"Saving to {output_file}")
    plotter.screenshot(output_file)
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default="verification_run/showcase")
    parser.add_argument("--output", default="docs/showcase_streamlines.png")
    args = parser.parse_args()
    
    visualize(args.case, args.output)
