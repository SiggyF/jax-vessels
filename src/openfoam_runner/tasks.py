import subprocess
import time
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

def run_command(cmd, cwd=None):
    logger.info(f"Running: {cmd} in {cwd}")
    subprocess.check_call(cmd, shell=True, cwd=cwd)

def setup_case_task(hull_stl: Path, case_dir: Path):
    """
    Sets up the OpenFOAM case directory.
    """
    case_dir.mkdir(parents=True, exist_ok=True)
    
    # Locate templates relative to project root or package
    # Assuming /app structure or current working directory has templates
    template_src = Path("templates/base_case").resolve()
    
    if not template_src.exists():
         # Fallback try relative to file
         template_src = Path(__file__).parent.parent.parent / "templates" / "base_case"
         
    if not template_src.exists():
        raise FileNotFoundError(f"Template directory not found at {template_src}")

    # Copy template files
    run_command(f"cp -r {template_src}/* {case_dir}/")

    (case_dir / "constant" / "triSurface").mkdir(parents=True, exist_ok=True)
    if hull_stl.exists():
        run_command(f"cp {hull_stl} {case_dir}/constant/triSurface/hull.stl")
    return case_dir

def run_meshing_task(case_dir: Path):
    """
    Runs the meshing pipeline.
    """
    if not shutil.which("blockMesh"):
        raise EnvironmentError("blockMesh not found")
    
    run_command("blockMesh", cwd=case_dir)
    
    # Optional: surfaceFeatureExtract and snappyHexMesh check
    if (case_dir / "system" / "snappyHexMeshDict").exists():
        if not shutil.which("snappyHexMesh"):
             raise EnvironmentError("snappyHexMesh not found")
        
        run_command("surfaceFeatureExtract", cwd=case_dir)
        run_command("snappyHexMesh -overwrite", cwd=case_dir)
    
    return case_dir

def run_set_fields_task(case_dir: Path):
    """
    Initialize fields (e.g. water level).
    """
    if not shutil.which("setFields"):
         raise EnvironmentError("setFields not found")

    run_command("setFields", cwd=case_dir)
    return case_dir

def run_simulation_task(case_dir: Path):
    """
    Runs the simulation solver.
    """
    if not shutil.which("interFoam"):
        raise EnvironmentError("interFoam not found")

    run_command("interFoam", cwd=case_dir)
    return case_dir

def run_post_processing_task(case_dir: Path):
    """
    Runs post-processing (VTK conversion).
    """
    if not shutil.which("foamToVTK"):
        raise EnvironmentError("foamToVTK not found")

    run_command("foamToVTK", cwd=case_dir)
    return case_dir

def extract_parameters_task(case_dir: Path):
    """
    Parses simulation results.
    """
    # TODO: Parse actual results logic
    return {
        "status": "completed",
        "case": str(case_dir.name)
    }
