import logging
import bpy
import bmesh
import math
from mathutils import Vector

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def create_main_geometry():
    # 1. Create Main Hull as a CLOSED SOLID
    mesh = bpy.data.meshes.new("Hull_Base_Mesh")
    obj = bpy.data.objects.new("Hull_Base", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    L = 320.0
    B = 58.0
    D = 30.0
    half_B = B / 2.0
    
    # We generate Stbd side, then mirror to Port, then cap Deck.
    
    sections = 40 # smooth
    
    # Storage for Stbd vertices
    # grid[i][j] where i is longitudinal, j is girth
    grid = []
    
    angle_steps = 12
    
    for i in range(sections + 1):
        x = (i / sections) * 315.0 # Stop before 320
        
        # Norm param
        u = i / sections
        
        # Breadth
        bx = 1.0
        if u < 0.2: bx = (u/0.2)**0.5 # Stern taper
        if u > 0.8: bx = ((1-u)/0.2)**0.7 # Bow taper
        
        # Profile
        n = 4.0
        if u < 0.1 or u > 0.9: n = 1.6
        
        row_verts = []
        for j in range(angle_steps + 1):
            theta = (j / angle_steps) * (math.pi / 2)
            
            # Superellipse
            sin_n = abs(math.sin(theta))**(2/n)
            cos_n = abs(math.cos(theta))**(2/n)
            
            y = half_B * bx * sin_n
            z = D * (1 - cos_n)
            
            v = bm.verts.new((x, y, z))
            row_verts.append(v)
            
        grid.append(row_verts)
            
    bm.verts.ensure_lookup_table()
    
    # Skin Stbd Side
    for i in range(sections):
        for j in range(angle_steps):
            v1 = grid[i][j]
            v2 = grid[i+1][j]
            v3 = grid[i+1][j+1]
            v4 = grid[i][j+1]
            bm.faces.new((v1, v2, v3, v4))
            
    # Mirror Update:
    # We rely on BMesh ops to mirror and weld
    bmesh.ops.mirror(bm, geom=bm.verts[:] + bm.faces[:], axis='Y', merge_dist=0.01)
    
    # After mirror, we have a U-shape hull (Bottom+Sides). 
    # The TOP (Deck) is open.
    # The Centerline (Keel) should be merged by mirror op.
    
    # Recalculate to be sure
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    
    # Cap the Deck (Connect Port Deck Edge to Stbd Deck Edge)
    # The Deck Edge vertices are the last in the row (j=angle_steps)
    # After mirror, we have duplicates? No, mirror doubles them.
    # We need to find boundary edges at Z ~ D and close them.
    
    # Simpler approach: Select all boundary edges
    # Filter for edges at Z approx D
    boundary_edges = [e for e in bm.edges if e.is_boundary]
    deck_edges = [e for e in boundary_edges if (e.verts[0].co.z > D - 0.1)]
    
    # Fill the deck
    # Usually 'Bridge Edge Loops' or 'Grid Fill'.
    # Or just 'F' (Make Face) but that might be n-gon.
    # Let's clean up: make a face using bmesh context (like pressing F)
    # But checking strictly, create a face from edge loop.
    if deck_edges:
        # Sort edges or just create face from verts?
        # Only works if simple loop.
        # bmesh.ops.contextual_create(bm, geom=deck_edges)
        # Assuming convex-ish enough?
        pass # Let's rely on contextual create
        
    # Let's brute force cap boundary loops (Transom, Bow, Deck)
    # This closes everything to make a solid.
    ret = bmesh.ops.holes_fill(bm, edges=boundary_edges, sides=0) # sides=0 means fill simple holes
    
    # Ensure normals out for the new faces
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    
    bm.to_mesh(mesh)
    bm.free()
    
    return obj

def create_bulb_obj():
    # 2. Bulb Object
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=32, ring_count=16, radius=1.0, location=(320.0, 0, 6.0)
    )
    bulb = bpy.context.active_object
    bulb.name = "Bulb_Obj"
    # Scale: Long (18m), Wide (5.5m), Tall (9m)
    bulb.scale = (12.0, 4.0, 7.0) 
    
    # Hide render/viewport?
    # bulb.hide_viewport = True
    # bulb.hide_render = True
    return bulb

def setup_geonodes(hull_obj):
    # Add Modifier
    mod = hull_obj.modifiers.new(name="HullGen", type='NODES')
    
    # Create Tree definition
    tree = bpy.data.node_groups.new(name="HullFusionTree", type='GeometryNodeTree')
    mod.node_group = tree
    
    # Base Dimensions the mesh was built with
    BASE_L = 320.0
    BASE_B = 58.0
    BASE_D = 30.0
    
    # Create Interface Sockets
    if hasattr(tree, 'interface'):
        # Blender 4.0+
        tree.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
        
        # Ship Dimensions
        l_sock = tree.interface.new_socket(name="Length", in_out='INPUT', socket_type='NodeSocketFloat')
        l_sock.default_value = BASE_L
        l_sock.min_value = 1.0
        l_sock.subtype = 'DISTANCE'
        l_sock.description = "Overall Length of the ship (m)"
        
        b_sock = tree.interface.new_socket(name="Beam", in_out='INPUT', socket_type='NodeSocketFloat')
        b_sock.default_value = BASE_B
        b_sock.min_value = 0.1
        b_sock.subtype = 'DISTANCE'
        b_sock.description = "Overall Beam (m)"
        
        d_sock = tree.interface.new_socket(name="Depth", in_out='INPUT', socket_type='NodeSocketFloat')
        d_sock.default_value = BASE_D
        d_sock.subtype = 'DISTANCE'
        d_sock.description = "Depth from Keel to Deck (m)"
        
        # Bulb Parameters
        s_sock = tree.interface.new_socket(name="Bulb Scale", in_out='INPUT', socket_type='NodeSocketVector')
        s_sock.default_value = (9.0, 7.0, 7.0) 
        s_sock.description = "Bulb Dimensions (Radius in m)"
        
        l_sock = tree.interface.new_socket(name="Bulb Offset", in_out='INPUT', socket_type='NodeSocketVector')
        l_sock.default_value = (-10.0, 0.0, 5.0) # Relative to Bow Tip (L, 0, 0)
        l_sock.description = "Offset from Bow Tip (x=Length, z=0)"
        
        tree.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    else:
        # Blender 3.x Support (Less metadata support)
        tree.inputs.new('NodeSocketGeometry', 'Geometry')
        tree.inputs.new('NodeSocketFloat', 'Length').default_value = BASE_L
        tree.inputs.new('NodeSocketFloat', 'Beam').default_value = BASE_B
        tree.inputs.new('NodeSocketFloat', 'Depth').default_value = BASE_D
        tree.inputs.new('NodeSocketVector', 'Bulb Scale').default_value = (9.0, 7.0, 7.0)
        tree.inputs.new('NodeSocketVector', 'Bulb Offset').default_value = (-10.0, 0.0, 5.0)
        tree.outputs.new('NodeSocketGeometry', 'Geometry')
    
    # Nodes
    # 1. Group Input
    in_node = tree.nodes.new('NodeGroupInput')
    in_node.location = (-1000, 0)
    
    # Scale Logic (Same as before)
    # ...
    math_l = tree.nodes.new('ShaderNodeMath')
    math_l.operation = 'DIVIDE'
    math_l.inputs[1].default_value = BASE_L
    math_l.location = (-800, 200)
    
    math_b = tree.nodes.new('ShaderNodeMath')
    math_b.operation = 'DIVIDE'
    math_b.inputs[1].default_value = BASE_B
    math_b.location = (-800, 100)
    
    math_d = tree.nodes.new('ShaderNodeMath')
    math_d.operation = 'DIVIDE'
    math_d.inputs[1].default_value = BASE_D
    math_d.location = (-800, 0)
    
    comb_xyz = tree.nodes.new('ShaderNodeCombineXYZ')
    comb_xyz.location = (-600, 100)
    
    trans_hull = tree.nodes.new('GeometryNodeTransform')
    trans_hull.location = (-400, 100)
    
    # Bulb Logic
    sphere = tree.nodes.new('GeometryNodeMeshUVSphere')
    sphere.location = (-800, -200)
    sphere.inputs['Segments'].default_value = 32
    sphere.inputs['Radius'].default_value = 1.0 # Base radius 1m
    
    trans_bulb = tree.nodes.new('GeometryNodeTransform')
    trans_bulb.location = (-400, -200)
    
    # Relative Position Logic:
    # Bulb Pos = (Length, 0, 0) + Bulb Offset
    
    # 1. Create Vector (Length, 0, 0)
    comb_bow_pos = tree.nodes.new('ShaderNodeCombineXYZ')
    comb_bow_pos.location = (-800, -400)
    
    # 2. Add Offset
    vec_add = tree.nodes.new('ShaderNodeVectorMath')
    vec_add.operation = 'ADD'
    vec_add.location = (-600, -400)
    
    # Links
    links = tree.links
    
    # Hull Scale Links
    links.new(in_node.outputs['Length'], math_l.inputs[0])
    links.new(in_node.outputs['Beam'], math_b.inputs[0])
    links.new(in_node.outputs['Depth'], math_d.inputs[0])
    
    links.new(math_l.outputs[0], comb_xyz.inputs['X'])
    links.new(math_b.outputs[0], comb_xyz.inputs['Y'])
    links.new(math_d.outputs[0], comb_xyz.inputs['Z'])
    
    links.new(comb_xyz.outputs[0], trans_hull.inputs['Scale'])
    links.new(in_node.outputs['Geometry'], trans_hull.inputs['Geometry'])
    
    # Bulb Links
    # Scale
    links.new(in_node.outputs['Bulb Scale'], trans_bulb.inputs['Scale'])
    
    # Location Calculation
    # Length -> Bow Pos X
    links.new(in_node.outputs['Length'], comb_bow_pos.inputs['X'])
    # Bow Pos -> Add A
    links.new(comb_bow_pos.outputs[0], vec_add.inputs[0])
    # Bulb Offset -> Add B
    links.new(in_node.outputs['Bulb Offset'], vec_add.inputs[1])
    
    # Result -> Transform Translation
    links.new(vec_add.outputs[0], trans_bulb.inputs['Translation'])
    
    links.new(sphere.outputs[0], trans_bulb.inputs['Geometry']) # Sphere Geom
    
    # Join (Hull + Bulb)
    join_all = tree.nodes.new('GeometryNodeJoinGeometry')
    join_all.location = (-200, 0)
    
    links.new(trans_hull.outputs[0], join_all.inputs[0])
    links.new(trans_bulb.outputs[0], join_all.inputs[0])
    
    # ... Rest of Fusion Logic ...
    # (Realize -> Mesh2Volume -> Volume2Mesh -> Shade)
    
    realize = tree.nodes.new('GeometryNodeRealizeInstances')
    realize.location = (0, 0)
    links.new(join_all.outputs[0], realize.inputs[0])
    
    m2v = tree.nodes.new('GeometryNodeMeshToVolume')
    m2v.location = (200, 0)
    m2v.resolution_mode = 'VOXEL_SIZE'
    def safe_set(node, name, val):
        if name in node.inputs: node.inputs[name].default_value = val
    safe_set(m2v, 'Voxel Size', 0.5)
    safe_set(m2v, 'Fill Volume', True)
    
    links.new(realize.outputs[0], m2v.inputs[0])
    
    v2m = tree.nodes.new('GeometryNodeVolumeToMesh')
    v2m.location = (400, 0)
    v2m.inputs['Adaptivity'].default_value = 0.05
    links.new(m2v.outputs[0], v2m.inputs[0])
    
    shade = tree.nodes.new('GeometryNodeSetShadeSmooth')
    shade.location = (600, 0)
    links.new(v2m.outputs[0], shade.inputs[0])
    
    out_node = tree.nodes.new('NodeGroupOutput')
    out_node.location = (800, 0)
    links.new(shade.outputs[0], out_node.inputs[0])

    logger.info("GeoNodes setup complete. Parametric sizing enabled.")

def main():
    # Clear
    try:
        bpy.ops.object.select_all(action='DESELECT')
        bpy.ops.object.select_by_type(type='MESH')
        bpy.ops.object.delete()
    except Exception as e:
        logger.warning(f"Could not clear scene: {e}")
    
    hull = create_main_geometry()
    
    setup_geonodes(hull)
    
    # Add Decimate Modifier for simplification
    mod_dec = hull.modifiers.new(name="Simplify", type='DECIMATE')
    mod_dec.ratio = 0.5 # Simplify by 50%
    
    # Set Defaults in Modifier explicitly
    mod_gn = hull.modifiers["HullGen"]
    tree = mod_gn.node_group
    
    # Explicit values
    vals = {
        "Length": 320.0,
        "Beam": 58.0,
        "Depth": 30.0,
        "Bulb Scale": (9.0, 7.0, 7.0),
        "Bulb Offset": (-10.0, 0.0, 5.0) 
    }
    
    logger.info(f"Setting modifier parameters: {vals}")
    
    # Robust Name -> Identifier Mapping
    # Modifier keys usually use the socket Identifier (e.g. "Socket_1"), not the Name.
    name_to_id = {}
    
    if hasattr(tree, 'interface'): # Blender 4.0+
        for item in tree.interface.items_tree:
            if item.item_type == 'SOCKET':
                name_to_id[item.name] = item.identifier
    else: # Blender 3.x
        for sock in tree.inputs:
            name_to_id[sock.name] = sock.identifier
            
    logger.info(f"Interface Mapping: {name_to_id}")
    logger.info(f"Available Modifier Keys: {list(mod_gn.keys())}")
    
    for name, value in vals.items():
        identifier = name_to_id.get(name)
        if identifier and identifier in mod_gn.keys():
            mod_gn[identifier] = value
            logger.info(f"Set {name} ({identifier}) -> {value}")
        else:
            # Fallback: Try by name directly (sometimes keys match names)
            if name in mod_gn.keys():
                mod_gn[name] = value
                logger.info(f"Set {name} (Direct) -> {value}")
            else:
                logger.error(f"FAILED to find property for '{name}'. Identifier was '{identifier}'")

    logger.info("Ship Generated.")

if __name__ == "__main__":
    main()
