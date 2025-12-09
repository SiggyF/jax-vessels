import pyvista as pv
import sys

def inspect(path):
    mesh = pv.read(path)
    print(f"Bounds: {mesh.bounds}")
    print(f"Dimensions: {mesh.bounds[1]-mesh.bounds[0]}, {mesh.bounds[3]-mesh.bounds[2]}, {mesh.bounds[5]-mesh.bounds[4]}")
    
    if mesh.is_manifold:
        print("STL is manifold (watertight).")
    else:
        print("WARNING: STL is NOT manifold (has holes/open edges)!")

if __name__ == "__main__":
    inspect(sys.argv[1])
