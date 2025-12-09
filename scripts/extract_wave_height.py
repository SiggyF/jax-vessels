import pyvista as pv
import numpy as np
import argparse
from pathlib import Path

def extract_wave_height(case_dir, output_file=None):
    """
    Extracts the free surface (alpha.water = 0.5) from OpenFOAM VTK output.
    """
    case_path = Path(case_dir)
    vtk_dir = case_path / "VTK"
    
    # Find the latest timestep directories
    time_dirs = sorted([d for d in vtk_dir.iterdir() if d.is_dir()], key=lambda x: extract_time(x.name))
    if not time_dirs:
        print("No timestep directories found.")
        return

    for latest_time_dir in reversed(time_dirs):
        print(f"Processing timestep: {latest_time_dir.name}")
        internal_file = latest_time_dir / "internal.vtu"
        
        if not internal_file.exists():
            continue
            
        try:
            # Load data
            mesh = pv.read(internal_file)
            break
        except Exception as e:
            print(f"Failed to read {internal_file}: {e}")
            continue
    else:
        print("No valid VTK data found.")
        return
    
    # Extract isosurface for alpha.water = 0.5
    if "alpha.water" not in mesh.point_data:
        # Check cell data
        if "alpha.water" in mesh.cell_data:
             mesh = mesh.cell_data_to_point_data()
        else:
             print("alpha.water field not found in mesh data.")
             return

    # Contour
    free_surface = mesh.contour([0.5], scalars="alpha.water")
    
    # Clip to remove boundary artifacts
    # Inlet is at x=-100. We cuts x < -95 to remove the "waterfall" at the inlet.
    # We clip z to +/- 40m to ensure we capture all geometry, even transient splashes.
    free_surface = free_surface.clip_box([-95, 1000, -1000, 1000, -40, 40], invert=False)
    
    # Warping/Elevation - The Z coordinate itself is the wave height
    # Add 'z' as a scalar field for coloring
    z_values = free_surface.points[:, 2]
    free_surface["elevation"] = z_values
    
    z_min, z_max = z_values.min(), z_values.max()
    print(f"Elevation range after clipping: {z_min:.4f} to {z_max:.4f}")
    
    # Use symmetric range for diverging colormap
    # Focus on the relevant wave height (e.g. +/- 5m) to see the wake pattern.
    # Larger transient values will be clamped/saturated.
    clim = [-5, 5]
    
    # Plotting
    plotter = pv.Plotter(off_screen=True)
    plotter.set_background("white")
    plotter.enable_lightkit()
    
    # Add Free Surface
    plotter.add_mesh(free_surface, scalars="elevation", cmap="coolwarm", clim=clim, 
                     show_edges=False, smooth_shading=True, lighting=True,
                     specular=0.5, specular_power=15,
                     scalar_bar_args={"title": "Elevation [m]", "color": "black"})
    
    # Add Ship Hull
    hull_file = latest_time_dir / "boundary" / "hull.vtp"
    if hull_file.exists():
        hull_mesh = pv.read(hull_file)
        print(f"Hull bounds: {hull_mesh.bounds}")
        plotter.add_mesh(hull_mesh, color="silver", smooth_shading=True, lighting=True, specular=0.5)
    else:
        print(f"Warning: Hull file not found at {hull_file}")

    plotter.show_grid(color="black")
    
    # Set camera
    plotter.view_isometric()
    plotter.camera.zoom(1.5) # Reduced zoom slightly to see context if needed

    
    if output_file:
        plotter.screenshot(output_file)
        print(f"Saved visualization to {output_file}")
        
    # Also save the surface as VTP for separate viewing
    vtp_out = case_path / "free_surface.vtk"
    free_surface.save(vtp_out)
    print(f"Saved surface geometry to {vtp_out}")

def extract_time(dirname):
    try:
        # Format usually case_hull_0_TIMESTEPINDEX, but here looks like case_hull_0_26
        # The number is an index, not time value?
        return int(dirname.split('_')[-1])
    except ValueError:
        return -1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract wave height from OpenFOAM simulation")
    parser.add_argument("case_dir", help="Path to the case directory (containing VTK folder)")
    parser.add_argument("--output", "-o", default="wave_height.png", help="Output image path")
    
    args = parser.parse_args()
    extract_wave_height(args.case_dir, args.output)
