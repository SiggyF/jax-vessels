#!/bin/bash
set -e

# Defaults
TEMPLATE="templates/base_case"
IMAGE="opencfd/openfoam-default:latest"
HULL=""
OUT=""

# Usage
usage() {
    echo "Usage: $0 --hull <path_to_stl> --out <output_dir> [--template <path>] [--image <docker_image>]"
    exit 1
}

# Parse Args
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --hull) HULL="$2"; shift ;;
        --out) OUT="$2"; shift ;;
        --template) TEMPLATE="$2"; shift ;;
        --image) IMAGE="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; usage ;;
    esac
    shift
done

if [ -z "$HULL" ] || [ -z "$OUT" ]; then
    echo "Error: --hull and --out are required."
    usage
fi

# Convert paths to absolute
HULL=$(realpath "$HULL")
OUT=$(realpath "$OUT")
TEMPLATE=$(realpath "$TEMPLATE")

echo "-------------------------------------------------------"
echo "Starting OpenFOAM Simulation (Docker)"
echo "Hull:     $HULL"
echo "Output:   $OUT"
echo "Template: $TEMPLATE"
echo "Image:    $IMAGE"
echo "-------------------------------------------------------"

# 1. Setup Run Directory
if [ -d "$OUT" ]; then
    echo "Output directory exists. Updating..."
else
    mkdir -p "$OUT"
fi

# Copy template content to output (using cp -R)
# Trailing slash importance: we want contents of template in OUT
cp -R "$TEMPLATE/" "$OUT/"

# 2. Setup Hull
mkdir -p "$OUT/constant/triSurface"
cp "$HULL" "$OUT/constant/triSurface/hull.stl"
echo "Copied hull.stl to relevant directory."

# 3. Docker Command
# Explicitly force entry to /data and use pipefail
CMDS="set -o pipefail && \
cd /data && \
blockMesh | tee log.blockMesh && \
surfaceFeatureExtract | tee log.surfaceFeatureExtract && \
snappyHexMesh -overwrite | tee log.snappyHexMesh && \
checkMesh | tee log.checkMesh"
# interFoam | tee log.interFoam (Excluded for fast check)

echo "Running Docker container..."
docker run --rm \
    -v "$OUT":/data \
    "$IMAGE" \
    /bin/bash -c "$CMDS"

echo "-------------------------------------------------------"
if [ $? -eq 0 ]; then
    echo "Simulation (Meshing) Completed Successfully."
else
    echo "Simulation Failed."
    exit 1
fi
