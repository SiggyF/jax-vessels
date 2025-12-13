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
        
    # 3. Raycast Inspection for Closure (Top & Bottom & Transom)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    
    # Check Midship (X=50)
    h_up, _, _, _, _, _ = bpy.context.scene.ray_cast(depsgraph, (50, 0, -10), (0,0,1))
    h_dn, _, _, _, _, _ = bpy.context.scene.ray_cast(depsgraph, (50, 0, 10), (0,0,-1))
    
    if not (h_up and h_dn):
        logger.error("FAIL: Hull is not closed at midship X=50.")
        sys.exit(1)
        
    # Check Transom (X=0) from behind (X=-1)
    transom_origin = (-1.0, 0.0, 3.0)
    transom_dir = (1.0, 0.0, 0.0)
    h_transom, _, _, _, _, _ = bpy.context.scene.ray_cast(depsgraph, transom_origin, transom_dir)
    
    if not h_transom:
        logger.error("FAIL: Transom is not closed (Ray from X=-1 missed).")
        sys.exit(1)
        
    logger.info("PASS: Hull is fully closed (Midship & Transom).")
    
    # 4. Shape Quality (Keel Curvature at Stern)
    # Check if bottom is curved at start (X=0 to X=0.1)
    # Raycast UP from -5.0
    def get_keel_z(x):
        h, loc, _, _, _, _ = bpy.context.scene.ray_cast(depsgraph, (x, 0, -5), (0,0,1))
        return loc.z if h else None

    z0 = get_keel_z(0.0)
    z01 = get_keel_z(0.1)
    
    if z0 is not None and z01 is not None:
        diff = z0 - z01
        logger.info(f"Stern Keel Drop (10cm): {diff:.4f}m")
        if diff < 0.001:
             logger.warning("WARN: Stern appears flat (expected curve).")
        else:
             logger.info("PASS: Stern rake has curvature.")
    
    # 5. Cleanup
    try:
        os.remove("barge_nurbs.blend")
        logger.info("Cleanup: 'barge_nurbs.blend' removed.")
    except OSError:
        pass
        
    logger.info("ALL PASSED")

if __name__ == "__main__":
    verify_nurbs_barge()
