import bpy
import bmesh
import sys
import os
import math
import logging
import importlib.util

# Configure test logging
logging.basicConfig(level=logging.INFO, format='TEST_NURBS: %(message)s')
logger = logging.getLogger(__name__)

# Add module path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
script_dir = os.path.join(project_root, 'examples', 'scripts')
sys.path.append(script_dir)

spec = importlib.util.spec_from_file_location("blender_nurbs_barge", os.path.join(script_dir, "blender_nurbs_barge.py"))
module = importlib.util.module_from_spec(spec)
sys.modules["blender_nurbs_barge"] = module
spec.loader.exec_module(module)

def get_bmesh_from_object(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)
    mesh = obj_eval.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    obj_eval.to_mesh_clear()
    return bm

def verify_nurbs_barge():
    logger.info("Starting NURBS Barge Verification...")
    
    # Run Generation
    module.main()
    
    # Get Mesh Object
    obj = bpy.data.objects.get("Barge")
    if not obj:
        logger.error("FAIL: 'Barge' mesh object not found")
        sys.exit(1)
        
    bm = get_bmesh_from_object(obj)
    
    # 1. Dimensions
    bbox_corners = [obj.matrix_world @ getattr(v, "co", v) for v in bm.verts]
    min_x = min(v.x for v in bbox_corners); max_x = max(v.x for v in bbox_corners)
    min_y = min(v.y for v in bbox_corners); max_y = max(v.y for v in bbox_corners)
    min_z = min(v.z for v in bbox_corners); max_z = max(v.z for v in bbox_corners)
    
    L = max_x - min_x
    B = max_y - min_y
    
    logger.info(f"Dimensions: L={L:.2f}, B={B:.2f}")
    
    if not math.isclose(L, 135.0, abs_tol=0.5):
        logger.error(f"FAIL: Length {L} != 135.0")
        sys.exit(1)
    if not math.isclose(B, 14.2, abs_tol=0.2):
        logger.error(f"FAIL: Beam {B} != 14.2")
        sys.exit(1)

    # 2. Container Capacity (Midship Width)
    midship_verts = [v for v in bm.verts if 64.0 < v.co.x < 66.0]
    if midship_verts:
        ys = [v.co.y for v in midship_verts]
        width = max(ys) - min(ys)
        logger.info(f"Midship Width: {width:.2f}")
        if width < 12.2:
            logger.error("FAIL: Midship width < 12.2m (5 TEU)")
            sys.exit(1)
    else:
        logger.warning("WARN: No vertices at midship to measure width.")

    # 3. Cleanup
    try:
        os.remove("barge_nurbs.blend")
        logger.info("Cleanup: 'barge_nurbs.blend' removed.")
    except OSError:
        pass
        
    logger.info("ALL PASSED")

if __name__ == "__main__":
    verify_nurbs_barge()
