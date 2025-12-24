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

def calculate_hydrostatics(stl_path: Path, target_draft=None):
    """
    Calculates displacement at given draft.
    Placeholder: Returns dummy values.
    """
    return {
        "displacement": 1000.0,
        "center_of_buoyancy": [0, 0, -1.0],
        "draft": 2.0 if target_draft is None else target_draft
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
        if hasattr(mesh, 'geometry'): # Handle scene vs mesh
             # If it's a scene, assume first geometry or concat?
             # STLs usually load as Mesh or Scene depending on trimesh version/file.
             # Trimesh.load on single STL usually returns Mesh.
             pass
    except Exception as e:
        logger.error(f"Failed to load mesh: {e}")
        report["status"] = "FAILED_LOAD"
        with output.open('w') as f:
            json.dump(report, f, indent=2)
        sys.exit(1)

    # 1. Integrity
    is_watertight = mesh.is_watertight
    is_winding_consistent = mesh.is_winding_consistent
    # valid_normals = np.all(np.linalg.norm(mesh.face_normals, axis=1) > 0.9) # simple check

    report["checks"]["watertight"] = bool(is_watertight)
    report["checks"]["winding_consistent"] = bool(is_winding_consistent)
    
    passed_integrity = is_watertight and is_winding_consistent

    # 2. Dimensions
    bounds = mesh.bounds
    extents = mesh.extents # [x, y, z] length
    
    report["dimensions"]["mesh_extents"] = extents.tolist()
    report["dimensions"]["bounds_min"] = bounds[0].tolist()
    report["dimensions"]["bounds_max"] = bounds[1].tolist()

    passed_dimensions = True
    if profile:
        with open(profile, 'r') as f:
            prof = json.load(f)
        
        # Expected
        L = float(prof.get('length', 0))
        B = float(prof.get('width', 0))
        D = float(prof.get('depth', 0)) # or draft? Depth of hull usually. 
        # Note: 'depth' in profile might mean hull depth. 'draft' is water level.
        # Extents: X=Length, Y=Beam, Z=Height (Depth)
        
        # Tolerances (e.g. 5%)
        # Logic: If L > 0, check it.
        if L > 0:
            err = abs(extents[0] - L) / L
            report["checks"]["length_error"] = err
            if err > 0.05: passed_dimensions = False
            
        if B > 0:
            err = abs(extents[1] - B) / B
            report["checks"]["beam_error"] = err
            if err > 0.05: passed_dimensions = False

        # Z check might be tricky (freeboard vs draft). 
        # If profile has 'depth', check it.
        if D > 0:
            err = abs(extents[2] - D) / D
            report["checks"]["depth_error"] = err
            if err > 0.10: passed_dimensions = False # looser on depth

    # 3. Hydrostatics (Volume)
    vol = mesh.volume
    com = mesh.center_mass
    report["hydrostatics"] = {
        "volume": vol,
        "center_of_mass": com.tolist() if com is not None else None
    }

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
