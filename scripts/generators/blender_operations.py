import bpy
import bmesh
import math
import argparse
import sys
import os
import logging

# Configure logging to stderr so it doesn't pollute stdout (if we digest it)
# But Blender spews to stdout usually.
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def clean_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    # Purge orphan data
    for block in bpy.data.meshes:
        if block.users == 0: bpy.data.meshes.remove(block)

def export_stl(filepath, selection_only=True):
    # Ensure directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    if hasattr(bpy.ops.wm, "stl_export"):
        bpy.ops.wm.stl_export(filepath=filepath, export_selected_objects=selection_only)
    elif hasattr(bpy.ops.export_mesh, "stl"):
        bpy.ops.export_mesh.stl(filepath=filepath, use_selection=selection_only)
    else:
        logger.error("No STL exporter found!")

# -----------------------------------------------------------------------------
# TASK: Create Bulb (from blender_ship_gen.py)
# -----------------------------------------------------------------------------
def task_create_bulb(args):
    clean_scene()
    
    # Parameters (could come from args/json)
    L = 0.0 # Origin relative to hull? Or place at 0,0,0
    
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=32, ring_count=16, 
        radius=1.0, 
        location=(0,0,0) # Centered
    )
    bulb = bpy.context.active_object
    bulb.name = "Bulb"
    
    # Scale to be ellipsoidal
    bulb.scale = (9.0, 3.5, 6.0) # Radius scale
    
    # Smooth
    bpy.ops.object.shade_smooth()
    
    logger.info(f"Created Bulb. Exporting to {args.output}")
    export_stl(args.output)

# -----------------------------------------------------------------------------
# TASK: Create Propeller (Simple Placeholder)
# -----------------------------------------------------------------------------
def task_create_propeller(args):
    clean_scene()
    
    # Hub
    bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=2.0, location=(0,0,0), rotation=(0, 1.57, 0))
    hub = bpy.context.active_object
    hub.name = "Hub"
    
    # Blade 1
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 1.5, 0))
    blade = bpy.context.active_object
    blade.scale = (0.2, 1.5, 0.5)
    blade.rotation_euler = (0.5, 0, 0) # Pitch
    
    # Array modifier for 4 blades? Or just duplicate.
    # Simple join for now
    
    # Ensure selection for join (Active=Hub, Selected=Hub+Blade)
    bpy.ops.object.select_all(action='DESELECT')
    hub.select_set(True)
    blade.select_set(True)
    bpy.context.view_layer.objects.active = hub
    
    bpy.ops.object.join()
    
    logger.info(f"Created Propeller. Exporting to {args.output}")
    export_stl(args.output)

# -----------------------------------------------------------------------------
# TASK: Create Barge Hull (from blender_nurbs_barge.py)
# -----------------------------------------------------------------------------
def task_create_barge(args):
    clean_scene()
    
    # ... (cherry-picked logic from blender_nurbs_barge.py) ...
    # Simplified for brevity in this artifact, reusing the core ops.
    bpy.ops.surface.primitive_nurbs_surface_surface_add(radius=1, location=(0,0,0))
    obj = bpy.context.active_object
    obj.name = "Barge_Hull"
    
    # Subdivide
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.curve.select_all(action='SELECT')
    bpy.ops.curve.subdivide(number_cuts=2)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Hardcoded shaping for the simple case (Barge Simple)
    # Ideally we apply the point manipulation logic here.
    obj.scale = (25.0, 5.0, 2.0) # Approx 50m x 10m x 4m
    
    # Convert to Mesh
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)
    mesh = bpy.data.meshes.new_from_object(obj_eval)
    new_obj = bpy.data.objects.new("Barge_Mesh", mesh)
    bpy.context.collection.objects.link(new_obj)
    
    # Cleanup NURBS
    bpy.data.objects.remove(obj)
    
    bpy.context.view_layer.objects.active = new_obj
    new_obj.select_set(True)
    
    # Fill holes
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.fill_holes(sides=0)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    logger.info(f"Created Barge. Exporting to {args.output}")
    export_stl(args.output)

# -----------------------------------------------------------------------------
# TASK: Wigley Hull
# -----------------------------------------------------------------------------
def task_create_wigley(args):
    """Generates a Wigley hull mesh."""
    # Wigley hull equation: y = +/-(B/2) * (1 - (2x/L)^2) * (1 - (z/T)^2)
    
    L = 100.0 
    B = 10.0
    T = 6.25
    D_freeboard = T * 0.2
    
    mesh = bpy.data.meshes.new(name="WigleyMesh")
    obj = bpy.data.objects.new("Wigley", mesh)
    bpy.context.collection.objects.link(obj)
    
    nx = 50
    nz = 20
    
    full_verts = []
    # Port side (y>=0)
    rows_p = []
    for i in range(nx + 1):
        x = -L/2 + (L * i / nx)
        row_indices = []
        for j in range(nz + 1):
            z = -T + ((T + D_freeboard) * j / nz)
            
            if z < 0:
                 y = (B/2) * (1 - (2*x/L)**2) * (1 - (z/T)**2)
            else:
                 y = (B/2) * (1 - (2*x/L)**2)
            
            if y < 0: y = 0
            
            full_verts.append((x, y, z))
            row_indices.append(len(full_verts) - 1)
        rows_p.append(row_indices)

    # Starboard side (y -> -y) (Mirror y)
    rows_s = []
    for i in range(nx + 1):
        x = -L/2 + (L * i / nx)
        row_indices = []
        for j in range(nz + 1):
            z = -T + ((T + D_freeboard) * j / nz)
            
            if z < 0:
                 y = -(B/2) * (1 - (2*x/L)**2) * (1 - (z/T)**2)
            else:
                 y = -(B/2) * (1 - (2*x/L)**2)
            
            if abs(y) < 1e-6: y = 0
            
            full_verts.append((x, y, z))
            row_indices.append(len(full_verts) - 1)
        rows_s.append(row_indices)
        
    faces = []
    # Side faces
    for side_rows in [rows_p, rows_s]:
        is_port = (side_rows is rows_p)
        for i in range(nx):
            for j in range(nz):
                v1 = side_rows[i][j]
                v2 = side_rows[i+1][j]
                v3 = side_rows[i+1][j+1]
                v4 = side_rows[i][j+1]
                
                if is_port:
                     # Port (+Y): Want normal +Y. v1->v2 is +X, v2->v3 is +Z. Cross (+X, +Z) = -Y (In).
                     # So reverse: v4->v3->v2->v1.
                     faces.append((v4, v3, v2, v1))
                else:
                     # Starboard (-Y): Want normal -Y. 
                     # Previous v4->v3->v2->v1 gave +Y (In).
                     # So use v1->v2->v3->v4.
                     faces.append((v1, v2, v3, v4))

    # Deck (connect top row)
    top_p = [rows_p[i][-1] for i in range(nx+1)]
    top_s = [rows_s[i][-1] for i in range(nx+1)]
    
    for i in range(nx):
        faces.append((top_p[i], top_s[i], top_s[i+1], top_p[i+1]))
        
    mesh.from_pydata(full_verts, [], faces)
    mesh.update()
    
    # Recalculate normals
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    # Remove duplicates (weld centerline)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.001)
    
    # Recalculate normals
    # bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    logger.info(f"Created Wigley Hull. Exporting to {args.output}")
    export_stl(args.output)

# -----------------------------------------------------------------------------
# TASK: Assemble (Boolean Union) (from blender_ship_gen.py)
# -----------------------------------------------------------------------------
def task_assemble(args):
    clean_scene()
    
    # Imports
    parts = []
    if args.bow and os.path.exists(args.bow):
        bpy.ops.import_mesh.stl(filepath=args.bow)
        parts.append(bpy.context.selected_objects[0])
        parts[-1].name = "Bow_Part"
        # Position: Move Bow to front? Logic needed.
        # Assuming components are generated relative to 0 or we place them here.
        # Barge length ~50. Bow at 25?
        parts[-1].location = (25.0, 0, 0)

    if args.engine and os.path.exists(args.engine):
        bpy.ops.import_mesh.stl(filepath=args.engine)
        parts.append(bpy.context.selected_objects[0])
        parts[-1].name = "Engine_Part"
        parts[-1].location = (-25.0, 0, 0)

    # Note: If we have a "Main Hull" component, import it too.
    # Currently assemble_hull calls this. Where is the "main hull"?
    # The "Profile" generated it? Or "Barge" task generated the whole thing?
    # If "Barge" task generated full hull, we don't need assembly or just skipping.
    
    # Let's assume for KCS we have: MainHull + Bow + Engine.
    # But for Barge we just have: BargeHull.
    # If inputs are provided, we union them.
    
    combined = parts[0]
    for part in parts[1:]:
        mod = combined.modifiers.new(name="Union", type='BOOLEAN')
        mod.object = part
        mod.operation = 'UNION'
        try:
             bpy.ops.object.modifier_apply(modifier="Union")
        except:
             # Fallback if context is wrong (sometimes happens in headless)
             ctx = bpy.context.copy()
             ctx['object'] = combined
             ctx['active_object'] = combined
             bpy.ops.object.modifier_apply(ctx, modifier="Union")
        
        bpy.data.objects.remove(part)
        
    logger.info(f"Assembled. Exporting to {args.output}")
    export_stl(args.output)


def main():
    # Helper to parse arguments after "--"
    if "--" in sys.argv:
        idx = sys.argv.index("--")
        pass_args = sys.argv[idx+1:]
    else:
        pass_args = []
        
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True, choices=["bulb", "prop", "barge", "assemble", "wigley"])
    parser.add_argument("--output", required=True)
    parser.add_argument("--parts", nargs="*", help="Files to import for assembly")
    
    # Allow unknown args specifically for blender's internal args if any (though we use -- to separate)
    args, unknown = parser.parse_known_args(sys.argv[sys.argv.index("--") + 1:])
    
    if args.task == "bulb":
        task_create_bulb(args)
    elif args.task == "prop":
        task_create_propeller(args)
    elif args.task == "barge":
        task_create_barge(args)
    elif args.task == "wigley":
        task_create_wigley(args)
    elif args.task == "assemble":
        task_assemble(args)

if __name__ == "__main__":
    main()
