import pyvista as pv
import click
from pathlib import Path
import numpy as np
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@click.command()
@click.option("--case", default="verification_run/matrix_dynamic_still", help="Path to the case directory")
@click.option("--output", default="docs/forces.png", help="Path to the output image")
@click.option("--flip/--no-flip", default=False, help="Flip arrow direction")
def visualize_forces(case, output, flip):
    """Visualize the forces on the ship hull."""
    case_dir = Path(case)
    output_file = Path(output)
    
    logger.info(f"Searching for VTK data in: {case_dir}")
    
    # 1. Load the Hull Surface
    boundary_dir = case_dir / "VTK"
    
    # Try finding hull.vtp recursively
    hull_files = sorted(boundary_dir.rglob("hull.vtp"))
    if not hull_files:
        hull_files = sorted(boundary_dir.rglob("hull_*.vtp"))

    if not hull_files:
        logger.error("Could not find hull.vtp files")
        raise FileNotFoundError("Could not find hull.vtp files")
    
    # Create output directory if it doesn't exist
    output_dir = output_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    for hull_file in hull_files:
        # Extract timestamp from filename or path if possible, or just index
        # Assumption: path is .../VTK/matrix_dynamic_still_0.5/boundary/hull.vtp
        # or .../hull_100.vtp
        
        # Try to parse time from parent directory name
        # parent of boundary is matrix_dynamic_still_0.5
        parent_dir_name = hull_file.parent.parent.name
        
        time_str = "unknown"
        if "_" in parent_dir_name:
            try:
                time_str = parent_dir_name.split("_")[-1]
                # Validate if it's a number
                float(time_str)
            except ValueError:
                time_str = str(hull_files.index(hull_file))
        else:
             time_str = str(hull_files.index(hull_file))

        hull = pv.read(hull_file)
        
        # Try to get exact time from field data
        if "TimeValue" in hull.field_data:
            try:
                # TimeValue might be a scalar or array
                t_val = hull.field_data["TimeValue"]
                if hasattr(t_val, '__iter__'):
                    t_val = t_val[0]
                time_str = f"{float(t_val):.2f}"
            except Exception as e:
                logger.warning(f"Could not read TimeValue from {hull_file}: {e}")
        # Else fallback to previous logic (already computed in time_str)

        if hull.points.size == 0:
            logger.warning(f"Empty hull file: {hull_file}")
            continue
        
        # 2. Extract Pressure and Compute Forces
        # Check for pressure field (p or p_rgh)
        pressure_field = None
        if "p" in hull.point_data:
            pressure_field = "p"
        elif "p_rgh" in hull.point_data:
            pressure_field = "p_rgh"
        
        if not pressure_field:
            logger.warning(f"No pressure field found in {hull_file}. Skipping.")
            continue

        # Compute normals
        # consistent_normals=True ensures they point uniformly (usually out)
        hull = hull.compute_normals(cell_normals=True, point_normals=True, consistent_normals=True, non_manifold_traversal=False)
        
        # Compute Force Vectors: F = p * n
        p_data = hull.point_data[pressure_field]
        normals = hull.point_data["Normals"]
        
        # F_vector = p * n
        # If flip is True (or by default if necessary), reverse direction
        direction_mult = -1.0 if flip else 1.0
        forces = normals * p_data[:, None] * direction_mult
        hull.point_data["Force"] = forces
        
        # 3. Plotting
        plotter = pv.Plotter(off_screen=True)
        # Render hull as wireframe to allow seeing arrows if they are inside/on surface
        plotter.add_mesh(hull, color="tan", style="wireframe", opacity=0.5, label="Hull")
        
        # Scaling
        # Calculate Hull Dimensions
        bounds = hull.bounds
        length = bounds[1] - bounds[0]
        width = bounds[3] - bounds[2]
        height = bounds[5] - bounds[4]
        logger.info(f"Hull Dimensions: L={length:.2f}, W={width:.2f}, H={height:.2f}")

        # Scaling Logic
        # User request: "just show the directions with a fixed arrow length"
        # We normalize the force vectors to unit length, then scale by a fixed size (e.g., 5m)
        
        # Calculate magnitudes
        mags = np.linalg.norm(forces, axis=1)
        max_force = np.max(mags)
        avg_force = np.mean(mags)
        
        # Avoid division by zero
        mags_safe = np.where(mags == 0, 1.0, mags)
        
        # Normalize forces to unit vectors
        forces_normalized = forces / mags_safe[:, None]
        
        # Zero out vectors that had zero magnitude originally (if any)
        forces_normalized[mags == 0] = 0
        
        # Set fixed length (e.g., 2% of hull length ~ 2.7m)
        fixed_length = length * 0.02
        forces_display = forces_normalized * fixed_length
        
        # Move arrows slightly off surface to prevent z-fighting/hiding
        # warp by normal * small buffer
        hull_display = hull.warp_by_vector("Normals", factor=0.1) 
        
        # Add data to mesh BEFORE subdivision so it interpolates
        hull_display.point_data["ForceDisplay"] = forces_display

        # Increase density? User request.
        # Subdivide mesh to create more points
        # Must triangulate first if mesh has quads/polys
        hull_display = hull_display.triangulate()
        # User requested factor of 10 increase. Level 1 = x4, Level 2 = x16.
        hull_display = hull_display.subdivide(2, subfilter="linear")
        
        hull_display.set_active_vectors("ForceDisplay")
        # geometric=True helps with sizing. shaft_radius controls thickness.
        # scaling by 'Scalar' requires a scalar array if scale="Scalar", but we verify magnitude manually or use vector mag
        # If scale="Force" (vector), magnitude is used.
        
        # Increase thickness significantly
        arrow_geo = pv.Arrow(shaft_radius=0.03, tip_radius=0.08)
        arrows = hull_display.glyph(geom=arrow_geo, scale="ForceDisplay", orient="ForceDisplay", factor=1.0, tolerance=0.05)
        
        logger.info(f"Generated Arrows: {arrows.n_points} points")

        plotter.add_mesh(arrows, color="hotpink", label="Pressure Direction (Fixed Length)", lighting=True)
        
        # Center of hull bounds
        bounds = hull.bounds # Re-fetch bounds just in case
        cx = (bounds[0] + bounds[1]) / 2
        cy = (bounds[2] + bounds[3]) / 2
        cz = (bounds[4] + bounds[5]) / 2

        # Add Water Surface
        # Create a plane at z=0 using hull bounds to size it
        water_plane = pv.Plane(center=(cx, cy, 0), direction=(0, 0, 1), i_size=length*2.0, j_size=width*10.0)
        plotter.add_mesh(water_plane, color="blue", opacity=0.2, label="Water Surface")

        # Add "Floor" Grid (Wireframe) - Bottom of Domain
        # blockMeshDict: z = -10
        # x: -100 to 400, y: -150 to 150
        domain_x_center = (400 - 100) / 2 # 150
        domain_y_center = 0
        domain_x_len = 500
        domain_y_len = 300
        
        floor_plane = pv.Plane(center=(domain_x_center, domain_y_center, -10), direction=(0, 0, 1), i_size=domain_x_len, j_size=domain_y_len, i_resolution=20, j_resolution=10)
        plotter.add_mesh(floor_plane, color="gray", style="wireframe", opacity=0.3, label="Domain Bottom")

        # Add "Side" Grid (Wireframe) - Side of Domain
        # side_left/right are at y = +/- 150.
        # Let's show the "back" side relative to camera or just one side.
        # Camera is at y ~ -85 (width*6). Side Left is at +150, Side Right at -150.
        # Showing y = 150 (Far side)
        side_plane = pv.Plane(center=(domain_x_center, 150, 45), direction=(0, 1, 0), i_size=domain_x_len, j_size=110, i_resolution=20, j_resolution=5) # z -10 to 100 = 110 height, center at 45
        plotter.add_mesh(side_plane, color="gray", style="wireframe", opacity=0.3, label="Domain Side")

        # Camera setup: Bird's Eye View (from FRONT-SIDE)
        # "View a bit more from the front"
        # Front is +X (L=135). Center is ~67.5.
        # We want to be at X > 135.
        # Position: Forward (+X), Side (-Y), Up (+Z)
        plotter.camera.position = (cx + length*0.8, cy - width*6.0, height*10.0)
        # Position: Forward (towards bow), Wide out, High up
        
        plotter.camera.focal_point = (cx, cy, 0)
        plotter.camera.up = (0, 0, 1) 
        
        plotter.camera.zoom(1.0)
        plotter.enable_eye_dome_lighting()
        plotter.add_title(f"Time: {time_str} s\nMax Force: {max_force:.2e}")
        
        # Derive output filename
        current_output = output_dir / f"{output_file.stem}_{time_str}{output_file.suffix}"
        
        logger.info(f"Saving to {current_output}")
        plotter.screenshot(current_output)
        plotter.close()
    
if __name__ == "__main__":
    visualize_forces()
