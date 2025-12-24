import argparse
import json
import re
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True, help="Hull verification report")
    parser.add_argument("--dict", type=Path, required=True, help="Path to dynamicMeshDict or include file")
    args = parser.parse_args()

    # 1. Load Hull Data
    with open(args.report, 'r') as f:
        data = json.load(f)
    
    com = data['hydrostatics']['center_of_mass']
    volume = data['hydrostatics']['volume']
    
    # Volume in report is now the DISPLACED VOLUME at Z=0.
    # To float at Z=0, Mass = Displaced Volume * Density.
    # We assume standard seawater density 1025 kg/m3.
    mass = abs(volume) * 1025.0

    print(f"Configuring Case:")
    print(f"  CoM: {com}")
    print(f"  Vol: {volume} -> Mass (est): {mass}")

    # 2. Patch Dictionary
    # We use regex to be robust against formatting differences
    content = args.dict.read_text()

    # Patch Centre of Mass
    # Pattern: centreOfMass    (67.5 0 2);
    com_str = f"centreOfMass    ({com[0]:.6f} {com[1]:.6f} {com[2]:.6f});"
    content = re.sub(r'centreOfMass\s+\(.*;', com_str, content)

    # Patch Mass
    mass_str = f"mass            {mass:.6f};"
    content = re.sub(r'mass\s+.*;', mass_str, content)
    
    # Write back
    HEADER = """/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  2406                                  |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      dynamicMeshDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

"""
    if "FoamFile" not in content:
        content = HEADER + content

    args.dict.write_text(content)
    print(f"Updated {args.dict}")

if __name__ == "__main__":
    main()
