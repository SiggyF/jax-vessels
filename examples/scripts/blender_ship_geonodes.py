import bpy
import bmesh
import math
from mathutils import Vector

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
    
    # Create Interface Sockets
    # inputs: Geometry (Hull), Bulb Scale (Vector), Bulb Location (Vector)
    # outputs: Geometry
    
    if hasattr(tree, 'interface'):
        # Blender 4.0+
        tree.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
        
        # Bulb Parameters
        s_sock = tree.interface.new_socket(name="Bulb Scale", in_out='INPUT', socket_type='NodeSocketVector')
        s_sock.default_value = (8.0, 5.5, 8.0) # Stout
        s_sock.min_value = 0.1
        
        l_sock = tree.interface.new_socket(name="Bulb Location", in_out='INPUT', socket_type='NodeSocketVector')
        l_sock.default_value = (320.0, 0.0, 6.0)
        
        tree.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    else:
        # Blender 3.x
        tree.inputs.new('NodeSocketGeometry', 'Geometry')
        
        s_sock = tree.inputs.new('NodeSocketVector', 'Bulb Scale')
        s_sock.default_value = (8.0, 5.5, 8.0)
        
        l_sock = tree.inputs.new('NodeSocketVector', 'Bulb Location')
        l_sock.default_value = (320.0, 0.0, 6.0)
        
        tree.outputs.new('NodeSocketGeometry', 'Geometry')
    
    # Nodes
    # 1. Group Input
    in_node = tree.nodes.new('NodeGroupInput')
    in_node.location = (-600, 0)
    
    # 2. Bulb Generation (Procedural)
    # Mesh Primitive UV Sphere
    sphere = tree.nodes.new('GeometryNodeMeshUVSphere')
    sphere.location = (-600, -200)
    sphere.inputs['Segments'].default_value = 32
    sphere.inputs['Rings'].default_value = 16
    sphere.inputs['Radius'].default_value = 1.0
    
    # Transform (Scale/Pos)
    trans_bulb = tree.nodes.new('GeometryNodeTransform')
    trans_bulb.location = (-400, -200)
    
    # Connect Input Params to Transform
    links = tree.links
    
    # Robust Linking via Indices
    # Group Input Outputs: 
    # 0: Geometry
    # 1: Bulb Scale
    # 2: Bulb Location
    
    # Bulb Scale (1) -> Transform Scale
    # Transform Inputs: Geometry, Translation, Rotation, Scale
    # Safest is to check naming or standard indices, but 'Scale' is standard.
    links.new(in_node.outputs[1], trans_bulb.inputs['Scale'])
    
    # Bulb Location (2) -> Transform Translation
    links.new(in_node.outputs[2], trans_bulb.inputs['Translation'])
    
    # Sphere Output (0=Mesh) -> Transform Geometry (0)
    links.new(sphere.outputs[0], trans_bulb.inputs[0])
    
    # Join (Hull + Bulb)
    join_all = tree.nodes.new('GeometryNodeJoinGeometry')
    join_all.location = (-200, 0)
    
    # Link Hull (Group Input 0) -> Join
    links.new(in_node.outputs[0], join_all.inputs[0])
    # Link Bulb (Transform Out 0) -> Join
    links.new(trans_bulb.outputs[0], join_all.inputs[0])
    
    # 3. Realize Instances (Critical for Volume/Boolean ops on primitives)
    realize = tree.nodes.new('GeometryNodeRealizeInstances')
    realize.location = (0, 0)
    
    links.new(join_all.outputs[0], realize.inputs[0])
    
    # 4. Mesh to Volume (Fusion)
    # This creates the smooth organic merge
    m2v = tree.nodes.new('GeometryNodeMeshToVolume')
    m2v.location = (200, 0)
    # Switch to Voxel Size for consistent detail
    m2v.resolution_mode = 'VOXEL_SIZE'
    
    # helper to safely set inputs
    def safe_set_input(node, name, value):
        if name in node.inputs:
            node.inputs[name].default_value = value
            
    safe_set_input(m2v, 'Voxel Size', 0.5)
    safe_set_input(m2v, 'Fill Volume', True)
    
    links.new(realize.outputs[0], m2v.inputs[0]) # Input 0 is Mesh
    
    # 5. Volume to Mesh
    v2m = tree.nodes.new('GeometryNodeVolumeToMesh')
    v2m.location = (400, 0)
    v2m.inputs['Adaptivity'].default_value = 0.05
    
    # 6. Set Shade Smooth
    shade = tree.nodes.new('GeometryNodeSetShadeSmooth')
    shade.location = (600, 0)
    
    # 7. Group Output
    out_node = tree.nodes.new('NodeGroupOutput')
    out_node.location = (800, 0)
    
    # Links
    links = tree.links
    
    # Join Hull + Bulb
    links.new(in_node.outputs['Geometry'], join_all.inputs['Geometry'])
    links.new(trans_bulb.outputs['Geometry'], join_all.inputs['Geometry'])
    
    # Join -> Realize
    links.new(join_all.outputs['Geometry'], realize.inputs['Geometry'])
    
    # Realize -> Mesh2Volume
    links.new(realize.outputs['Geometry'], m2v.inputs['Mesh'])
    
    # Vol -> Mesh
    links.new(m2v.outputs['Volume'], v2m.inputs['Volume'])
    
    # Mesh -> Shade -> Out
    links.new(v2m.outputs['Mesh'], shade.inputs['Geometry'])
    links.new(shade.outputs['Geometry'], out_node.inputs['Geometry'])
    
    print("GeoNodes setup complete. Bulb is now parametric.")

def main():
    # Clear
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.select_by_type(type='MESH')
    bpy.ops.object.delete()
    
    hull = create_main_geometry()
    # Bulb is now inside the nodes
    
    setup_geonodes(hull)
    
    # Explicitly set modifier values to ensure defaults are applied
    # (Sometimes creating via Python doesn't auto-apply defaults to the modifier instance)
    mod = hull.modifiers["HullGen"]
    
    # Finding the input identifier is tricky across versions, 
    # but usually key access by Name works if unique.
    
    # Set defaults:
    # We want a stout bulb for KVLCC2
    default_scale = (12.0, 7.0, 10.0) 
    default_loc = (323.0, 0.0, 6.0)
    
    # Try different access methods for robustness (Blender 3.x vs 4.x)
    try:
        if "Bulb Scale" in mod.keys():
             mod["Bulb Scale"] = default_scale
        if "Socket_1" in mod.keys(): # Sometimes indexed
             mod["Socket_1"] = default_scale
             
        if "Bulb Location" in mod.keys():
             mod["Bulb Location"] = default_loc
        if "Socket_2" in mod.keys():
             mod["Socket_2"] = default_loc
             
        print(f"Set modifier defaults: Scale={default_scale}, Loc={default_loc}")
    except Exception as e:
        print(f"Could not set modifier values directly: {e}")

if __name__ == "__main__":
    main()
