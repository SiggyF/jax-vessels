import bpy
import math
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def clean_scene():
    # Delete everything including default Cube, Camera, Light
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
    # Purge orphan data
    for block in bpy.data.meshes:
        if block.users == 0: bpy.data.meshes.remove(block)
    for block in bpy.data.curves:
        if block.users == 0: bpy.data.curves.remove(block)

from dataclasses import dataclass

@dataclass
class BargeConfig:
    length: float = 135.0
    beam: float = 14.2
    depth: float = 4.0
    bilge_radius: float = 1.2
    parallel_midbody_start: float = 20.0
    parallel_midbody_end: float = 115.0
    bow_rake_len: float = 20.0
    stern_rake_len: float = 25.0
    stern_tunnel_height: float = 1.8

def create_nurbs_barge(config: BargeConfig = BargeConfig()):
    """
    Creates a procedural inland barge hull using NURBS surfaces.
    Scale: Meters.
    """
    # Parameters
    L = config.length
    B = config.beam
    H = config.depth
    R = config.bilge_radius 
    HalfB = B / 2.0
    
    # Target Grid Size: 9 U stations x 5 V points
    # We will create a 4x4 primitive and subdivide to get >= 9x5
    # Subdivide (2 cuts) -> 10x10 grid.
    # We will use the first 9 rows and 5 columns, or resample?
    # Resample logic: Map our 9 defined stations to the 10 available U-rows.
    # Or just use the 10 rows!
    
    # 1. Create Primitive
    # Location 0,0,0. Radius 1.
    bpy.ops.surface.primitive_nurbs_surface_surface_add(radius=1, location=(0,0,0))
    obj = bpy.context.active_object
    obj.name = "Barge_Surface"
    
    # 2. Subdivide
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.curve.select_all(action='SELECT')
    # 2 cuts -> 10x10 grid (4 points -> 3 segs -> 2 cuts/seg -> 4 + 6 = 10)
    bpy.ops.curve.subdivide(number_cuts=2)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    spline = obj.data.splines[0]
    
    # CRITICAL: Enable endpoints so surface reaches the control points
    spline.use_endpoint_u = True
    spline.use_endpoint_v = True
    
    u_count = spline.point_count_u # Should be 10
    v_count = spline.point_count_v # Should be 10
    
    logger.info(f"Surface Grid: {u_count}x{v_count}")
    
    # 3. Shape the Points
    
    # Define Target X Coordinates (for 10 rows)
    x_targets = [0.0, 2.0, 8.0, 20.0, 45.0, 90.0, 115.0, 125.0, 132.0, 135.0]
    
    # If u_count doesn't match x_targets (10), we must interpolate or resample
    real_x_coords = []
    if u_count == len(x_targets):
        real_x_coords = x_targets
    else:
        logger.warning(f"Grid U {u_count} != Target {len(x_targets)}. Resampling X.")
        # Linear map indices to 0..135 (Not ideal, loses feature alignment)
        # Better: Interpolate x_targets indices to new range
        for i in range(u_count):
            t = i / (u_count - 1)
            # Map t (0..1) to x_targets
            # Simple approach: Map t to Total Length? No, we want features.
            # Just Map t to feature list?
            # Index in x_targets = t * (len-1)
            f_idx = t * (len(x_targets) - 1)
            idx_low = int(f_idx)
            idx_high = min(idx_low + 1, len(x_targets) - 1)
            frac = f_idx - idx_low
            lrp = x_targets[idx_low] + (x_targets[idx_high] - x_targets[idx_low]) * frac
            real_x_coords.append(lrp)

    # V Columns (10 available). We only need 5 to define the section (Keel..Deck).
    # We can use the first 5 and scrunch the others or use them for more detail?
    # Let's use 10 points for the section! Smoother bilge.
    # Logical section: 0=Keel, 10=Deck.
    # distribution: 
    # 0,1: Flat Bottom
    # 2,3,4: Bilge Turn
    # 5,6,7: Side
    # 8,9: Deck Edge
    
    # Helper to get section profile
    def get_section_profile(x, num_points_v):
        # Returns list of (y, z) for this x
        
        # 1. Calculate Envelope (Width, Height, KeelZ)
        width_fac = 1.0
        # Tapers
        if x < config.parallel_midbody_start: # Stern
             t = x / config.parallel_midbody_start
             width_fac = 0.6 + 0.4 * (t**0.5)
        elif x > config.parallel_midbody_end: # Bow
             t = (x - config.parallel_midbody_end) / config.bow_rake_len
             width_fac = 1.0 - 0.9 * (t**1.5)
             
        curr_half_b = HalfB * width_fac
        
        keel_z = 0.0
        # Stern Tunnel / Rake
        if x < config.stern_rake_len:
            t = (config.stern_rake_len - x) / config.stern_rake_len
            keel_z = config.stern_tunnel_height * (t**2) 
            
        deck_z = H
        if x < 10.0: deck_z += 0.5 * ((10-x)/10)**2
        if x > 120.0: deck_z += 1.0 * ((x-120)/15)**2
        
        curr_r = min(R, curr_half_b * 0.9)
        
        # Generate Points along the section
        # We trace a "virtual" U-shape and sample it N times
        points = []
        for i in range(num_points_v):
            t = i / (num_points_v - 1) # 0..1
            
            # Map t to geometry
            # 0.0 .. 0.4 -> Bottom
            # 0.4 .. 0.6 -> Bilge
            # 0.6 .. 1.0 -> Side
            
            # Use simple parametric section
            # But we want explicit control.
            # Let's interpolate between key points.
            
            # Key points of section:
            k_keel = (0.0, keel_z)
            k_bilge_start = (curr_half_b - curr_r, keel_z)
            k_bilge_end = (curr_half_b, keel_z + curr_r)
            k_deck = (curr_half_b, deck_z)
            
        # V4: Centerline Deck (Closed Loop)
        k_deck_center = (0.0, deck_z) # Flat deck (no camber). Add camber here if needed.
        
        # Distribute t
        # We need to map 0..1 to:
        # 1. Bottom (Keel -> BilgeStart)
        # 2. Bilge (Arc)
        # 3. Side (BilgeEnd -> SideTop)
        # 4. Deck (SideTop -> Centerline)
        
        # Segments weights:
        # Bottom: 0.3
        # Bilge: 0.2
        # Side: 0.2
        # Deck: 0.3
        
        for i in range(num_points_v):
            t = i / (num_points_v - 1) # 0..1
            
            y, z = 0, 0
            if t < 0.3: # Bottom
                lt = t / 0.3
                y = k_keel[0] + (k_bilge_start[0] - k_keel[0]) * lt
                z = k_keel[1] + (k_bilge_start[1] - k_keel[1]) * lt
            elif t < 0.5: # Bilge
                lt = (t - 0.3) / 0.2
                cy = curr_half_b - curr_r
                cz = keel_z + curr_r
                ang = -math.pi/2 + lt * (math.pi/2)
                y = cy + math.cos(ang) * curr_r
                z = cz + math.sin(ang) * curr_r
            elif t < 0.7: # Side
                lt = (t - 0.5) / 0.2
                y = k_bilge_end[0] + (k_deck[0] - k_bilge_end[0]) * lt
                z = k_bilge_end[1] + (k_deck[1] - k_bilge_end[1]) * lt
            else: # Deck
                lt = (t - 0.7) / 0.3
                y = k_deck[0] + (k_deck_center[0] - k_deck[0]) * lt
                z = k_deck[1] + (k_deck_center[1] - k_deck[1]) * lt
            
            points.append((y, z))
            
        return points

    # Apply to Spline Points
    # Points are laid out: row0_col0, row0_col1 ... row0_colM, row1_col0...
    # Wait! Internal layout might be U-major or V-major?
    # Usually p[u + v * u_count]? Or p[v + u * v_count]?
    # Let's assume standard linear order.
    # We can check coordinates to verify.
    # BUT, we are overwriting them anyway.
    
    # "The points are indexed by v * resolution_u + u" -> v is major?
    # Or u * resolution_v + v?
    # Let's iterate linearly and assign based on our assumed grid structure.
    # If we get it transposed, the hull will be weird.
    # NURBS Primitive is usually U=Cyclic? No, Surface is usually grid.
    
    # We will assume U is the 'long' dimension (10) and V is the short (10).
    # Since both are 10, it's symmetric.
    # We map "U" to X and "V" to Section.
    
    idx = 0
    for u_idx in range(u_count):
        x = real_x_coords[u_idx]
        
        # Generate section for THIS x, with exactly v_count points
        section_pts = get_section_profile(x, v_count)
        
        for v_idx in range(v_count):
            if v_idx < len(section_pts):
                y, z = section_pts[v_idx]
            else:
                # Should not happen if loop logic matches
                logger.error(f"IndexError at U={u_idx} V={v_idx}. Pts={len(section_pts)}")
                y, z = 0, 0
            
            # Assign
            spline.points[idx].co = (x, y, z, 1.0)
            idx += 1
            
    # Apply Mirror
    mod_mirror = obj.modifiers.new(name="Mirror", type='MIRROR')
    mod_mirror.use_axis[0] = False # X
    mod_mirror.use_axis[1] = True  # Y
    mod_mirror.use_axis[2] = False # Z
    if hasattr(mod_mirror, "use_mirror_merge"):
         mod_mirror.use_mirror_merge = True
    else:
         try: mod_mirror.use_merge_vertices = True
         except: pass     
    mod_mirror.merge_threshold = 0.01

    logger.info("NURBS Surface Created via Ops.")
    return obj

def convert_to_mesh(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)
    mesh = bpy.data.meshes.new_from_object(obj_eval)
    
    new_obj = bpy.data.objects.new("Barge", mesh)
    bpy.context.collection.objects.link(new_obj)
    bpy.context.view_layer.objects.active = new_obj
    new_obj.select_set(True) # Select the new object
    new_obj.location = obj.location
    
    # Close the Hull (Watertight)
    # The NURBS surface is open at the top (Deck) and Transom.
    # Convert to mesh leaves these open. We must fill them.
    
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    
    # Fill Holes (Covers Deck and Transom openings)
    bpy.ops.mesh.fill_holes(sides=0) # 0 = Unlimited sides
    
    # Ensure Normals are consistent (pointing out)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    
    bpy.ops.object.mode_set(mode='OBJECT')
    
    return new_obj

def main():
    clean_scene()
    surface = create_nurbs_barge()
    
    # Convert to Mesh
    mesh_obj = convert_to_mesh(surface)
    
    # Hide the Source Surface to avoid confusion
    surface.hide_viewport = True
    surface.hide_render = True
    
    # Select the Mesh
    bpy.ops.object.select_all(action='DESELECT')
    mesh_obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_obj
    
    # Save Blend
    bpy.ops.wm.save_as_mainfile(filepath="barge_nurbs.blend")
    
    # Export STL
    stl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "vessels", "barge_nurbs.stl")
    os.makedirs(os.path.dirname(stl_path), exist_ok=True)
    
    # Ensure only Mesh is selected for export
    # Blender 4.x STL Exporter: bpy.ops.wm.stl_export
    if hasattr(bpy.ops.wm, "stl_export"):
        bpy.ops.wm.stl_export(filepath=stl_path, export_selected_objects=True)
    elif hasattr(bpy.ops.export_mesh, "stl"): # Fallback for <4.0
        bpy.ops.export_mesh.stl(filepath=stl_path, use_selection=True)
    else:
        logger.error("No STL exporter found!")
        
    logger.info(f"Exported STL to {stl_path}")

if __name__ == "__main__":
    main()
