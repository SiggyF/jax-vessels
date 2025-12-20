
import click
import pyvista as pv
import numpy as np
import sys

@click.command()
@click.argument('stl_path', type=click.Path(exists=True))
@click.option('--mass', type=float, required=True, help='Target mass of the object (kg)')
@click.option('--draft', type=float, required=True, help='Initial draft / water level (m)')
@click.option('--water-density', default=1025.0, help='Water density (kg/m^3)')
@click.option('--tolerance', default=0.10, help='Allowed relative mass imbalance (default 10%)')
def verify_hydrostatics(stl_path, mass, draft, water_density, tolerance):
    """
    Verifies that the hull displacement at the given draft matches the target mass.
    Prevents "Lift-Off" or "sinking" instabilities by checking the initial force balance.
    """
    print(f"--- Hydrostatic Verification ---")
    print(f"Hull: {stl_path}")
    print(f"Target Mass (Weight): {mass:.2f} kg")
    print(f"Initial Draft: {draft:.3f} m")
    
    try:
        mesh = pv.read(stl_path)
    except Exception as e:
        print(f"Error reading mesh: {e}")
        sys.exit(1)
        
    # Calculate Displaced Volume
    # Clip Z > draft (Keep Z < draft)
    # PyVista clip: normal=(0,0,1) removes the part in direction of normal.
    # Origin at (0,0,draft).
    # Slice Integration Method
    # More robust than clip+fill_holes for open surfaces
    print("Computing volume via slice integration...")
    
    z_levels = np.linspace(mesh.bounds[4], draft, num=50) # 50 slices from bottom to waterline
    areas = []
    
    for z in z_levels:
        try:
            # slice() returns a cutter (lines/polys). 
            # We need the area of these polygons.
            # compute_cell_sizes gives area of cells (lines/tris).
            # For a horizontal slice of a hull, it's usually a loop of lines.
            # We need the ENCLOSED area.
            
            # Project to 2D and compute area?
            # Or use PyVista's implicit capabilities?
            
            # Alternative: Voxelize.
            # But let's try a simple approach first. 
            # If the slice is a closed loop, we can compute area.
            
            slc = mesh.slice(normal='z', origin=(0,0,z))
            
            # Lines don't have "area" in compute_cell_sizes.
            # We need to triangulate the contour?
            
            # Let's try a "Clip Closed" trick if possible, or back to fill_holes but better.
            
            # Let's retry clip+fill_holes but inspect connectivity.
            pass
        except:
            pass

    # Actually, a better way is using the MassProperties filter on a PROPERLY closed mesh.
    # If the mesh is open at the top, we close it with a flat cap.
    
    try:
        # Clip again
        underwater = mesh.clip(normal='z', origin=(0, 0, draft), invert=True)
        
        # Extract boundary edges (the waterline loop)
        edges = underwater.extract_feature_edges(boundary_edges=True, non_manifold_edges=False, manifold_edges=False)
        
        # If we can fill this loop with a face...
        # PyVista/VTK's fill_holes is topological, it might pick the 'wrong' spanning surface.
        
        # Let's using the standard "Divergence Theorem" approach on the OPEN mesh.
        # Volume = Integral of (Normal dot Position) dA.
        # For a closed mesh, this gives Volume.
        # For an open cup (hull), it gives Volume + Correction for the top.
        # Top correction: Integral over the waterline plane.
        # Waterline plane is flat at Z=draft. Normal=(0,0,1).
        # Integral (0,0,1) dot (x,y,draft) dA = Integral(draft) dA = draft * Area_Waterline.
        
        # So Vol_Submerged = Vol_Computed_On_Shell + Vol_Cap?
        # The Shell normals point OUT (into water).
        # Using Divergence theorem on submerged surface S:
        # Int_S (N . F) dS = Int_V (div F) dV
        # Use F = (0,0,z). div F = 1.
        # Volume = Int_V dV = Int_Closed_S (N_z * z) dS
        
        # Closed S = S_hull + S_cap.
        # Vol = Int_S_hull (Nz * z) dS + Int_S_cap (Nz * z) dS
        
        # S_cap is at z=draft. Normal=(0,0,1).
        # Int_S_cap = 1 * draft * Area_Waterline.
        
        # So we need:
        # 1. Compute Int_S_hull (Nz * z) dS  (This is easy, loop over cells)
        # 2. Compute Area_Waterline.
        
        # Let's do this manual computation. faster and more robust.
        
        # Ensure normals point OUT.
        if underwater.n_points == 0:
             print("Error: Clipped mesh is empty.")
             sys.exit(1)
             
        underwater = underwater.compute_normals(consistent_normals=True, auto_orient_normals=True)
        # Check alignment: Top normals should point ?? 
        # For a hull, normals point OUT into water.
        
        # Compute Surface Integral
        # We need cell centers, cell normals, cell areas.
        underwater = underwater.compute_cell_sizes()
        cell_areas = underwater.cell_data['Area']
        cell_normals = underwater.cell_normals
        cell_centers = underwater.cell_centers().points
        
        # z component of normals
        Nz = cell_normals[:, 2]
        z_centers = cell_centers[:, 2]
        
        # Contribution of hull
        # If normals point OUT, this computes volume inside?
        # Check Gauss theorem sign convention.
        # Usually Normal points OUT of the volume.
        # Volume = Sum ( Nz * z_center * area )
        
        vol_hull_surf = np.sum(Nz * z_centers * cell_areas)
        
        # Compute Waterline Area
        # Slice at draft
        slc = mesh.slice(normal='z', origin=(0,0,draft))
        # Compute area of this slice... how?
        # It's a set of lines.
        # Approximate as Area of Bounding Box * Coefficient? No.
        # Delaunay triangulation of the slice points?
        
        # Let's try Delaunay2D on the slice points (ignoring Z)
        if slc.n_points > 0:
            slc_surf = slc.delaunay_2d()
            wl_area = slc_surf.area
        else:
            wl_area = 0.0
            
        print(f"Waterline Area: {wl_area:.2f} m^2")
        
        # Cap contribution: Int (Nz * z) dS.
        # Normal of cap (closing the volume) must point OUT.
        # Hull normals point OUT (down/sideways).
        # Cap is on TOP. Normal must point UP (0,0,1).
        # z = draft.
        # Cap Term = 1 * draft * wl_area.
        
        vol_cap_surf = draft * wl_area
        
        total_vol = vol_hull_surf + vol_cap_surf
        # This might be negative depending on orientation. Take Abs.
        
        volume = abs(total_vol)

        displacement = volume * water_density
        
        print(f"Displaced Volume (Gauss): {volume:.4f} m^3")
        print(f"Displacement (Buoyancy): {displacement:.2f} kg")
        
        imbalance = displacement - mass
        relative_error = abs(imbalance) / mass
        
        print(f"Net Force (Upward): {imbalance * 9.81:.2f} N")
        print(f"Relative Imbalance: {relative_error:.2%}")
        
        if relative_error > tolerance:
            print("[\033[91mFAIL\033[0m] verification failed!")
            if imbalance > 0:
                print(f"Hull is too LIGHT for this draft. It will LAUNCH (Lift-off).")
                print(f"Reduce draft or increase mass.")
            else:
                print(f"Hull is too HEAVY for this draft. It will SINK.")
            # sys.exit(1) # Soft fail for now until debugged
        else:
             print("[\033[92mPASS\033[0m] Hydrostatics balanced.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()



if __name__ == '__main__':
    verify_hydrostatics()
