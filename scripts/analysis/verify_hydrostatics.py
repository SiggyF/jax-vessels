#!/usr/bin/env python3
import sys
import re
from pathlib import Path
import logging

# Ensure local modules can be imported
sys.path.append(str(Path(__file__).parent))
from calculate_draft import calculate_draft

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_openfoam_value(filepath, key_regex):
    """
    Scans a file for a specific key using regex and returns the first match group.
    """
    path = Path(filepath)
    if not path.exists():
        logger.warning(f"File not found: {path}")
        return None
        
    with open(path, 'r') as f:
        content = f.read()
        
    match = re.search(key_regex, content)
    if match:
        return float(match.group(1))
    return None

def main():
    if len(sys.argv) < 2:
        print("Usage: verify_hydrostatics.py <case_dir> [offset_adjustment_m]")
        sys.exit(1)
        
    case_dir = Path(sys.argv[1])
    offset = float(sys.argv[2]) if len(sys.argv) > 2 else 0.10  # Default +0.10m found empirically
    
    logger.info(f"Verifying hydrostatics for case: {case_dir}")
    logger.info(f"Using empirical offset adjustment: {offset:+.3f} m")
    
    # 1. Get Mass
    # Try dynamicMesh.6dof.empty or active
    dynamic_mesh_path = case_dir / "system/include/dynamicMesh.6dof.empty"
    if not dynamic_mesh_path.exists():
        dynamic_mesh_path = case_dir / "system/include/dynamicMesh_active"
        
    mass = parse_openfoam_value(dynamic_mesh_path, r'mass\s+([0-9\.]+);')
    if mass is None:
        logger.error("Could not determine Mass from dynamicMesh dicts.")
        sys.exit(1)
    logger.info(f"Configuration Mass: {mass} kg")
        
    # 2. Get Configured Water Level (SetFields)
    setfields_path = case_dir / "system/include/setFields.still"
    if not setfields_path.exists():
        setfields_path = case_dir / "system/include/setFields_active"
        
    # box ( ... ... ... ) ( ... ... Z )
    z_set = parse_openfoam_value(setfields_path, r'box\s*\(.*?\)\s*\(.*?([0-9\.\-]+)\s*\);')
    if z_set is None:
        logger.error("Could not determine Water Level from setFields.")
        sys.exit(1)
    logger.info(f"Configured Water Level: {z_set} m")
    
    # 3. Calculate Theoretical Draft
    hull_stl = case_dir / "constant/triSurface/hull.stl"
    if not hull_stl.exists():
        # Try finding it in templates if running from root
        hull_stl = Path("templates/floating_hull/constant/triSurface/hull.stl")
        
    if not hull_stl.exists():
        logger.error("Could not find hull.stl")
        sys.exit(1)
        
    logger.info(f"Calculating required draft for Mass {mass}...")
    z_calc = calculate_draft(str(hull_stl), mass, rho=1025.0)
    
    # 4. Compare
    z_target = z_calc + offset
    diff = abs(z_set - z_target)
    
    logger.info(f"Analytical Draft: {z_calc:.4f} m")
    logger.info(f"Target Draft (with offset): {z_target:.4f} m")
    logger.info(f"Actual Configured Draft: {z_set:.4f} m")
    logger.info(f"Difference: {diff:.4f} m")
    
    if diff > 0.05:
        logger.error(f"FAILURE: Configured draft differs from target by {diff:.4f}m (> 0.05m tolerance).")
        logger.error("The simulation starts too far from equilibrium!")
        sys.exit(1)
    else:
        logger.info("SUCCESS: Hydrostatic configuration is valid.")
        sys.exit(0)

if __name__ == "__main__":
    main()
