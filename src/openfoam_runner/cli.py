import click
import logging
from pathlib import Path
from dask.distributed import Client, LocalCluster
from dask import delayed
import dask
from .tasks import setup_case_task, run_meshing_task, run_set_fields_task, run_simulation_task, run_post_processing_task, extract_parameters_task

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    
    logger.info(f"Processing {len(hull_stls)} hulls...")
    
    for i, hull_stl in enumerate(hull_stls):
        case_dir = out_dir / f"case_{hull_stl.stem}_{i}"
        
        # Define pipeline using Dask delayed or direct submission
        if parallel:
            # Using simple delayed workflow
            setup = delayed(setup_case_task)(hull_stl, case_dir)
            mesh = delayed(run_meshing_task)(setup)
            fields = delayed(run_set_fields_task)(mesh)
            sim = delayed(run_simulation_task)(fields)
            post = delayed(run_post_processing_task)(sim)
            params = delayed(extract_parameters_task)(post)
            tasks.append(params)
        else:
            # Sequential execution
            setup_case_task(hull_stl, case_dir)
            run_meshing_task(case_dir)
            run_set_fields_task(case_dir)
            run_simulation_task(case_dir)
            run_post_processing_task(case_dir)
            params = extract_parameters_task(case_dir)
            logger.info(f"Result for {hull_stl.name}: {params}")

    if parallel and tasks:
        # Compute all tasks
        logger.info("Submitting tasks to Dask cluster...")
        results = dask.compute(*tasks)

        for i, res in enumerate(results):
             logger.info(f"Result for {hull_stls[i].name}: {res}")

if __name__ == "__main__":
    main()
