import bpy
import math
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def clean_scene():
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.select_by_type(type='MESH')
    bpy.ops.object.delete()
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.node_groups:
        if block.users == 0:
            bpy.data.node_groups.remove(block)

def create_master_section_node_group():
    group_name = "GN_Master_Section"
    if group_name in bpy.data.node_groups:
        return bpy.data.node_groups[group_name]
    
    tree = bpy.data.node_groups.new(name=group_name, type='GeometryNodeTree')
    
    # Interface
    if hasattr(tree, 'interface'): # 4.0+
        tree.interface.new_socket(name="Beam", in_out='INPUT', socket_type='NodeSocketFloat').default_value = 14.2
        tree.interface.new_socket(name="Depth", in_out='INPUT', socket_type='NodeSocketFloat').default_value = 4.0
        tree.interface.new_socket(name="Bilge Radius", in_out='INPUT', socket_type='NodeSocketFloat').default_value = 0.8
        tree.interface.new_socket(name="Curve", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    else:
        tree.inputs.new('NodeSocketFloat', 'Beam').default_value = 14.2
        tree.inputs.new('NodeSocketFloat', 'Depth').default_value = 4.0
        tree.inputs.new('NodeSocketFloat', 'Bilge Radius').default_value = 0.8
        tree.outputs.new('NodeSocketGeometry', 'Curve')

    # Nodes
    in_node = tree.nodes.new('NodeGroupInput')
    in_node.location = (-600, 0)
    
    out_node = tree.nodes.new('NodeGroupOutput')
    out_node.location = (600, 0)
    
    # Logic: Quadrilateral containing the section
    # We want a U-shape or Box shape? 
    # Issue says: "Quadrilateral Curve (Width=Beam, Height=Depth) -> Fillet"
    # Usually for a hull section we want:
    # (0, Depth) -> (0, 0) -> (Beam/2, 0) -> (Beam/2, Depth) ?
    # Or full width? "Width=Beam".
    # Assuming full box for simplicity of quadrilateral node, then maybe delete top edge?
    # Or just use "Quadrilateral" primitive.
    
    quad = tree.nodes.new('GeometryNodeCurvePrimitiveQuadrilateral')
    quad.location = (-300, 0)
    
    # Quad takes Width and Height
    # Width = Beam
    # Height = Depth
    
    links = tree.links
    links.new(in_node.outputs['Beam'], quad.inputs['Width'])
    links.new(in_node.outputs['Depth'], quad.inputs['Height'])
    
    # Fillet Curve
    fillet = tree.nodes.new('GeometryNodeFilletCurve')
    fillet.location = (0, 0)
    fillet.mode = 'POLY' # or BEZIER
    
    links.new(quad.outputs['Curve'], fillet.inputs['Curve'])
    links.new(in_node.outputs['Bilge Radius'], fillet.inputs['Radius'])
    
    # The Quad primitive creates a closed rectangle centered? Or corner?
    # Default is centered. We might need to offset it so bottom is at Z=0?
    # Actually, commonly for lofting, we want the origin to be at a specific point (e.g. Centerline, Baseline).
    # If the ship is symmetrical, do we model half? 
    # Issue says "Beam=14.2". "Quadrilateral Curve ... Fillet".
    # If we fillet all corners, the "deck" corners also get filleted. We prob don't want that.
    # But let's follow explicit instructions "Fillet Curve on bottom corners".
    # "Quadrilateral" node fillets ALL corners if a single radius is given.
    # To fillet only bottom, we might need selection.
    
    # Alternatively, construct from points using specific logic, but Issue implies simple Quad+Fillet.
    # Maybe limit fillet using selection?
    # Or just assume for now simple Fillet is "Component A".
    
    links.new(fillet.outputs['Curve'], out_node.inputs['Curve'])
    
    return tree

def create_spine_gen_node_group():
    group_name = "GN_Spine_Gen"
    if group_name in bpy.data.node_groups:
        return bpy.data.node_groups[group_name]
    
    tree = bpy.data.node_groups.new(name=group_name, type='GeometryNodeTree')
    
    if hasattr(tree, 'interface'):
        tree.interface.new_socket(name="Length", in_out='INPUT', socket_type='NodeSocketFloat').default_value = 135.0
        tree.interface.new_socket(name="Resolution X", in_out='INPUT', socket_type='NodeSocketInt').default_value = 200
        tree.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    else:
        tree.inputs.new('NodeSocketFloat', 'Length').default_value = 135.0
        tree.inputs.new('NodeSocketInt', 'Resolution X').default_value = 200
        tree.outputs.new('NodeSocketGeometry', 'Geometry')
        
    in_node = tree.nodes.new('NodeGroupInput')
    in_node.location = (-600, 0)
    out_node = tree.nodes.new('NodeGroupOutput')
    out_node.location = (600, 0)
    
    # Mesh Line
    line = tree.nodes.new('GeometryNodeMeshLine')
    line.location = (-300, 0)
    line.mode = 'END_POINTS'
    
    # Debug inputs if needed
    # for input in line.inputs: print(input.name, input.identifier)
    
    comb_xyz = tree.nodes.new('ShaderNodeCombineXYZ')
    comb_xyz.location = (-450, -100)
    
    links = tree.links
    links.new(in_node.outputs['Length'], comb_xyz.inputs['X'])
    
    # In Blender 4.x, Mesh Line inputs might be named differently or need update
    # Usually "Start Location", "End Location"
    # Using identifiers is safer if we knew them, but name usually works.
    # If "End Location" fails, maybe it is "End Position"? 
    # Let's try to find it safely.
    
    if 'End Location' in line.inputs:
        links.new(comb_xyz.outputs[0], line.inputs['End Location'])
    elif 'End Position' in line.inputs: # valid alias?
         links.new(comb_xyz.outputs[0], line.inputs['End Position'])
    else:
         # Fallback: assume second vector input?
         # Inputs: Count, Start Location, Offset (if offset mode) / End Location (if end points)
         # But mode switch changes sockets. 
         # We need to access by name usually.
         # Let's try "End Location" again, maybe I need to force update?
         # Or maybe names are localized (unlikely in script).
         pass
         
    # Actually, the error might be because I set mode immediately before accessing?
    # Blender Node inputs update dynamically.
    
    links.new(comb_xyz.outputs[0], line.inputs[3]) # Try index? 0=Count, 1=Item?, 2=Start, 3=End?
    # Let's rely on looking it up.
    
    links.new(in_node.outputs['Resolution X'], line.inputs['Count'])
    
    # Store Named Attribute "Normalized_X"
    # Value = Index / (Count - 1)
    
    idx = tree.nodes.new('GeometryNodeInputIndex')
    idx.location = (-300, -200)
    
    cnt = tree.nodes.new('GeometryNodeInputMeshEdgeVertices') # ERROR: we need Count from input
    # Actually we can get count from Domain Size or just reusing input.
    # Reusing input is safer.
    
    math_sub = tree.nodes.new('ShaderNodeMath')
    math_sub.operation = 'SUBTRACT'
    math_sub.inputs[1].default_value = 1.0
    
    links.new(in_node.outputs['Resolution X'], math_sub.inputs[0])
    
    math_div = tree.nodes.new('ShaderNodeMath')
    math_div.operation = 'DIVIDE'
    
    links.new(idx.outputs[0], math_div.inputs[0])
    links.new(math_sub.outputs[0], math_div.inputs[1])
    
    store = tree.nodes.new('GeometryNodeStoreNamedAttribute')
    store.location = (0, 0)
    store.data_type = 'FLOAT'
    store.domain = 'POINT'
    store.inputs['Name'].default_value = "Normalized_X"
    
    links.new(line.outputs['Mesh'], store.inputs['Geometry'])
    links.new(math_div.outputs[0], store.inputs['Value'])
    
    links.new(store.outputs['Geometry'], out_node.inputs['Geometry'])
    
    return tree

def create_hull_shaper_node_group():
    group_name = "GN_Hull_Shaper"
    if group_name in bpy.data.node_groups:
        return bpy.data.node_groups[group_name]
    
    tree = bpy.data.node_groups.new(name=group_name, type='GeometryNodeTree')
    
    if hasattr(tree, 'interface'):
        tree.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
        # We can't pass Curves (Float Curve) as socket input easily in Geonodes prior to very recent versions?
        # Actually we usually contain the curves INSIDE the node group or pass a dummy geometry to sample?
        # Ideally we expose parameters to control the shape, OR we assume the curves are internal to the modifier for now.
        # "Plan Shape Curve (Float Curve)" -> This suggests using a Float Curve Node inside the group.
        # So we won't expose them as sockets unless we use "Object Info" to sample external curves.
        # Let's put Float Curve nodes INSIDE this group for now.
        tree.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    else:
        tree.inputs.new('NodeSocketGeometry', 'Geometry')
        tree.outputs.new('NodeSocketGeometry', 'Geometry')

    in_node = tree.nodes.new('NodeGroupInput')
    in_node.location = (-800, 0)
    out_node = tree.nodes.new('NodeGroupOutput')
    out_node.location = (800, 0)
    
    # Read Normalized_X
    read_norm = tree.nodes.new('GeometryNodeInputNamedAttribute')
    read_norm.data_type = 'FLOAT'
    read_norm.inputs['Name'].default_value = "Normalized_X"
    read_norm.location = (-800, 200)
    
    # 1. Plan Shape (Width Control)
    # Map X to Width Factor
    plan_curve = tree.nodes.new('ShaderNodeFloatCurve')
    plan_curve.location = (-500, 200)
    
    # Configure Curve Points for Barge Shape
    # Default is 2 points: (0,0) and (1,1). We want Box shape.
    # Points:
    # 0.0 -> 0.6 (Stern Transom Width)
    # 0.1 -> 1.0 (Parallel Midbody Start)
    # 0.9 -> 1.0 (Parallel Midbody End)
    # 1.0 -> 0.4 (Bow Width)
    
    curve = plan_curve.mapping.curves[0]
    
    # Reuse existing points to avoid removal errors
    # Default usually has 2 points
    
    # Define our target data
    # (Location X, Location Y, Handle Type)
    targets = [
        ((0.0, 0.6), 'VECTOR'),  # 0. Stern Transom
        ((0.05, 0.9), 'AUTO'),   # 1. Stern Taper
        ((0.1, 1.0), 'AUTO'),    # 2. Parallel Start
        ((0.9, 1.0), 'AUTO'),    # 3. Parallel End
        ((0.95, 0.8), 'AUTO'),   # 4. Bow Taper
        ((1.0, 0.2), 'VECTOR')   # 5. Bow Tip
    ]
    
    # Ensure we have enough points
    while len(curve.points) < len(targets):
        curve.points.new(0.5, 0.5)
        
    # If too many (unlikely for default), remove or ignore. 
    # Default is 2. We need 6. So we just add 4.
    
    # Apply data
    for i, (loc, h_type) in enumerate(targets):
        p = curve.points[i]
        p.location = loc
        p.handle_type = h_type
        
    # Refresh curve
    plan_curve.mapping.update()
    
    # 3. Parallel Midbody End (0.9 -> 1.0)
    p3 = curve.points.new(0.9, 1.0)
    p3.handle_type = 'AUTO'
    
    # 4. Bow Taper Start (0.95 -> 0.8)
    p4 = curve.points.new(0.95, 0.8)
    p4.handle_type = 'AUTO'
    
    # 5. Bow Tip (1.0 -> 0.2) - Use VECTOR for sharp finish
    p5 = curve.points.new(1.0, 0.2)
    p5.handle_type = 'VECTOR'
    
    # Refresh curve
    plan_curve.mapping.update()
    
    links = tree.links
    links.new(read_norm.outputs[0], plan_curve.inputs['Value'])
    
    # Set Position (Scale Y)
    # We want to Multiply Y by this factor.
    pos = tree.nodes.new('GeometryNodeInputPosition')
    sep_xyz = tree.nodes.new('ShaderNodeSeparateXYZ')
    
    links.new(pos.outputs[0], sep_xyz.inputs[0])
    
    math_mul = tree.nodes.new('ShaderNodeMath')
    math_mul.operation = 'MULTIPLY'
    
    links.new(sep_xyz.outputs['Y'], math_mul.inputs[0])
    links.new(plan_curve.outputs['Value'], math_mul.inputs[1])
    
    comb_xyz = tree.nodes.new('ShaderNodeCombineXYZ')
    links.new(sep_xyz.outputs['X'], comb_xyz.inputs['X'])
    links.new(math_mul.outputs[0], comb_xyz.inputs['Y'])
    links.new(sep_xyz.outputs['Z'], comb_xyz.inputs['Z']) # Temporary Z
    
    # 2. Sheer Line (Deck Height Control)
    # Map X to Z Add
    sheer_curve = tree.nodes.new('ShaderNodeFloatCurve')
    sheer_curve.location = (-500, -200)
    
    links.new(read_norm.outputs[0], sheer_curve.inputs['Value'])
    
    # Add to Z
    math_add_z = tree.nodes.new('ShaderNodeMath')
    math_add_z.operation = 'ADD'
    
    links.new(sep_xyz.outputs['Z'], math_add_z.inputs[0])
    links.new(sheer_curve.outputs['Value'], math_add_z.inputs[1])
    
    links.new(math_add_z.outputs[0], comb_xyz.inputs['Z']) # Update Z
    
    # Apply
    set_pos = tree.nodes.new('GeometryNodeSetPosition')
    set_pos.location = (400, 0)
    
    links.new(in_node.outputs['Geometry'], set_pos.inputs['Geometry'])
    links.new(comb_xyz.outputs[0], set_pos.inputs['Position'])
    
    links.new(set_pos.outputs['Geometry'], out_node.inputs['Geometry'])
    
    return tree

def create_tunnel_deformer_node_group():
    group_name = "GN_Tunnel_Deformer"
    if group_name in bpy.data.node_groups:
        return bpy.data.node_groups[group_name]
    
    tree = bpy.data.node_groups.new(name=group_name, type='GeometryNodeTree')
    
    if hasattr(tree, 'interface'):
        tree.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
        tree.interface.new_socket(name="Tunnel Height", in_out='INPUT', socket_type='NodeSocketFloat').default_value = 1.8
        tree.interface.new_socket(name="Tunnel Start", in_out='INPUT', socket_type='NodeSocketFloat').default_value = 25.0
        tree.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    else:
        tree.inputs.new('NodeSocketGeometry', 'Geometry')
        tree.inputs.new('NodeSocketFloat', 'Tunnel Height').default_value = 1.8
        tree.inputs.new('NodeSocketFloat', 'Tunnel Start').default_value = 25.0
        tree.outputs.new('NodeSocketGeometry', 'Geometry')

    in_node = tree.nodes.new('NodeGroupInput')
    in_node.location = (-800, 0)
    out_node = tree.nodes.new('NodeGroupOutput')
    out_node.location = (800, 0)
    
    # Logic:
    # Select vertices where:
    # 1. Z < Bilge Radius (or some height threshold). Actually just bottom vertices.
    # 2. X < Tunnel Start
    
    pos = tree.nodes.new('GeometryNodeInputPosition')
    sep = tree.nodes.new('ShaderNodeSeparateXYZ')
    tree.links.new(pos.outputs[0], sep.inputs[0])
    
    # Condition X
    comp_x = tree.nodes.new('FunctionNodeCompare')
    comp_x.data_type = 'FLOAT'
    comp_x.operation = 'LESS_THAN'
    
    tree.links.new(sep.outputs['X'], comp_x.inputs['A'])
    tree.links.new(in_node.outputs['Tunnel Start'], comp_x.inputs['B'])
    
    # Condition Z (Approximation: Z < 1.0??)
    # Ideally only "flat bottom" nodes.
    # Let's say Z < 0.1
    comp_z = tree.nodes.new('FunctionNodeCompare')
    comp_z.data_type = 'FLOAT'
    comp_z.operation = 'LESS_THAN'
    comp_z.inputs['B'].default_value = 0.1 
    tree.links.new(sep.outputs['Z'], comp_z.inputs['A'])
    
    # Combine conditions
    bool_and = tree.nodes.new('FunctionNodeBooleanMath')
    bool_and.operation = 'AND'
    # Use index 0 for outputs to be safe across versions (usually 'Boolean' or 'Result')
    tree.links.new(comp_x.outputs[0], bool_and.inputs[0])
    tree.links.new(comp_z.outputs[0], bool_and.inputs[1])
    
    # Deform Z
    # We want a smooth rise. 
    # Shape function: Simple parabolic or cosine from X=0 to X=Start?
    # Normalize X in Tunnel Region: u = X / TunnelStart
    # Rise = Height * (1 - u^2) ? Or something to make it zero at TunnelStart.
    # At X=0 (Stern), Rise = Max Height.
    # At X=TunnelStart, Rise = 0.
    
    math_div = tree.nodes.new('ShaderNodeMath')
    math_div.operation = 'DIVIDE'
    tree.links.new(sep.outputs['X'], math_div.inputs[0])
    tree.links.new(in_node.outputs['Tunnel Start'], math_div.inputs[1]) # u = x/L
    
    # Smooth step (1-u)
    # Let's use Float Curve again for shape control? Or just simple math.
    # let's do (1 - u).
    math_sub = tree.nodes.new('ShaderNodeMath')
    math_sub.operation = 'SUBTRACT'
    math_sub.inputs[0].default_value = 1.0
    tree.links.new(math_div.outputs[0], math_sub.inputs[1]) # 1 - u
    
    # Clamp 0 just in case
    math_max = tree.nodes.new('ShaderNodeMath')
    math_max.operation = 'MAXIMUM'
    math_max.inputs[1].default_value = 0.0
    tree.links.new(math_sub.outputs[0], math_max.inputs[0])
    
    # Multiply by Height
    math_mul = tree.nodes.new('ShaderNodeMath')
    math_mul.operation = 'MULTIPLY'
    tree.links.new(math_max.outputs[0], math_mul.inputs[0])
    tree.links.new(in_node.outputs['Tunnel Height'], math_mul.inputs[1])
    
    # Set Position (Offset Z)
    set_pos = tree.nodes.new('GeometryNodeSetPosition')
    
    tree.links.new(in_node.outputs['Geometry'], set_pos.inputs['Geometry'])
    tree.links.new(bool_and.outputs[0], set_pos.inputs['Selection'])
    
    # We need to construct offset vector (0,0, Z_Rise)
    comb_off = tree.nodes.new('ShaderNodeCombineXYZ')
    tree.links.new(math_mul.outputs[0], comb_off.inputs['Z'])
    
    tree.links.new(comb_off.outputs[0], set_pos.inputs['Offset'])
    
    tree.links.new(set_pos.outputs['Geometry'], out_node.inputs['Geometry'])
    
    return tree

def create_assembly_node_group(master, spine, shaper, tunnel):
    group_name = "GN_Main_Assembly"
    tree = bpy.data.node_groups.new(name=group_name, type='GeometryNodeTree')
    
    # Interface
    # Expose inputs from components
    if hasattr(tree, 'interface'):
        tree.interface.new_socket(name="Length", in_out='INPUT', socket_type='NodeSocketFloat').default_value = 135.0
        tree.interface.new_socket(name="Beam", in_out='INPUT', socket_type='NodeSocketFloat').default_value = 14.2
        tree.interface.new_socket(name="Depth", in_out='INPUT', socket_type='NodeSocketFloat').default_value = 4.0
        tree.interface.new_socket(name="Bilge Radius", in_out='INPUT', socket_type='NodeSocketFloat').default_value = 0.8
        tree.interface.new_socket(name="Resolution X", in_out='INPUT', socket_type='NodeSocketInt').default_value = 200
        tree.interface.new_socket(name="Tunnel Height", in_out='INPUT', socket_type='NodeSocketFloat').default_value = 1.8
        tree.interface.new_socket(name="Tunnel Start", in_out='INPUT', socket_type='NodeSocketFloat').default_value = 25.0
        tree.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    else:
        # Compatibility
        pass 

    in_node = tree.nodes.new('NodeGroupInput')
    in_node.location = (-1000, 0)
    out_node = tree.nodes.new('NodeGroupOutput')
    out_node.location = (1000, 0)
    
    # 1. Generate Spine
    node_spine = tree.nodes.new('GeometryNodeGroup')
    node_spine.node_tree = spine
    node_spine.location = (-700, 0)
    
    tree.links.new(in_node.outputs['Length'], node_spine.inputs['Length'])
    tree.links.new(in_node.outputs['Resolution X'], node_spine.inputs['Resolution X'])
    
    # 2. Instance Master Section
    inst = tree.nodes.new('GeometryNodeInstanceOnPoints')
    inst.location = (-500, 0)
    tree.links.new(node_spine.outputs['Geometry'], inst.inputs['Points'])
    
    node_master = tree.nodes.new('GeometryNodeGroup')
    node_master.node_tree = master
    node_master.location = (-700, -200)
    
    tree.links.new(in_node.outputs['Beam'], node_master.inputs['Beam'])
    tree.links.new(in_node.outputs['Depth'], node_master.inputs['Depth'])
    tree.links.new(in_node.outputs['Bilge Radius'], node_master.inputs['Bilge Radius'])
    
    tree.links.new(node_master.outputs['Curve'], inst.inputs['Instance'])
    
    # 3. Realize
    realize = tree.nodes.new('GeometryNodeRealizeInstances')
    realize.location = (-300, 0)
    tree.links.new(inst.outputs['Instances'], realize.inputs[0])
    
    # Convert Curve to Mesh? Or Loft?
    # If Master Section is a Curve, realized instances are Curves.
    # To skin them, we need "Curve to Mesh" with a profile? No, we have profiles.
    # We want to "Bridge" them. geometry nodes doesn't imply lofting easily from separate curves.
    # A standard trick: Use a Grid primitive instead? 
    # Or: "Curve to Mesh" where Profile is the Section and Curve is the Spine? 
    # YES! That's the standard way.
    # So "2. Instance" is WRONG for lofting.
    # Correct: use "Curve to Mesh".
    # Curve = Spine. Profile = Master Section.
    
    # Let's fix 2 & 3.
    c2m = tree.nodes.new('GeometryNodeCurveToMesh')
    c2m.location = (-400, 0)
    
    # Spine is Mesh Line. Need Mesh to Curve?
    m2c = tree.nodes.new('GeometryNodeMeshToCurve')
    m2c.location = (-550, 0)
    tree.links.new(node_spine.outputs['Geometry'], m2c.inputs['Mesh'])
    tree.links.new(m2c.outputs['Curve'], c2m.inputs['Curve'])
    
    # Enable Fill Caps
    if 'Fill Caps' in c2m.inputs:
        c2m.inputs['Fill Caps'].default_value = True
    
    tree.links.new(node_master.outputs['Curve'], c2m.inputs['Profile Curve'])
    
    # Be careful: Curve to Mesh aligns Profile Z to Curve Tangent.
    # Spine is along X. Master Section is in XY? 
    # We might need to orient Master Section.
    
    # 4. Shape Hull
    node_shaper = tree.nodes.new('GeometryNodeGroup')
    node_shaper.node_tree = shaper
    node_shaper.location = (-200, 0)
    
    tree.links.new(c2m.outputs['Mesh'], node_shaper.inputs['Geometry'])
    
    # 5. Tunnel
    node_tunnel = tree.nodes.new('GeometryNodeGroup')
    node_tunnel.node_tree = tunnel
    node_tunnel.location = (0, 0)
    
    tree.links.new(node_shaper.outputs['Geometry'], node_tunnel.inputs['Geometry'])
    tree.links.new(in_node.outputs['Tunnel Height'], node_tunnel.inputs['Tunnel Height'])
    tree.links.new(in_node.outputs['Tunnel Start'], node_tunnel.inputs['Tunnel Start'])
    
    # 6. Cap Ends (Fill Holes) - REMOVED (Use Fill Caps in CurveToMesh)
    # fill = tree.nodes.new('GeometryNodeFillHoles')
    
    # 7. Triangulate
    tri = tree.nodes.new('GeometryNodeTriangulate')
    tri.location = (400, 0)
    # Link Tunnel directly to Triangulate
    tree.links.new(node_tunnel.outputs['Geometry'], tri.inputs['Mesh'])
    
    tree.links.new(tri.outputs['Mesh'], out_node.inputs['Geometry'])
    
    return tree

def main():
    clean_scene()
    
    gn_master = create_master_section_node_group()
    gn_spine = create_spine_gen_node_group()
    gn_shaper = create_hull_shaper_node_group()
    gn_tunnel = create_tunnel_deformer_node_group()
    gn_assembly = create_assembly_node_group(gn_master, gn_spine, gn_shaper, gn_tunnel)
    
    # Create Main Object
    mesh = bpy.data.meshes.new("BargeMesh")
    obj = bpy.data.objects.new("Barge", mesh)
    bpy.context.collection.objects.link(obj)
    
    mod = obj.modifiers.new(name="BargeGen", type='NODES')
    mod.node_group = gn_assembly
    
    # --- Debug Substeps ---
    row_offset = 50.0 # meters
    
    # 1. Debug Master Section
    # Create an object that just uses the Master Section node
    mesh_sect = bpy.data.meshes.new("Debug_Section_Mesh")
    obj_sect = bpy.data.objects.new("Debug_Section", mesh_sect)
    obj_sect.location.y = -row_offset
    bpy.context.collection.objects.link(obj_sect)
    
    mod_sect = obj_sect.modifiers.new(name="DebugSection", type='NODES')
    # We need a wrapper to output the curve
    tree_sect = bpy.data.node_groups.new(name="Debug_Section_Tree", type='GeometryNodeTree')
    if hasattr(tree_sect, 'interface'):
        tree_sect.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    else:
        tree_sect.outputs.new('NodeSocketGeometry', 'Geometry')
        
    out_s = tree_sect.nodes.new('NodeGroupOutput')
    group_s = tree_sect.nodes.new('GeometryNodeGroup')
    group_s.node_tree = gn_master
    tree_sect.links.new(group_s.outputs['Curve'], out_s.inputs['Geometry'])
    mod_sect.node_group = tree_sect
    
    # 2. Debug Spine
    mesh_spine = bpy.data.meshes.new("Debug_Spine_Mesh")
    obj_spine = bpy.data.objects.new("Debug_Spine", mesh_spine)
    obj_spine.location.y = -row_offset * 1.5
    bpy.context.collection.objects.link(obj_spine)
    
    mod_spine = obj_spine.modifiers.new(name="DebugSpine", type='NODES')
    tree_spine = bpy.data.node_groups.new(name="Debug_Spine_Tree", type='GeometryNodeTree')
    if hasattr(tree_spine, 'interface'):
        tree_spine.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    else:
        tree_spine.outputs.new('NodeSocketGeometry', 'Geometry')
    out_sp = tree_spine.nodes.new('NodeGroupOutput')
    group_sp = tree_spine.nodes.new('GeometryNodeGroup')
    group_sp.node_tree = gn_spine
    tree_spine.links.new(group_sp.outputs['Geometry'], out_sp.inputs['Geometry'])
    mod_spine.node_group = tree_spine

    logger.info("Barge and Debug Objects Generated.")
    
    # Save validation file
    bpy.ops.wm.save_as_mainfile(filepath="barge_debug.blend")

if __name__ == "__main__":
    main()
