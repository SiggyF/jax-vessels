import bpy
import math
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def clean_scene():
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.select_by_type(type='MESH')
    bpy.ops.object.select_by_type(type='SURFACE')
    bpy.ops.object.delete()
    # Purge
    for block in bpy.data.meshes:
        if block.users == 0: bpy.data.meshes.remove(block)
    for block in bpy.data.curves:
        if block.users == 0: bpy.data.curves.remove(block)

def create_nurbs_barge():
    # Parameters
    L = 135.0
    B = 14.2
    H = 4.0
    R = 0.8 # Bilge Radius
    HalfB = B / 2.0
    
    # We define the control point grid (U x V)
    # U = Longitudinal (X)
    # V = Transverse (Y, Z) section curve
    
    # U Stations (X positions)
    u_stations = [
        0.0,    # Transom
        2.0,    # Stern
        10.0,   # Stern Run
        20.0,   # Parallel Start
        67.5,   # Midship
        115.0,  # Parallel End
        125.0,  # Bow Entrance
        132.0,  # Bow Tip
        135.0   # Cap
    ]
    num_u = len(u_stations)
    
    # V Control Points (For a Section)
    # To approximate a box with bilge radius R:
    # 4 Points (Order 3?): Keel, BilgeInner, BilgeOuter, Deck
    # Or 5 Points (Order 4): Keel, BottomFlatEnd, Corner, SideStart, Deck
    # Let's use 5 points for better control of the "Corner".
    # P0: (0, 0) - Keel
    # P1: (HalfB - R, 0) - Bottom Flat End
    # P2: (HalfB, 0) - Corner Control (Weight?)
    # P3: (HalfB, R) - Side Vertical Start
    # P4: (HalfB, H) - Deck
    
    # However, the shape changes along U.
    # We define a function `get_section_points(x)` that returns the 5 V-points.
    
    def get_section_width_factor(x):
        # 0..1 factor for Beam
        if 20.0 <= x <= 115.0: return 1.0 # Parallel Midbody
        
        # Stern Taper
        if x < 20.0:
            # Transom width (x=0) ~ 0.6 * HalfB
            # Parabolic or linear taper?
            t = x / 20.0
            return 0.6 + 0.4 * (t**0.5) # Blunt stern
            
        # Bow Taper
        if x > 115.0:
            # 115 -> 135
            t = (x - 115.0) / 20.0
            # Taper to 0 (or small nose)
            # Nose width ~ 0.1 at 135
            return 1.0 - 0.9 * (t**1.5)
            
        return 1.0
        
    def get_section_keel_rise(x):
        # Rise of floor / tunnel at stern?
        # Stern Tunnel: x < 25.
        if x < 25.0:
            # Rise to 1.8m at transom?
            # Simple linear rise for NURBS demo
            t = (25.0 - x) / 25.0
            return 1.5 * (t**2)
        return 0.0

    # Create Curve Data
    curve_data = bpy.data.curves.new('Barge_NURBS', type='SURFACE')
    curve_data.dimensions = '3D'
    
    spline = curve_data.splines.new(type='NURBS')
    
    num_v = 5
    spline.points.add(num_u * num_v - 1) # Total points minus 1 (first already exists)
    
    # Configure Dimensions
    spline.use_cyclic_u = False
    spline.use_cyclic_v = False
    spline.use_endpoint_u = True
    spline.use_endpoint_v = True
    spline.order_u = 4 # Degree 3
    spline.order_v = 4 # Degree 3
    
    # Populate Points
    # Points are stored flat: u0v0, u0v1, ... u0vN, u1v0...
    
    pt_index = 0
    for i, x in enumerate(u_stations):
        width_fac = get_section_width_factor(x)
        keel_z = get_section_keel_rise(x)
        
        curr_half_b = HalfB * width_fac
        # Adjust bilge radius if beam is too small?
        curr_r = min(R, curr_half_b * 0.9)
        
        # V0: Keel
        v0 = (x, 0.0, keel_z, 1.0)
        
        # V1: Bottom Flat End
        v1 = (x, curr_half_b - curr_r, keel_z, 1.0)
        
        # V2: Corner (Control)
        # To make a nice corner, place it at (HalfB, Keel_Z)
        v2 = (x, curr_half_b, keel_z, 1.0) 
        
        # V3: Side Vertical Start
        # Ensure side is vertical?
        # For bow/stern flare, wall might slope.
        # But let's assume vertical side for simplicity, just narrower.
        v3 = (x, curr_half_b, keel_z + curr_r, 1.0)
        
        # V4: Deck
        # Add sheer? (Deck height rises at ends)
        sheer = 0.0
        if x < 10.0: sheer = 0.5 * ((10-x)/10)**2
        if x > 120.0: sheer = 1.0 * ((x-120)/15)**2
        
        v4 = (x, curr_half_b, H + sheer, 1.0)
        
        # Assign
        spline.points[pt_index].co = v0; pt_index += 1
        spline.points[pt_index].co = v1; pt_index += 1
        spline.points[pt_index].co = v2; pt_index += 1
        spline.points[pt_index].co = v3; pt_index += 1
        spline.points[pt_index].co = v4; pt_index += 1
        
    # Create Object
    obj = bpy.data.objects.new("Barge_Surface", curve_data)
    bpy.context.collection.objects.link(obj)
    
    # Mirror modifier to create full hull
    mod_mirror = obj.modifiers.new(name="Mirror", type='MIRROR')
    mod_mirror.use_axis[0] = False # X
    mod_mirror.use_axis[1] = True  # Y
    mod_mirror.use_axis[2] = False # Z
    
    # API Change: use_mirror_merge in recent versions?
    if hasattr(mod_mirror, "use_mirror_merge"):
         mod_mirror.use_mirror_merge = True
    else:
         try:
             mod_mirror.use_merge_vertices = True
         except:
             pass 
             
    mod_mirror.merge_threshold = 0.01
    
    logger.info("NURBS Surface Created.")
    return obj

def convert_to_mesh(obj):
    # Convert to mesh
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)
    mesh = bpy.data.meshes.new_from_object(obj_eval)
    
    new_obj = bpy.data.objects.new("Barge", mesh)
    bpy.context.collection.objects.link(new_obj)
    new_obj.location = obj.location
    
    # Ensure it's active
    bpy.context.view_layer.objects.active = new_obj
    
    return new_obj

def main():
    clean_scene()
    surface = create_nurbs_barge()
    
    # Convert to Mesh for usage/verification
    mesh_obj = convert_to_mesh(surface)
    
    # Move surface to hidden collection or just hide?
    # surface.hide_viewport = True
    
    # Save blend
    bpy.ops.wm.save_as_mainfile(filepath="barge_nurbs.blend")

if __name__ == "__main__":
    main()
