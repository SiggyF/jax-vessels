#!/bin/bash
set -e
CASE_DIR=build/wave_verification
rm -rf $CASE_DIR
mkdir -p $CASE_DIR

echo "Preparing Wave Verification Case..."
cp -r templates/wave_tank/* $CASE_DIR/

# Copy Wave Configuration from Hull case to ensure consistency
cp templates/floating_hull/constant/waveProperties $CASE_DIR/constant/
cp templates/floating_hull/0/U.waves $CASE_DIR/0/U
cp templates/floating_hull/0/alpha.water.waves $CASE_DIR/0/alpha.water

# Update blockMesh for reasonable wave resolution
# Generate blockMeshDict explicitly to control boundary types
cat <<EOF > $CASE_DIR/system/blockMeshDict
/*--------------------------------*- C++ -*----------------------------------*\\
  =========                 |
  \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \\\\    /   O peration     | Website:  www.openfoam.com
    \\\\  /    A nd           |
     \\\\/     M anipulation  |
\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      blockMeshDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

scale   1;

vertices
(
    (-100 -150 -10)
    ( 400 -150 -10)
    ( 400  150 -10)
    (-100  150 -10)
    (-100 -150  100)
    ( 400 -150  100)
    ( 400  150  100)
    (-100  150  100)
);

blocks
(
    hex (0 1 2 3 4 5 6 7) (200 20 60) simpleGrading (1 1 1)
);

edges
();

boundary
(
    inlet
    {
        type patch;
        faces
        (
            (0 4 7 3)
        );
    }
    outlet
    {
        type patch;
        faces
        (
            (1 2 6 5)
        );
    }
    bottom
    {
        type patch; // Changed from symmetryPlane to patch to match 0/* BCs (wall/slip/zeroGradient)
        faces
        (
            (0 3 2 1)
        );
    }
    top
    {
        type patch;
        faces
        (
            (4 5 6 7)
        );
    }
    side_right
    {
        type symmetryPlane;
        faces
        (
            (0 1 5 4)
        );
    }
    side_left
    {
        type symmetryPlane;
        faces
        (
            (3 7 6 2)
        );
    }
);

mergePatchPairs
();

// ************************************************************************* //
EOF

# sed -i '' 's/(40 20 20)/(200 20 60)/' $CASE_DIR/system/blockMeshDict
# sed -i '' 's/type symmetryPlane;/type patch;/g' $CASE_DIR/system/blockMeshDict
# Wait, this changes sides too. Sides are symmetryPlane. U.waves usually has symmetryPlane for sides.
# Let's be specific.
# Replace just the bottom definition.
# We'll rely on the fact that U.waves/alpha.waves are set up for the HULL case which has bottom as WALL (type patch).
# So making the wave_tank bottom a 'patch' makes it consistent.

# Ensure bottom/sides match properties (U.waves uses slip for bottom?)
# U.waves uses 'waveVelocity' for inlet.
# Check boundary names: blockMesh uses 'inlet', 'outlet', 'bottom', 'top', 'side_right', 'side_left'.
# This matches U.waves.

echo "Running BlockMesh..."
./scripts/utils/run_openfoam_docker.sh blockMesh -case $CASE_DIR

echo "Running SetFields..."
# We need system/setFieldsDict. wave_tank template might not have it or have a default.
# We'll copy from hull but remove hull-specific logic if any.
# Create valid setFieldsDict with header
cat <<EOF > $CASE_DIR/system/setFieldsDict
/*--------------------------------*- C++ -*----------------------------------*\\
  =========                 |
  \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \\\\    /   O peration     | Website:  www.openfoam.com
    \\\\  /    A nd           |
     \\\\/     M anipulation  |
\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      setFieldsDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

defaultFieldValues
(
    volScalarFieldValue alpha.water 0
);

regions
(
    boxToCell
    {
        box ( -100 -150 -10 ) ( 400 150 1.42 );
        fieldValues
        (
            volScalarFieldValue alpha.water 1
        );
    }
);
// ************************************************************************* //
EOF
# Patch 0/p_rgh if it exists (it comes from wave_tank template)
# It likely has 'type symmetryPlane' for bottom. We need 'type fixedFluxPressure' or 'zeroGradient'.
if [ -f $CASE_DIR/0/p_rgh ]; then
    # Change bottom from symmetryPlane to fixedFluxPressure (or zeroGradient)
    # We replaced blockMesh bottom to 'patch'.
    # We must ensure the p_rgh definition is compatible with 'patch'.
    # A simple way is to replace the whole entry or just the type.
    # Assuming standard formatting, looking for "bottom { ... type symmetryPlane; ... }" might be hard with sed.
    # But usually "bottom" is followed by "type ...".
    # Let's just blindly replace "type symmetryPlane" with "type zeroGradient" for the bottom patch? 
    # No, that might affect sides.
    # The sides ARE symmetryPlane. We don't want to change them.
    # We only changed 'bottom' to patch in blockMeshDict.
    
    # Let's use a more robust approach: foamDictionary or specific sed.
    # Or... since this is a verification script, just write the p_rgh file explicitly like we did for blockMesh.
    # That is the safest.
    cat <<EOF > $CASE_DIR/0/p_rgh
/*--------------------------------*- C++ -*----------------------------------*\\
  =========                 |
  \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \\\\    /   O peration     | Website:  www.openfoam.com
    \\\\  /    A nd           |
     \\\\/     M anipulation  |
\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    object      p_rgh;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [1 -1 -2 0 0 0 0];

internalField   uniform 0;

boundaryField
{
    inlet
    {
        type            fixedFluxPressure;
        value           uniform 0;
    }
    outlet
    {
        type            fixedFluxPressure;
        value           uniform 0;
    }
    bottom
    {
        type            fixedFluxPressure;
        value           uniform 0;
    }
    top
    {
        type            totalPressure;
        p0              uniform 0;
    }
    side_right
    {
        type            symmetryPlane;
    }
    side_left
    {
        type            symmetryPlane;
    }
}

// ************************************************************************* //
EOF
fi

# Force LAMINAR flow to avoid k/omega/nut boundary issues with the custom mesh
cat <<EOF > $CASE_DIR/constant/turbulenceProperties
/*--------------------------------*- C++ -*----------------------------------*\\
  =========                 |
  \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \\\\    /   O peration     | Website:  www.openfoam.com
    \\\\  /    A nd           |
     \\\\/     M anipulation  |
\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      turbulenceProperties;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

simulationType  laminar;

// ************************************************************************* //
EOF

./scripts/utils/run_openfoam_docker.sh setFields -case $CASE_DIR

echo "Running InterFoam (Serial)..."
# We run serial for simplicity and speed of setup (no decompose).
# But we might need parallel for speed of execution? 
# 200*20*60 = 240,000 cells. Serial is fine.
./scripts/utils/run_openfoam_docker.sh interFoam -case $CASE_DIR > $CASE_DIR/log.interFoam

echo "Done. Check $CASE_DIR/log.interFoam"
