import subprocess
import time
from pathlib import Path

def run_command(cmd, cwd=None):
    # print(f"Running: {cmd}") # Verbose
    subprocess.check_call(cmd, shell=True, cwd=cwd)

def setup_case_task(hull_stl: Path, case_dir: Path):
    """
    Sets up the OpenFOAM case directory.
    """
    (case_dir / "constant" / "triSurface").mkdir(parents=True, exist_ok=True)
    # Mocking copy for now if file doesn't exist
    if hull_stl.exists():
        run_command(f"cp {hull_stl} {case_dir}/constant/triSurface/hull.stl")
    return case_dir

def run_meshing_task(case_dir: Path):
    """
    Runs the meshing pipeline.
    """
    # run_command("blockMesh", cwd=case_dir)
    # run_command("surfaceFeatureExtract", cwd=case_dir)
    # run_command("snappyHexMesh -overwrite", cwd=case_dir)
    time.sleep(1) # Simulate work
    return case_dir

def run_simulation_task(case_dir: Path):
    """
    Runs the simulation solver.
    """
    # run_command("potentialFoam", cwd=case_dir)
    time.sleep(2) # Simulate work
    return case_dir

def extract_parameters_task(case_dir: Path):
    """
    Parses simulation results.
    """
    # TODO: Parse actual results
    return {
        "M": [[1000, 0, 0], [0, 1200, 0], [0, 0, 1500]], 
        "D": [[10, 0, 0], [0, 20, 0], [0, 0, 30]]
    }
