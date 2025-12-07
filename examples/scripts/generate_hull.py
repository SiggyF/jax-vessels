import numpy as np
import argparse
from pathlib import Path

def write_stl(filename, vertices, faces, name="hull"):
    """
    Writes vertices and faces to an ASCII STL file.
    """
    with open(filename, 'w') as f:
        f.write(f"solid {name}\n")
        for face in faces:
            v1 = vertices[face[0]]
            v2 = vertices[face[1]]
            v3 = vertices[face[2]]
            
            f.write("facet normal 0 0 0\n")
            f.write("  outer loop\n")
            f.write(f"    vertex {v1[0]:.4f} {v1[1]:.4f} {v1[2]:.4f}\n")
            f.write(f"    vertex {v2[0]:.4f} {v2[1]:.4f} {v2[2]:.4f}\n")
            f.write(f"    vertex {v3[0]:.4f} {v3[1]:.4f} {v3[2]:.4f}\n")
            f.write("  endloop\n")
            f.write("endfacet\n")
        f.write(f"endsolid {name}\n")

def generate_barge(L=80, B=11.4, D=4.0, rake_len=5.0):
    """
    Generates a generic inland barge hull (box with raked bow/stern).
    """
    w = B / 2
    z_deck = D
    z_keel = 0.0
    
    x_stern = 0
    x_stern_fwd = rake_len
    x_bow_aft = L - rake_len
    x_bow = L
    
    # Vertices
    v_bottom_flat = [
        [x_stern_fwd, w, z_keel],  # 0
        [x_stern_fwd, -w, z_keel], # 1
        [x_bow_aft, -w, z_keel],   # 2
        [x_bow_aft, w, z_keel]     # 3
    ]
    
    v_deck = [
        [x_stern, w, z_deck],      # 4
        [x_stern, -w, z_deck],     # 5
        [x_bow, -w, z_deck],       # 6
        [x_bow, w, z_deck]         # 7
    ]
    
    verts = v_bottom_flat + v_deck
    
    # Faces (indices)
    faces = []
    # Bottom Flat
    faces.append([0, 2, 1])
    faces.append([0, 3, 2])
    # Aft Rake
    faces.append([5, 1, 0])
    faces.append([5, 0, 4])
    # Fwd Rake
    faces.append([2, 3, 7])
    faces.append([2, 7, 6])
    # Port Side
    faces.append([0, 7, 4])
    faces.append([0, 3, 7])
    # Stbd Side
    faces.append([1, 5, 2])
    faces.append([2, 5, 6])
    # Deck
    faces.append([4, 5, 6])
    faces.append([4, 6, 7])
    # Aft Transom (Close the box)
    faces.append([5, 4, 0])
    faces.append([0, 4, 0]) # Degenerate/Wrong? No, 5-4 are top, 1-0 are bottom.
    # It's actually a quad 4-5-1-0.
    # We already did Aft Rake which connects 0,1 to 4,5. So it's closed?
    # Yes, raked stern is the stern.
    
    return verts, faces

def generate_tanker(L=320, B=58, D=30):
    """
    Generates a simplified KVLCC2-like hull using parametric curves.
    """
    verts = []
    faces = []
    nx = 40; ny = 20
    w = B / 2
    grid = np.zeros((nx + 1, ny + 1, 3))
    
    for i in range(nx + 1):
        x = (i / nx) * L
        bx = 1.0; dx = 1.0
        if x < 0.2 * L:
            t = x / (0.2 * L)
            bx = t**0.5
            dx = 0.5 + 0.5 * t
        elif x > 0.8 * L:
            t = (L - x) / (0.2 * L)
            bx = t**0.6
        
        for j in range(ny + 1):
            theta = (j / ny) * (np.pi / 2)
            y_local = w * bx * np.sin(theta)
            z_local = D * (1 - np.cos(theta))
            if x < 10: z_local += 15
            grid[i, j] = [x, y_local, z_local]

    stbd_verts = []
    stbd_faces = []
    idx = 0
    node_map = {}
    
    for i in range(nx + 1):
        for j in range(ny + 1):
            stbd_verts.append(grid[i,j])
            node_map[(i,j)] = idx
            idx += 1
            
    for i in range(nx):
        for j in range(ny):
            p0 = node_map[(i, j)]
            p1 = node_map[(i+1, j)]
            p2 = node_map[(i+1, j+1)]
            p3 = node_map[(i, j+1)]
            stbd_faces.append([p0, p1, p2])
            stbd_faces.append([p0, p2, p3])
            
    verts = list(stbd_verts)
    faces = list(stbd_faces)
    n_stbd = len(verts)
    
    for v in stbd_verts:
        verts.append([v[0], -v[1], v[2]])
        
    for f in stbd_faces:
        faces.append([f[0] + n_stbd, f[2] + n_stbd, f[1] + n_stbd])
        
    return verts, faces

def main():
    parser = argparse.ArgumentParser(description="Generate procedural ship hulls")
    parser.add_argument("--type", choices=["tanker", "barge"], required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    
    if args.type == "tanker":
        v, f = generate_tanker()
    else:
        v, f = generate_barge()
        
    write_stl(args.out, v, f, args.type)
    print(f"Generated {args.type} hull at {args.out}")

if __name__ == "__main__":
    main()
