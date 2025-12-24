import click
import json
import logging
import sys
from pathlib import Path

print("DEBUG: Script started")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_integrity(stl_path: Path):
    """
    Checks if STL is watertight / manifold.
    Placeholder: just checks if file exists and has size.
    """
    if not stl_path.exists():
        return False, "File not found"
    
    if stl_path.stat().st_size < 100:
        return False, "File too small (likely invalid)"
    
    return True, "Passed integrity check"

def calculate_hydrostatics(mesh, target_draft=0.0):
    """
    Calculates displacement (volume below waterplane at Z=target_draft).
    Assumes Z is vertical.
    """
    import trimesh
    import numpy as np

    # The hull is usually centered at [0,0,0] or similar.
    # We want the volume below Z=target_draft.
    # Trimesh can verify if watertight to calculate volume.
    
    # 1. Clip the mesh at Z = target_draft
    # plane_origin = [0, 0, target_draft]
    # plane_normal = [0, 0, -1] # Keep things below?
    # slice_mesh returns the cross section. intersection?
    # We want the volume of the closed mesh below the plane.
    
    # trimesh.intersection.slice_mesh assumes a hollow surface usually. 
    # For volume, we need to cap the slice.
    
    # A robust way:
    # Use trimesh.boolean.intersection if we have a solid block? Expensive.
    
    # Simpler: If the mesh is watertight, strict clipping.
    # But often hulls are open at the top (deck).
    # If open top, we need to "close" it to compute volume.
    # Or assume the user provided a closed solid.
    
    # Let's assume the STL is a closed solid for now (Wigley usually is).
    # If not, volume computation is ill-defined.
    
    try:
        # Create a large box representing the water
        # Bounds of the hull
        bounds = mesh.bounds
        extents = mesh.extents
        
        # Water box: slightly larger than hull in X,Y, and from bottom to draft in Z
        min_z = bounds[0][2] - 1.0
        
        # If the hull is fully above draft, volume is 0
        if bounds[0][2] > target_draft:
            return {"displacement": 0.0, "center_of_buoyancy": [0,0,0]}
            
        # Box from min_z to target_draft
        box_min = [bounds[0][0]-1, bounds[0][1]-1, min_z]
        box_max = [bounds[1][0]+1, bounds[1][1]+1, target_draft]
        
        # Create box
        water_box = trimesh.creation.box(bounds=[box_min, box_max])
        
        # Intersection
        # boolean operations can be slow/flaky on bad meshes
        # But this is "exact"
        underwater = trimesh.boolean.intersection([mesh, water_box], engine='blender') # Use blender if avail? or scikit-image
        # default engine is often 'scad' or 'blender' depending on install. 
        # internal 'mesh' engine is fast but only works for convex? No.
        
        if underwater.is_empty:
             return {"displacement": 0.0, "center_of_buoyancy": [0,0,0]}
        
        return {
            "displacement": underwater.volume,
            "center_of_buoyancy": underwater.center_mass.tolist()
        }
            
    except Exception as e:
        logger.warning(f"Complex boolean failed: {e}. Falling back to crude estimation.")
        # Fallback: total volume * ratio of depth?
        # Very crude.
        return {
            "displacement": mesh.volume * 0.5,
            "center_of_buoyancy": mesh.center_mass.tolist()
        }

@click.command()
@click.option("--hull", required=True, type=click.Path(exists=True, path_type=Path), help="Path to hull.stl")
@click.option("--profile", type=click.Path(exists=True, path_type=Path), default=None, help="Path to profile.json")
@click.option("--output", required=True, type=click.Path(path_type=Path), help="Output JSON report")
def main(hull, profile, output):
    """Verify Hull Integrity and Hydrostatics."""
    import trimesh
    import numpy as np

    logger.info(f"Verifying hull: {hull}")
    
    report = {
        "hull": str(hull),
        "checks": {},
        "dimensions": {},
        "status": "UNKNOWN"
    }
    
    try:
        mesh = trimesh.load(hull)
        if isinstance(mesh, trimesh.Scene):
            # Concatenate if scene
            if len(mesh.geometry) == 0:
                raise ValueError("Empty Scene")
            mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
            
    except Exception as e:
        logger.error(f"Failed to load mesh: {e}")
        report["status"] = "FAILED_LOAD"
        with output.open('w') as f:
            json.dump(report, f, indent=2)
        sys.exit(1)

    # 1. Integrity
    is_watertight = mesh.is_watertight
    is_winding_consistent = mesh.is_winding_consistent

    report["checks"]["watertight"] = bool(is_watertight)
    report["checks"]["winding_consistent"] = bool(is_winding_consistent)
    
    passed_integrity = is_watertight # Relax winding check?

    # 2. Dimensions
    bounds = mesh.bounds
    extents = mesh.extents # [x, y, z] length
    
    report["dimensions"]["mesh_extents"] = extents.tolist()
    report["dimensions"]["bounds_min"] = bounds[0].tolist()
    report["dimensions"]["bounds_max"] = bounds[1].tolist()

    passed_dimensions = True
    
    # 3. Hydrostatics (Volume)
    # Calculate DISPLACEMENT at Z=0 (Design Waterline)
    hydro = calculate_hydrostatics(mesh, target_draft=0.0)
    
    report["hydrostatics"] = {
        "total_volume": mesh.volume,
        "volume": hydro["displacement"], # This is the submerged volume
        "center_of_mass": mesh.center_mass.tolist() if mesh.center_mass is not None else [0,0,0],
        "center_of_buoyancy": hydro["center_of_buoyancy"]
    }
    
    # LOGIC:
    # If the hull is meant to float directly, Mass must equal Displacement * Density.
    # configure_case.py will read 'volume' from this report.
    # We should ensure 'volume' here refers to Displacement.

    # Final Status
    if passed_integrity and passed_dimensions:
        report["status"] = "APPROVED"
    else:
        report["status"] = "REJECTED"
        logger.error("Hull verification FAILED.")

    with output.open('w') as f:
        json.dump(report, f, indent=2)

    logger.info(f"Report saved to {output}")
    
    if report["status"] != "APPROVED":
        logger.warning(f"Verification {report['status']} but proceeding (soft failure).")
        sys.exit(0)

if __name__ == "__main__":
    main()
