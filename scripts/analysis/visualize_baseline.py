import pyvista as pv
import sys
import os

# Usage: python visualize_baseline.py <case_dir> [time_value]
if len(sys.argv) < 2:
    print("Usage: python visualize_baseline.py <case_dir> [time_value]")
    sys.exit(1)

case_dir = sys.argv[1]
time_val = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
output_file = f"baseline_t{time_val}.png"

print(f"Visualizing {case_dir} at T={time_val}")

# Load Case
reader = pv.POpenFOAMReader(os.path.join(case_dir, "system/controlDict"))
reader.set_active_time_value(time_val)
mesh = reader.read()

# Blocks
internal = mesh["internalMesh"]

# Extract Hull (boundary)
boundary = mesh["boundary"]
hull = None
for patch_name in boundary.keys():
    if "hull" in patch_name.lower():
        hull = boundary[patch_name]
        break

if hull is None:
    print("Warning: Specific 'hull' patch not found. visualizing whole boundary.")
    hull = internal.extract_surface()

# Extract Water Surface (Iso-surface of alpha.water = 0.5)
if "alpha.water" in internal.point_data:
    water = internal.contour(isosurfaces=[0.5], scalars="alpha.water")
else:
    print("Warning: alpha.water not found in internal mesh.")
    water = None

# Plot
plotter = pv.Plotter(off_screen=True)
plotter.add_mesh(hull, color="tan", show_edges=True, opacity=1.0, label="Hull")

if water is not None:
    plotter.add_mesh(water, color="blue", opacity=0.3, label="Water Surface (alpha=0.5)")

plotter.add_axes()
plotter.camera_position = 'xz'
plotter.camera.azimuth = 45
plotter.camera.elevation = 30
plotter.camera.zoom(1.2)

plotter.show(screenshot=output_file)
print(f"Saved to {output_file}")
