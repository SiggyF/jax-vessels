import pyvista as pv
import numpy as np
from pathlib import Path
import sys

def debug_mesh(case_dir):
    case_path = Path(case_dir)
    vtk_dir = case_path / "VTK"
    
    if not vtk_dir.exists():
        print(f"VTK directory not found at {vtk_dir}")
        return

    # Find latest timestep
    time_dirs = sorted([d for d in vtk_dir.iterdir() if d.is_dir()], key=lambda x: float(x.name.split('_')[-1]) if '_' in x.name else -1)
    
    if not time_dirs:
        print("No timestep directories found.")
        return

    latest_dir = time_dirs[-1]
    print(f"Inspecting timestep: {latest_dir.name}")
    
    
    hull_file = latest_dir / "boundary" / "hull.vtp"
    if hull_file.exists():
        hull_mesh = pv.read(hull_file)
        print(f"Hull VTP bounds: {hull_mesh.bounds}")
    else:
        print("Hull VTP file not found.")

    internal_file = latest_dir / "internal.vtu"
    if not internal_file.exists():
        print("internal.vtu not found.")
        return

    mesh = pv.read(internal_file)
    print(f"Mesh bounds: {mesh.bounds}")
    
    # We expect the hull to be around (0,0) and extending downwards.
    # Let's probe a few points that *should* be inside the hull.
    # KVLCC2 is massive, but let's assume standard sizing for now or check bounds.
    # Probing at (0, 0, -2) - assuming draft > 2m
    probe_points = np.array([
        [150, 0, -10],  # Mid-ship, deep inside
        [50, 0, -5],    # Forward section
        [250, 0, -5],   # Aft section
        [150, 30, -5]   # Near hull wall (but outside if beam is 29) - let's check inside: beam is ~29, so y=20 is inside.
    ])
    
    print("\nProbing points (x,y,z) for alpha.water:")
    for pt in probe_points:
        # Find cell containing point
        cell_idx = mesh.find_closest_cell(pt)
        if cell_idx >= 0:
            cell_data = mesh.cell_data
            if "alpha.water" in cell_data:
                val = cell_data["alpha.water"][cell_idx]
                print(f"  Point {pt}: alpha.water = {val:.4f} (Cell ID: {cell_idx})")
            else:
                 print(f"  Point {pt}: Cell found, but 'alpha.water' not in data.")
        else:
             print(f"  Point {pt}: NO MESH CELL FOUND (Correct behavior for solid hull)")

    # Generate a slice at z=-5 to visually confirm
    print("Generating slice at z=-5...")
    if "alpha.water" in mesh.point_data:
        # Interpolate cell data to points for smooth slicing if needed, but cell data on slice works too.
        pass
    
    slice_mesh = mesh.slice(normal='z', origin=(0,0,-5))
    
    pl = pv.Plotter(off_screen=True)
    
    # Plot water (alpha.water > 0.5)
    pl.add_mesh(slice_mesh, scalars="alpha.water", cmap="coolwarm", show_edges=False)
    pl.add_mesh(slice_mesh.contour([0.5], scalars="alpha.water"), color="black", line_width=2)
    
    pl.add_mesh(pv.PolyData(probe_points), color='green', point_size=15, render_points_as_spheres=True)
    pl.view_xy()
    pl.camera.zoom(1.2)
    pl.screenshot("debug_mesh_slice.png")
    print("Saved debug_mesh_slice.png with alpha.water")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_mesh_inside.py <case_dir>")
        sys.exit(1)
    
    debug_mesh(sys.argv[1])
