import click
import shutil
import subprocess
import os
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

IMAGE_NAME = "opencfd/openfoam-default:latest"

@click.command()
@click.option("--hull", type=click.Path(exists=True, path_type=Path), required=True, help="Path to input Hull STL file")
@click.option("--out", type=click.Path(path_type=Path), required=True, help="Output simulation directory")
@click.option("--template", type=click.Path(exists=True, path_type=Path), default="templates/base_case", help="Path to base case template")
@click.option("--image", default=IMAGE_NAME, help="Docker image to use")
def main(hull, out, template, image):
    """
    Run an OpenFOAM simulation using Docker.
    
    1. Sets up the run directory (copies template).
    2. Copies hull STL to constant/triSurface/.
    3. Runs OpenFOAM commands in Docker container.
    """
    hull = hull.resolve()
    out = out.resolve()
    template = template.resolve()
    
    if out.exists():
        logger.warning(f"Output directory {out} already exists. Overwriting/Updating...")
        # Optional: shutil.rmtree(out)
    else:
        out.mkdir(parents=True)
        
    # 1. Copy Template
    logger.info(f"Copying template from {template} to {out}")
    # We use dirs_exist_ok=True to allow updating
    shutil.copytree(template, out, dirs_exist_ok=True)
    
    # 2. Setup Hull
    tri_surf_dir = out / "constant" / "triSurface"
    tri_surf_dir.mkdir(parents=True, exist_ok=True)
    
    dest_hull = tri_surf_dir / "hull.stl"
    logger.info(f"Copying hull from {hull} to {dest_hull}")
    shutil.copy(hull, dest_hull)
    
    # 3. Docker Command Construction
    # We mount 'out' to '/data' inside container
    
    # OpenFOAM commands to run
    # Source /usr/lib/openfoam/openfoam.../etc/bashrc is usually done by entrypoint in this image.
    # But usually creating a run script is safer.
    
    commands = [
        "blockMesh | tee log.blockMesh",
        "surfaceFeatureExtract | tee log.surfaceFeatureExtract",
        "snappyHexMesh -overwrite | tee log.snappyHexMesh",
        "checkMesh | tee log.checkMesh",
        # "interFoam | tee log.interFoam" # Comment out solver for now, fast check
    ]
    
    # Chain commands
    cmd_string = " && ".join(commands)
    
    # Docker run arguments
    # -u 0 is root, might be needed if permission issues, but typical user is usually 'openfoam' (uid 1000).
    # If out dir is owned by us (uid 501 on mac), we might have permission issues writing from container (uid 1000).
    # Mac Docker file sharing usually handles this gracefully, but let's watch out.
    
    docker_args = [
        "docker", "run", "--rm",
        "-v", f"{out}:/data",
        "-w", "/data",
        image,
        "/bin/bash", "-c", cmd_string
    ]
    
    logger.info(f"Running Docker command: {' '.join(docker_args)}")
    
    try:
        subprocess.run(docker_args, check=True)
        logger.info("Simulation (meshing) completed successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Docker command failed with exit code {e.returncode}")
        exit(e.returncode)

if __name__ == "__main__":
    main()
