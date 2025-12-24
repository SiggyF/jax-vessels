
import pyvista as pv
import argparse
import os
import glob

def visualize(case_dir, output_file="docs/showcase_streamlines.png"):
    print(f"Searching for VTK data in: {case_dir}")
    
    # 1. Load the Hull Surface
    # Recursive search for hull files
    boundary_dir = os.path.join(case_dir, "VTK")
    # 1. Load the Hull (Optional)
    hull_files = sorted(glob.glob(os.path.join(boundary_dir, "**", "boundary", "hull.vtp"), recursive=True))
    hull = None
    if hull_files:
        hull_file = hull_files[-1]
        print(f"Loading Hull: {hull_file}")
        hull = pv.read(hull_file)
    else:
        print("Warning: No hull.vtp found. Proceeding with fluid only.")
    
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
    
    # Seed a line source
    if hull:
        b = hull.bounds
    else:
        b = [-50, 50, -10, 10, -10, 0] # Default bounds for wave tank
    upstream_x = b[0] - 5
    
    streamlines = fluid.streamlines(
        pointa=(upstream_x, -10, -2),
        pointb=(upstream_x, 10, -2),
        n_points=40,
        integration_direction='forward',
        max_time=100.0
    )
    
    # Load Bottom Boundary for Grid Visualization
    bottom_files = sorted(glob.glob(os.path.join(boundary_dir, "**", "boundary", "bottom.vtp"), recursive=True))
    bottom_mesh = None
    if bottom_files:
        bottom_mesh = pv.read(bottom_files[-1])

    # 4. Plotting
    plotter = pv.Plotter(off_screen=True, window_size=[1920, 1080]) # Higher res
    plotter.enable_3_lights() # Better lighting
    if hull:
        plotter.add_mesh(hull, color="grey", show_edges=True)
    
    # Adding lights
    plotter.enable_3_lights()

    # Disable streamlines for wave verification clarity
    # plotter.add_mesh(streamlines, render_lines_as_tubes=True, line_width=5, cmap="viridis", scalar_bar_args={"title": "Velocity Magnitude"})
    
    # Add water surface (alpha.water = 0.5 contour)
    try:
        # Contour at 0.5
        water_surface = fluid.contour([0.5], scalars="alpha.water")
        
        # Color it nicely - SMOOTH (No edges)
        plotter.add_mesh(water_surface, color="dodgerblue", opacity=1.0, 
                        smooth_shading=True, specular=1.0, label="Water Surface")
                        
        # Simple Grid - No bounding box, just axis labels
        # Trying explicit font config
        plotter.show_grid(color='black', font_size=10, 
                         xtitle="X", ytitle="Y", ztitle="Z")
        plotter.add_axes()
        
    except Exception as e:
        print(f"Could not extract water surface: {e}")

    # Camera setup: Angled View with Exaggeration
    # Center roughly at X=50, Y=0, Z=0.
    center = [50, 0, 0] 
    plotter.camera_position = [
        (50, -100, 50),   # Angled view
        center,           # Look at center
        (0, 0, 1)         # Up vector
    ]
    
    # VERTICAL EXAGGERATION to make 1m waves visible in 500m domain
    plotter.set_scale(zscale=10)
    
    print(f"Saving to {output_file}")
    plotter.screenshot(output_file)
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default="verification_run/showcase")
    parser.add_argument("--output", default="docs/showcase_streamlines.png")
    args = parser.parse_args()
    
    visualize(args.case, args.output)
