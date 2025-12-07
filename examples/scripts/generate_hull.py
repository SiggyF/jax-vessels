import numpy as np

from pathlib import Path
import math

def write_stl(filename, vertices, faces, name="hull"):
    """
    Writes vertices and faces to an ASCII STL file.
    """
    with open(filename, 'w') as f:
        f.write(f"solid {name}\n")
        
        # Calculate normals for shading
        for face in faces:
            v1 = np.array(vertices[face[0]])
            v2 = np.array(vertices[face[1]])
            v3 = np.array(vertices[face[2]])
            
            u = v2 - v1
            v = v3 - v1
            n = np.cross(u, v)
            norm = np.linalg.norm(n)
            if norm > 1e-6: n /= norm
            
            f.write(f"facet normal {n[0]:.4f} {n[1]:.4f} {n[2]:.4f}\n")
            f.write("  outer loop\n")
            f.write(f"    vertex {v1[0]:.4f} {v1[1]:.4f} {v1[2]:.4f}\n")
            f.write(f"    vertex {v2[0]:.4f} {v2[1]:.4f} {v2[2]:.4f}\n")
            f.write(f"    vertex {v3[0]:.4f} {v3[1]:.4f} {v3[2]:.4f}\n")
            f.write("  endloop\n")
            f.write("endfacet\n")
        f.write(f"endsolid {name}\n")

def generate_europe_iia_barge():
    """
    Generates a Europe Type IIa push barge.
    Dimensions: 76.5m x 11.4m x 4.0m (approx depth).
    Box shape with curved rakes at bow and stern.
    """
    L = 76.5
    B = 11.4
    D = 4.0
    w = B / 2.0
    
    # Rake parameters
    rake_len = 6.0 # Bow and stern rake length
    bilge_radius = 0.5
    
    nx = 60
    ny = 15
    
    grid = []
    
    for i in range(nx + 1):
        x = (i / nx) * L
        
        # Longitudinal profile: Deck is flat at z=D. Bottom varies.
        # Flat bottom from rake_len to L-rake_len
        z_bottom = 0.0
        
        if x < rake_len: # Stern rake
            # Parabolic/Linear transition
            t = 1 - (x / rake_len)
            z_bottom = D * 0.8 * (t**2) # Rises to 0.8*D at stern
        elif x > L - rake_len: # Bow rake
            t = (x - (L - rake_len)) / rake_len
            z_bottom = D * 0.9 * (t**1.5) # Rises to 0.9*D at bow
        
        row = []
        for j in range(ny + 1):
            # Section shape: Box with bilge radius
            # Normalized girth coordinate s from 0 (keel) to 1 (deck side)
            # We map this to y, z structure
            
            # Simple approach: U-shape interpolation isn't great for box barges.
            # Explicit segments: Bottom -> Bilge -> Side
            
            # Total girth length approx w + D (ignoring bilge curvature diff)
            # Let's parameterize by angle for bilge, and linear for flat parts.
            
            # Divide ny into 3 zones? No, simpler to just map a "superellipse" or explicit offsets.
            
            # Use superellipse for section
            # (y/w)^n + ((z-z_c)/(D-z_b))^n = 1 ??
            
            # Parametric Box Section
            # t goes 0 to 1
            t = j / ny
            
            # Define section points
            # P0: (0, z_bottom) - Keel
            # P1: (w-r, z_bottom) - Start of bilge
            # P2: (w, z_bottom+r) - End of bilge
            # P3: (w, D) - Deck edge
            
            eff_w = w
            eff_D = D
            
            # Tapering width at very ends? (Push barges are usually very square)
            # Slight taper at bow/stern corners
            if x < 1.0: eff_w = w * (0.8 + 0.2*x)
            if x > L - 1.0: eff_w = w * (0.8 + 0.2*(L-x))
            
            r = bilge_radius
            
            # Clamp r
            if r > eff_w: r = eff_w
            
            # We distribute points along the section profile
            # 0..0.4 -> Bottom
            # 0.4..0.6 -> Bilge
            # 0.6..1.0 -> Side
            
            y_sect = 0
            z_sect = 0
            
            if t < 0.4:
                # Bottom flat
                u = t / 0.4
                y_sect = u * (eff_w - r)
                z_sect = z_bottom
            elif t < 0.6:
                # Bilge
                u = (t - 0.4) / 0.2
                theta = u * (math.pi / 2)
                y_sect = (eff_w - r) + r * math.sin(theta)
                z_sect = z_bottom + r * (1 - math.cos(theta))
            else:
                # Side
                u = (t - 0.6) / 0.4
                y_sect = eff_w
                z_sect = (z_bottom + r) + u * (eff_D - (z_bottom + r))
                
            row.append([x, y_sect, z_sect])
        grid.append(row)

    return grid_to_mesh(grid)

def generate_kvlcc2_improved():
    """
    Generates a KVLCC2-like Tanker with a proper bulbous bow.
    L=320m, B=58m, D=30m.
    """
    L = 320.0
    B = 58.0
    D = 30.0
    w = B / 2.0
    
    nx = 100
    ny = 40
    
    grid = []
    
    # Bulb parameters
    bulb_len = 15.0 # Extension forward of FP? Or just length of the bulbous part.
    bulb_center_z = 10.0
    bulb_radius_y = 6.0 # Max half-width of bulb
    bulb_radius_z = 8.0 # Max half-height of bulb
    
    for i in range(nx + 1):
        x = (i / nx) * L
        
        # Longitudinal Shaping Factors
        
        # 1. Main Hull Envelope
        run_len = 0.2 * L
        pmb_start = 0.2 * L
        pmb_end = 0.8 * L # Moved fwd slightly
        ent_len = L - pmb_end
        
        # Breadth factor B(x)
        bx = 1.0
        if x < pmb_start:
            u = x / run_len
            bx = u**(0.6)
        elif x > pmb_end:
            u = (L - x) / ent_len
            bx = u**(0.6)
            
        row = []
        for j in range(ny + 1):
            theta = (j / ny) * (math.pi / 2) # 0 to pi/2
            u_girth = j / ny
            
            # Base Hull Section
            # Simple U-shape
            cw = math.cos(theta)
            sw = math.sin(theta)
            
            # Shaping the section
            # Midship is box-like with bilge
            # Ends are V/U shaped
            
            bilge_exp = 4.0
            if x < 0.15 * L: bilge_exp = 1.8
            if x > 0.85 * L: bilge_exp = 1.8
            
            # Superellipse-ish
            # (y/W)^n + ((D-z)/D)^n = 1  (approx)
            # Parametric:
            # y = W * sin(t)^(2/n)
            # z = D * (1 - cos(t)^(2/n))
            
            sin_n = abs(math.sin(theta))**(2.0/bilge_exp)
            cos_n = abs(math.cos(theta))**(2.0/bilge_exp)
            
            y_base = w * bx * sin_n
            z_base = D * (1 - cos_n)
            
            # Deck camber/sheer? Ignored for now.
            
            # 2. Additive Bulbous Bow
            # We add an ellipsoid volume at the bow.
            # Center of bulb roughly at x = L
            # It protrudes slightly? Let's keep it within L for now, or x > L?
            # User said "front is open".
            
            y_final = y_base
            z_final = z_base
            
            if x > 0.9 * L:
                 # Implicit Bulb Function
                 # Bulb is centered at (L, 0, bulb_center_z)
                 dx_b = x - L
                 
                 # Radial distance from bulb axis line
                 # We want a sphere/ellipsoid at the nose.
                 
                 # Local bulb radius at x
                 # R(x) = R_max * sqrt(1 - (dx/len)^2)
                 
                 # We simply MAX the hull width with the bulb width
                 
                 # Bulb longitudinal profile
                 # Starts at 0.9L, peaks at L?
                 bulb_start = 0.92 * L
                 if x > bulb_start:
                     t_bulb = (x - bulb_start) / (L - bulb_start) # 0 to 1
                     
                     # Spheric/Ellipsoid profile
                     # Semi-circle in profile: sqrt(1 - (1-t)^2)? No.
                     # Full nose radius at L.
                     
                     # Profile shape P(x): 0 at start, 1 at L
                     # Elliptical nose:
                     # x_rel = (x - L) / bulb_nose_len
                     # y_bulb_local = Y_max * sqrt(1 - x_rel^2)
                     
                     # Let's model it as a sphere added to the flow.
                     # Sphere center at L - R?
                     
                     # Let's try:
                     # Width of bulb at x
                     # Forward separation: x from L-15 to L
                     dx_bulb = (x - L) / 12.0 # -1 to 0 roughly
                     
                     if dx_bulb > -1.0:
                         bulb_profile = math.sqrt(max(0, 1.0 - dx_bulb**2))
                         
                         bulb_y = bulb_radius_y * bulb_profile
                         bulb_z_top = bulb_center_z + bulb_radius_z * bulb_profile
                         bulb_z_bot = bulb_center_z - bulb_radius_z * bulb_profile
                         
                         # Check if current z is within vertical bulb range
                         if z_base < bulb_z_top and z_base > bulb_z_bot:
                             # Calculate theoretical y of bulb at this z
                             dz_rel = (z_base - bulb_center_z) / (bulb_radius_z * bulb_profile)
                             if abs(dz_rel) < 1.0:
                                 local_bulb_width = bulb_y * math.sqrt(1.0 - dz_rel**2)
                                 
                                 # Smooth blend or max?
                                 # Max gives distinct bulb
                                 if local_bulb_width > y_base:
                                     y_final = local_bulb_width
                                     
            row.append([x, y_final, z_final])
            
        grid.append(row)
        
    verts, faces = grid_to_mesh(grid)
    
    # Explicitly Close the Bow (i=nx)
    # The last row of vertices (x=L) has a "hole" because it's an open contour.
    # We need to cap it.
    
    # Identify indices of the last row (Bow)
    # i=nx
    start_idx = nx * (ny + 1)
    
    # We have Stbd and Port mirrored in grid_to_mesh. 
    # Current grid_to_mesh returns ALL verts (stbd + port).
    # We need to find the specific indices.
    
    # Re-logic grid_to_mesh to handle the cap?
    # Or just return grid and do it here?
    # Let's trust grid_to_mesh returns stbd then port.
    
    n_stbd_verts = (nx + 1) * (ny + 1)
    
    # Bow Stbd vertices: [start_idx ... start_idx+ny]
    # Bow Port vertices: [start_idx+n_stbd_verts ... start_idx+n_stbd_verts+ny]
    
    # We can create a "fan" closure or just a flat face if it's a single line.
    # But x=L is a curve.
    
    # Create valid triangles to close the loop Stbd(L) -> Port(L)
    # Connect Stbd(L, j) to Stbd(L, j+1) to Port(L, j+1) to Port(L, j).
    # Same as Transom closure logic.
    
    bow_stbd_start = nx * (ny + 1)
    n_total_half = (nx + 1) * (ny + 1)
    
    for j in range(ny):
         s0 = bow_stbd_start + j
         s1 = bow_stbd_start + j + 1
         p0 = s0 + n_total_half
         p1 = s1 + n_total_half
         
         # Face S0-P0-P1 (CCW outwards)
         # Normal pointing +x
         faces.append([s0, p0, p1])
         faces.append([s0, p1, s1])
         
    return verts, faces

def grid_to_mesh(grid):
    verts = []
    faces = []
    idx = 0
    node_map = {}
    
    nx = len(grid) - 1
    ny = len(grid[0]) - 1
    
    # Flatten Stbd grid
    stbd_start_idx = 0
    for i in range(nx + 1):
        for j in range(ny + 1):
            verts.append(grid[i][j])
            node_map[(i, j)] = idx
            idx += 1
            
    # Triangulate Stbd
    for i in range(nx):
        for j in range(ny):
            p0 = node_map[(i, j)]
            p1 = node_map[(i + 1, j)]
            p2 = node_map[(i + 1, j + 1)]
            p3 = node_map[(i, j + 1)]
            
            # Two triangles
            faces.append([p0, p1, p2])
            faces.append([p0, p2, p3])
            
    # Mirror Port side
    n_stbd = len(verts)
    for v in verts[:n_stbd]:
        verts.append([v[0], -v[1], v[2]])
        
    for f in faces[:len(faces)]: # Iterate over original faces only
        # Reverse winding: v1, v3, v2
        faces.append([f[0] + n_stbd, f[2] + n_stbd, f[1] + n_stbd])
        
    # Close transom (x=0) and Bow?
    # Omitted for simplicity (open surface mesh), but usually fine for styling.
    # For CFD snappyHexMesh, we need a closed loop?
    # Use "surfaceAutoPatch" or similar in OF, or ensure closed solid.
    # Let's close the transom (i=0)
    
    # Transom closure (connect stbd i=0 to port i=0)
    # i=0 column
    center_idx = len(verts) # Virtual center point? 
    # Or just stitch Stbd(0, j) to Port(0, j) across y=0?
    # Simple: Connect Stbd(0, j) to Stbd(0, j+1) to Port(0, j+1) to Port(0, j)
    # Port indices: i,j -> map to stbd index + n_stbd
    
    for j in range(ny):
         s0 = node_map[(0, j)]
         s1 = node_map[(0, j+1)]
         p0 = s0 + n_stbd
         p1 = s1 + n_stbd
         
         # Face S0-S1-P1-P0
         # Normal pointing BACK (-x)
         # S1, S0, P0
         faces.append([s1, s0, p0])
         faces.append([s1, p0, p1])
         
    return verts, faces


import click

@click.command()
@click.option("--type", type=click.Choice(["tanker", "barge"]), required=True, help="Type of hull to generate")
@click.option("--out", type=click.Path(path_type=Path), required=True, help="Output STL file path")
def main(type, out):
    """Generate procedural ship hulls."""
    if type == "tanker":
        v, f = generate_kvlcc2_improved()
    else:
        v, f = generate_europe_iia_barge()
        
    # Ensure parent directory exists
    out.parent.mkdir(parents=True, exist_ok=True)
    write_stl(out, v, f, type)
    click.echo(f"Generated {type} hull at {out}")

if __name__ == "__main__":
    main()
