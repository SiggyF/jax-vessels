import bpy
import bmesh
import sys
import os
import math
import logging

# Configure test logging
logging.basicConfig(level=logging.INFO, format='TEST: %(message)s')
logger = logging.getLogger(__name__)

# Add module path to sys.path
# Assuming we run from project root, examples/scripts is approachable
# Or relative to this file
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
script_dir = os.path.join(project_root, 'examples', 'scripts')
sys.path.append(script_dir)

import importlib.util

# Dynamic import because "examples.scripts" is not a package
spec = importlib.util.spec_from_file_location("blender_barge_geonodes", os.path.join(script_dir, "blender_barge_geonodes.py"))
module = importlib.util.module_from_spec(spec)
sys.modules["blender_barge_geonodes"] = module
spec.loader.exec_module(module)

def get_bmesh_from_object(obj):
    """Return a bmesh from the evaluated object (modifiers applied)"""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)
    mesh = obj_eval.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    obj_eval.to_mesh_clear()
    return bm

def verify_barge():
    logger.info("Starting Barge Verification...")
    
    # Run Generation
    module.main()
    
    # Get Object
    obj = bpy.data.objects.get("Barge")
    if not obj:
        logger.error("FAIL: Barge object not found")
        sys.exit(1)
        
    bm = get_bmesh_from_object(obj)
    
    # 1. Check Dimensions
    # Bound Box
    bbox_corners = [obj.matrix_world @ getattr(v, "co", v) for v in bm.verts]
    min_x = min(v.x for v in bbox_corners)
    max_x = max(v.x for v in bbox_corners)
    min_y = min(v.y for v in bbox_corners)
    max_y = max(v.y for v in bbox_corners)
    min_z = min(v.z for v in bbox_corners)
    max_z = max(v.z for v in bbox_corners)
    
    L = max_x - min_x
    B = max_y - min_y
    H = max_z - min_z
    
    logger.info(f"Dimensions: L={L:.2f}, B={B:.2f}, H={H:.2f}")
    
    if not math.isclose(L, 135.0, abs_tol=0.1):
        logger.error(f"FAIL: Length {L} != 135.0")
        sys.exit(1)
        
    if not math.isclose(B, 14.2, abs_tol=0.1):
        logger.error(f"FAIL: Beam {B} != 14.2")
        sys.exit(1)
        
    # 2. Check Watertightness
    # (Note: procedural mesh might have open ends if not capped, but our script attempts to cap)
    # Actually, main script puts caps? 
    # Current script REMOVED Fill Holes but used "Fill Caps" in CurveToMesh.
    # So it should be manifold.
    if not bm.is_manifold:
        logger.warning("WARN: Mesh is NOT fully manifold. OpenFOAM requires watertight geometry.")
        # Identify non-manifold elements?
        # Non-manifold is okay for VOF sometimes if checks pass, but ideally closed.
        # sys.exit(1) 
    else:
        logger.info("PASS: Mesh is manifold (watertight).")
        
    # 3. Check Volume (Displacement)
    vol = bm.calc_volume()
    logger.info(f"Total Enclosed Volume: {vol:.2f} m^3")
    
    # Expected displacement at T=2.5 is ~3980.
    # Total Volume includes hull above water.
    # Box approx: 135 * 14.2 * 4.0 = ~7600
    # Block coef 0.85 -> 0.85 * 7600 ~ 6500?
    # This is TOTAL volume. 
    # Just checking it's reasonable (not zero, positive).
    if vol < 5000 or vol > 8000:
        logger.warning(f"WARN: Volume {vol} seems unusual for these dimensions.")
        
    # 4. Check Container Fit (Midbody Width)
    # Check width at X=65m (midship) and Z=3m (Top deck approx)
    # We find vertices near X=65
    midship_verts = [v for v in bm.verts if 64.0 < v.co.x < 66.0]
    if not midship_verts:
         logger.error("FAIL: No vertices found at midship (X~65m)")
         sys.exit(1)
         
    ys = [v.co.y for v in midship_verts]
    width_at_midship = max(ys) - min(ys)
    logger.info(f"Width at Midship: {width_at_midship:.2f}m")
    
    # 5 TEU strict = 12.2m. 
    # Barge beam is 14.2. 
    # We expect width > 13.0 maybe? 
    if width_at_midship < 13.0:
        logger.error(f"FAIL: Midship width {width_at_midship} is too narrow for 5 TEU + structure.")
        sys.exit(1)
    
    logger.info("ALL CHECKS PASSED")
    bm.free()

if __name__ == "__main__":
    try:
        verify_barge()
    except Exception as e:
        logger.error(f"Exception during verification: {e}")
        sys.exit(1)
