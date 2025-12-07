import os
import subprocess
import time
import click
from pathlib import Path
from dask.distributed import Client, progress, LocalCluster
from dask import delayed
import dask
from tqdm import tqdm

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

@click.command()
@click.argument("hull_stls", nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option("--out-dir", type=click.Path(path_type=Path), default=Path("analysis_runs"), help="Base directory for analysis runs")
@click.option("--parallel/--no-parallel", default=True, help="Run in parallel using Dask")
def main(hull_stls, out_dir, parallel):
    """
    Run OpenFOAM analysis on multiple hull STL files.
    """
    if not hull_stls:
        click.echo("No hull files provided.")
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    if parallel:
        cluster = LocalCluster()
        client = Client(cluster)
        click.echo(f"Dask dashboard avaliable at: {client.dashboard_link}")
    
    tasks = []
    
    click.echo(f"Processing {len(hull_stls)} hulls...")
    
    for i, hull_stl in enumerate(hull_stls):
        case_dir = out_dir / f"case_{hull_stl.stem}_{i}"
        
        # Define pipeline using Dask delayed or direct submission
        if parallel:
            # Using simple delayed workflow
            setup = delayed(setup_case_task)(hull_stl, case_dir)
            mesh = delayed(run_meshing_task)(setup)
            sim = delayed(run_simulation_task)(mesh)
            params = delayed(extract_parameters_task)(sim)
            tasks.append(params)
        else:
            # Sequential execution
            setup_case_task(hull_stl, case_dir)
            run_meshing_task(case_dir)
            run_simulation_task(case_dir)
            params = extract_parameters_task(case_dir)
            click.echo(f"Result for {hull_stl.name}: {params}")

    if parallel:
        # Compute all tasks
        click.echo("Submitting tasks to Dask cluster...")
        results = dask.compute(*tasks)
        
        # If we wanted to use tqdm with futures, we could stick to client.map/submit and as_completed
        # But dask.compute is simple. 
        # For explicit progress bar with dask delayed:
        from dask.diagnostics import ProgressBar
        with ProgressBar():
             results = dask.compute(*tasks)

        for i, res in enumerate(results):
             click.echo(f"Result for {hull_stls[i].name}: {res}")

if __name__ == "__main__":
    main()

