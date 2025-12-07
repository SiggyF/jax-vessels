import bpy
import bmesh
import math
from mathutils import Vector, Matrix

def create_hull_subd(name="ProceduralShip"):
    # Clear existing
    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    
    # Create Mesh and Object
    mesh = bpy.data.meshes.new(name + "_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    # ----------------------------------------------------
    # Parameters for KVLCC2-style Tanker
    # ----------------------------------------------------
    L = 320.0
    B = 58.0
    D = 30.0
    half_B = B / 2.0
    
    # Bulb Params
    bulb_nose_x = 325.0
    bulb_width = 4.5
    bulb_z_center = 8.0
    bulb_height_r = 6.0
    
    # ----------------------------------------------------
    # Construction: "Lofting" Profiles
    # We define cross-section shapes (Ribs) at key X stations.
    # Each profile has the same number of vertices to allow easy bridging.
    # ----------------------------------------------------
    
    # Profile Definition (Starboard side only, CW winding)
    # Vertices: [Keel, Bilge_Low, Bilge_High, Waterline, Deck_Side, Deck_Center]
    # We need a consistent count. Let's say 6 verts per rib.
    
    def get_profile_verts(x_loc):
        nonlocal half_B, D, bulb_width, bulb_z_center, bulb_height_r
        
        # 0. Initialize vars with default PMB values
        w_factor = 1.0 # Width factor relative to half_B
        h_factor = 1.0 # Height factor?
        bilge_rad = 4.0
        floor_h = 0.0
        
        # Determine shape parameters based on X
        
        # 1. Stern Run (0 to 60)
        if x_loc < 60.0:
            # Transition from Transom (0) to Midship (60)
            t = x_loc / 60.0
            # Width widens from 0.6 to 1.0
            w_factor = 0.6 + 0.4 * (t**0.5)
            # Bilge gets softer? No, transom is sharp.
            # At x=0, floor is high? No, floor=0.
            # Just shape changes.
            if x_loc < 10:
                # Transom specific
                return [
                    Vector((x_loc, 0.0, 0.0)),                # 0
                    Vector((x_loc, half_B*0.3, 0.5)),         # 1
                    Vector((x_loc, half_B*w_factor, 15)),     # 2
                    Vector((x_loc, half_B*w_factor, 20)),     # 3
                    Vector((x_loc, half_B*w_factor, D)),      # 4
                    Vector((x_loc, 0.0, D))                   # 5
                ]
            else:
                 # Interpolate Run
                 return [
                    Vector((x_loc, 0.0, 0.0)),              
                    Vector((x_loc, half_B*0.8*w_factor, 0.0)), 
                    Vector((x_loc, half_B*w_factor, 4.0)),  
                    Vector((x_loc, half_B*w_factor, 15.0)), 
                    Vector((x_loc, half_B*w_factor, D)),    
                    Vector((x_loc, 0.0, D))                 
                ]

        # 2. Parallel Midbody (60 to 250)
        elif x_loc <= 250.0:
            return [
                Vector((x_loc, 0.0, 0.0)),              # 0
                Vector((x_loc, half_B*0.8, 0.0)),       # 1
                Vector((x_loc, half_B, 4.0)),           # 2
                Vector((x_loc, half_B, 15.0)),          # 3
                Vector((x_loc, half_B, D)),             # 4
                Vector((x_loc, 0.0, D))                 # 5
            ]
            
        # 3. Bow Transition (250 to 310)
        elif x_loc < 310.0:
            t = (x_loc - 250.0) / (310.0 - 250.0) # 0 to 1
            # Tapering width
            w = half_B * (1.0 - t**2)
            if w < bulb_width * 1.5: w = bulb_width * 1.5
            
            return [
                Vector((x_loc, 0.0, 0.0)),
                Vector((x_loc, w*0.5, 0.5)),
                Vector((x_loc, w, 5.0)),
                Vector((x_loc, w*1.1, 15.0)), 
                Vector((x_loc, w*1.2, D)),
                Vector((x_loc, 0.0, D))
            ]
            
        # 4. Bulb Base (310+)
        else:
            # Bulb Keyhole
            b_w = bulb_width
            b_z = bulb_z_center
            b_r = bulb_height_r
            
            flare_w = half_B * 0.4
            
            return [
                Vector((x_loc, 0.0, b_z - b_r)),     # 0 Bulb Bottom
                Vector((x_loc, b_w, b_z - b_r*0.5)), # 1 Bulb Low Side
                Vector((x_loc, b_w, b_z + b_r*0.5)), # 2 Bulb High Side
                Vector((x_loc, b_w*0.5, b_z + b_r)), # 3 Neck
                Vector((x_loc, flare_w, D)),         # 4 Deck Side
                Vector((x_loc, 0.0, D))              # 5 Deck Center
            ]

    # Stations to loft
    stations = [
        0.0, 20.0, 60.0, 
        100.0, 160.0, 220.0, 
        280.0, 305.0, 315.0, 322.0
    ]
    
    bm = bmesh.new()
    
    rows = []
    
    # Generate vertices for each station
    for x in stations:
        row_verts = []
        coords = get_profile_verts(x)
        for co in coords:
            v = bm.verts.new(co)
            row_verts.append(v)
        rows.append(row_verts)
        
    bm.verts.ensure_lookup_table()
    
    # ----------------------------------------------------
    # Skinning (Lofting)
    # ----------------------------------------------------
    for i in range(len(rows) - 1):
        r1 = rows[i]
        r2 = rows[i+1]
        
        # Connect quads
        for j in range(len(r1) - 1):
            # v1--v3
            # |    |
            # v2--v4
            # No, indices match:
            # r1[j] -- r2[j]
            # |        |
            # r1[j+1]--r2[j+1]
            
            v1 = r1[j]
            v2 = r1[j+1]
            v3 = r2[j+1]
            v4 = r2[j]
            
            bm.faces.new((v1, v2, v3, v4))
            
    # ----------------------------------------------------
    # Caps (Nose and Transom)
    # ----------------------------------------------------
    
    # Nose Cap (Bulb Tip)
    # The last row is at x=322. Let's extrude it to x=325 and collapse to a rounded nose.
    last_row = rows[-1]
    
    # Create tip vertex
    tip_z = bulb_z_center
    tip_v = bm.verts.new(Vector((bulb_nose_x, 0, tip_z))) # Bulb nose tip
    top_tip_v = bm.verts.new(Vector((324.0, 0, D)))       # Deck nose tip
    
    # Connect last row to tips
    # Indices: 0(Bot), 1, 2, 3(Neck) -> Bulb Tip
    # Indices: 4(DeckSide), 5(DeckCen) -> Deck Tip
    
    # Bulb Tip Fan
    bm.faces.new((last_row[0], last_row[1], tip_v))
    bm.faces.new((last_row[1], last_row[2], tip_v))
    bm.faces.new((last_row[2], last_row[3], tip_v))
    
    # Upper Bow Face (3-4-TopTip-Tip) - Keyhole closure
    bm.faces.new((last_row[3], last_row[4], top_tip_v, tip_v))
    
    # Deck Closure
    bm.faces.new((last_row[4], last_row[5], top_tip_v))
    
    # Transom Cap (x=0)
    # Create valid topology for the back face.
    first_row = rows[0]
    # Winding: 0->1->2->3->4->5 (CCW looking from back creates proper normal)
    bm.faces.new((first_row[0], first_row[1], first_row[2], first_row[3], first_row[4], first_row[5]))
    
    # ----------------------------------------------------
    # Centerline Handling
    # ----------------------------------------------------
    # Currently, indices 0 and 5 are on centerline (Y=0).
    # We should delete the faces on the centerline? 
    # No, we just built the starboard shell. The centerline is open.
    # Verts at Y=0 should be merging boundary.
    
    # ----------------------------------------------------
    # Modifiers for "Magic"
    # ----------------------------------------------------
    bm.to_mesh(mesh)
    bm.free()
    
    # 1. Mirror
    mod_mirror = obj.modifiers.new(name="Mirror", type='MIRROR')
    mod_mirror.use_axis[0] = False # X
    mod_mirror.use_axis[1] = True  # Y (Mirror across XZ plane)
    mod_mirror.use_bisect_axis[1] = False # Disable Bisect to prevent clipping
    mod_mirror.use_mirror_merge = True
    mod_mirror.merge_threshold = 0.01
    mod_mirror.use_clip = True # Ensure centerline vertices stick
    
    # 2. Subdivision Surface (The key to organic look)
    mod_subd = obj.modifiers.new(name="Subsurf", type='SUBSURF')
    mod_subd.levels = 2
    mod_subd.render_levels = 3
    
    # Creasing logic omitted for brevity, indices are tricky after edits.
             
    bm = bmesh.new()
    bm.from_mesh(mesh)
    
    # Recalculate Normals (Critical for proper shading/visibility)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    
    bm.to_mesh(mesh)
    bm.free()
    
    # Smooth Shade
    for p in mesh.polygons:
        p.use_smooth = True
        
    print("Sub-D Ship Generated.")

if __name__ == "__main__":
    create_hull_subd()
