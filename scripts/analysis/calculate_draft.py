import pyvista as pv
import numpy as np
import sys

def calculate_draft(hull_file, target_mass, rho=1025.0):
    """
    Calculates the required water level (Z) to support the target mass.
    """
    
    mesh = pv.read(hull_file)
    bounds = mesh.bounds
    z_min, z_max = bounds[4], bounds[5]
    
    print(f"Hull Bounds: X[{bounds[0]:.2f}, {bounds[1]:.2f}] Y[{bounds[2]:.2f}, {bounds[3]:.2f}] Z[{z_min:.2f}, {z_max:.2f}]")
    print(f"Target Mass: {target_mass} kg")
    print(f"Fluid Density: {rho} kg/m^3")
    
    target_volume = target_mass / rho
    print(f"Target Displacement Volume: {target_volume:.2f} m^3")
    
    print(f"Target Displacement Volume: {target_volume:.2f} m^3")
    
    # Method: Integration of Waterplane Areas
    # Volume(z) = Integral from z_min to z of Area(z') dz'
    
    # 1. Calculate Area(z) for many z levels
    z_sweep = np.linspace(z_min, z_max, 200)
    areas = []
    
    print("Computing waterplane areas...")
    for z in z_sweep:
        try:
            # slice returns a PolyData of lines
            slc = mesh.slice(normal='z', origin=(0,0,z))
            
            # To get area, we need to triangulate the polygon formed by the slice
            # Filter distinct loops if needed. 
            # Drivable approach: project to 2D, compute polygon area.
            
            # Extract strip/lines
            if slc.n_points < 3:
                areas.append(0.0)
                continue
                
            # PyVista doesn't instantly give area of a loop of lines.
            # We must sort points or use `delaunay_2d`.
            # If the slice is a simple closed loop (barge), delanay_2d works.
            
            # Project to XY (z=0)
            slc_2d = slc.project_points_to_plane(origin=(0,0,z), normal=(0,0,1))
            surf = slc_2d.delaunay_2d()
            areas.append(surf.area)
            
        except Exception:
            areas.append(0.0)
            
    areas = np.array(areas)
    
    # 2. Integrate to get Volume(z)
    # Cumulative Trapezoidal Rule
    volumes = np.zeros_like(areas)
    for i in range(1, len(z_sweep)):
        dz = z_sweep[i] - z_sweep[i-1]
        v_slab = 0.5 * (areas[i] + areas[i-1]) * dz
        volumes[i] = volumes[i-1] + v_slab
        
    # Check max volume
    max_disp = volumes[-1]
    print(f"Max Calculate Displacement: {max_disp:.2f} m^3")
    
    if max_disp < target_volume:
        print(f"Warning: Hull capacity ({max_disp:.2f}) < Target ({target_volume:.2f})")
    
    # Identify Z where volume matches
    # Interpolate using z_sweep and volumes
    idx = np.searchsorted(volumes, target_volume)
    
    if idx == 0:
        print("Error: Target volume smaller than minimum volume.")
        return z_min
    if idx >= len(volumes):
        print("Error: Target volume requires fully submerged or more.")
        return z_max
        
    z_low = z_sweep[idx-1]
    z_high = z_sweep[idx]
    v_low = volumes[idx-1]
    v_high = volumes[idx]
    
    # Linear interpolation
    fraction = (target_volume - v_low) / (v_high - v_low)
    target_z = z_low + fraction * (z_high - z_low)
    
    print(f"---")
    print(f"Calculated Equilibrium Water Level (Draft): Z = {target_z:.4f} m")
    print(f"---")
    return target_z

if __name__ == "__main__":
    # verification_run/matrix_6dof_staged/constant/triSurface/hull.stl
    # or look for .vtp in VTK folder if stl not handy
    # Assuming standard location
    hull_path = "templates/floating_hull/constant/triSurface/hull.stl" 
    if len(sys.argv) > 1:
        hull_path = sys.argv[1]
        
    # Mass from dynamicMeshDict: 2010000 + eventually container
    # Empty hull mass: 2.01e6 kg
    calculate_draft(hull_path, 2010000)
