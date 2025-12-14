import pyvista as pv
import numpy as np
import click
import logging
from pathlib import Path
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def analyze_velocity(vtk_dir: Path, limit: int):
    """
    Analyze velocity fields in VTK files to locate instability.
    """
    logger.info(f"Searching in {vtk_dir}")
    
    # recursive search for both .vtk and .vtu
    files = sorted(list(vtk_dir.glob("**/*.vtk")) + list(vtk_dir.glob("**/*.vtu")))
    
    if not files:
        logger.warning(f"No VTK/VTU files found in {vtk_dir}")
        return

    count = 0
    for f in files:
        if count >= limit:
            break
        
        try:
            # Simple heuristic to skip non-data files if needed, but pyvista handles most
            mesh = pv.read(f)
            
            # Check for velocity field 'U'
            if "U" in mesh.point_data:
                timestamp = f.parent.name
                logger.info(f"Analyzing {f.name} (Time: {timestamp})...")
                u = mesh.point_data["U"]
                u_mag = np.linalg.norm(u, axis=1)
                
                if "alpha.water" in mesh.point_data:
                    alpha = mesh.point_data["alpha.water"]
                    # Find max U
                    max_idx = np.argmax(u_mag)
                    max_u = u_mag[max_idx]
                    loc = mesh.points[max_idx]
                    alpha_val = alpha[max_idx]
                    
                    logger.info(f"  Global Max U: {max_u:.4f} m/s at {loc}, Alpha: {alpha_val:.2f}")

                    # Find max U in WATER (alpha > 0.5)
                    water_indices = np.where(alpha > 0.5)[0]
                    if len(water_indices) > 0:
                        u_mag_water = u_mag[water_indices]
                        max_idx_water = np.argmax(u_mag_water)
                        max_u_water = u_mag_water[max_idx_water]
                        # map back to global index
                        global_idx_water = water_indices[max_idx_water]
                        loc_water = mesh.points[global_idx_water]
                        logger.info(f"  Max Water U:  {max_u_water:.4f} m/s at {loc_water}")
                    else:
                        logger.info("  No water cells found (alpha > 0.5)")
                else:
                    max_idx = np.argmax(u_mag)
                    max_u = u_mag[max_idx]
                    loc = mesh.points[max_idx]
                    logger.info(f"  Max U: {max_u:.4f} m/s at {loc} (Alpha not found)")
                
                # Check if max velocity is near boundaries
                
                
                # Check if max velocity is near boundaries
                
                # Boundaries: x=-100(inlet), x=400(outlet), y=+-150(sides), z=-100(bottom), z=100(top)
                # These coords are approximate based on template knowledge
                near_inlet = abs(loc[0] - (-100)) < 1.0
                near_hull = (abs(loc[0]) < 100) and (abs(loc[1]) < 20) and (abs(loc[2]) < 10) 
                
                if near_inlet:
                    logger.info("  -> Near INLET boundary")
                elif near_hull:
                    logger.info("  -> Near HULL region")
                else:
                    logger.info("  -> In internal field / other boundary")
                
                count += 1
        except Exception as e:
            logger.error(f"Failed to process {f.name}: {e}")
            continue

def analyze_boundary(vtk_dir: Path, boundary_name: "str", limit: int):
    logger.info(f"Checking boundary: {boundary_name}")
    files = sorted(list(vtk_dir.glob(f"**/boundary/{boundary_name}.vt*")))
    
    count = 0
    for f in files:
        if count >= limit: break
        try:
            mesh = pv.read(f)
            if "U" in mesh.point_data:
                timestamp = f.parent.parent.name # boundary is in VTK/data_XX/boundary/
                u = mesh.point_data["U"]
                u_mag = np.linalg.norm(u, axis=1)
                max_u = np.max(u_mag)
                mean_u = np.mean(u_mag)
                logger.info(f"  {boundary_name} at {timestamp}: Max U = {max_u:.4f} m/s, Mean U = {mean_u:.4f} m/s")
                count += 1
        except Exception as e:
            pass

@click.command()
@click.argument('vtk_dir', type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
@click.option('--limit', default=5, help='Limit number of timesteps to analyze')
def main(vtk_dir: Path, limit: int):
    """
    Analyze velocity fields in VTK files to locate instability.
    """
    # Analyze Internal Field
    analyze_velocity(vtk_dir, limit)
    # Analyze Inlet
    analyze_boundary(vtk_dir, "inlet", limit)

if __name__ == "__main__":
    main()
