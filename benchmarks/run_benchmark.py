import click
import subprocess
import re
import json
import statistics
from datetime import datetime, timezone
import time
import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def parse_log_execution_time(log_path: Path):
    """Parses OpenFOAM logs for ExecutionTime lines."""
    if not log_path.exists():
        logger.warning(f"Log file not found: {log_path}")
        return None
    
    times = []
    with log_path.open('r') as f:
        for line in f:
            # Match "ExecutionTime = 12.34 s"
            match = re.search(r"ExecutionTime = ([\d\.]+) s", line)
            if match:
                times.append(float(match.group(1)))
    return times

def extract_mesh_stats(log_path: Path):
    """Parses snappyHexMesh log for cell count."""
    if not log_path.exists():
        logger.warning(f"Log file not found: {log_path}")
        return None
    
    stats = {}
    with log_path.open('r') as f:
        content = f.read()
        # Find final cell count
        # "cells: 123456"
        cells_match = re.findall(r"cells:(\s+)(\d+)", content)
        if cells_match:
            stats['cell_count'] = int(cells_match[-1][1])
            
    return stats

def get_simulated_time(log_path: Path):
    """Parses OpenFOAM log for the final simulation time."""
    if not log_path.exists():
        return 0.0
    
    last_time = 0.0
    with log_path.open('r') as f:
        for line in f:
            # Match "Time = 0.5"
            match = re.match(r"^Time = ([\d\.]+)", line)
            if match:
                last_time = float(match.group(1))
    return last_time

def run_benchmark(case_name: str, runs: int = 1):
    timestamp = datetime.now(timezone.utc).isoformat()
    results = {
        'timestamp': timestamp,
        'case': case_name,
        'runs': []
    }
    
    cmd = ["bash", "scripts/run_docker.sh", "bash", "scripts/verify_case.sh", case_name]
    
    logger.info(f"Starting Benchmark for '{case_name}' ({runs} runs)...")
    
    for i in range(runs):
        logger.info(f"--- Run {i+1}/{runs} ---")
        start_time = time.time() # time.time() is best for elapsed duration
        
        # Run the simulation via Docker wrapper
        subprocess.run(cmd, check=True)
            
        wall_time = time.time() - start_time
        
        # Analyze Logs
        run_data = {
            'run_id': i+1,
            'wall_time_total': wall_time
        }
        
        # Path to logs (mounted volume results)
        run_dir = Path(f"verification_run/{case_name}")
        
        # 1. Mesh Stats
        mesh_log = run_dir / "log.snappyHexMesh"
        mesh_stats = extract_mesh_stats(mesh_log)
        if mesh_stats:
            run_data.update(mesh_stats)
            
        # 2. Solver Performance
        solve_log = run_dir / "log.interFoam"
        exec_times = parse_log_execution_time(solve_log)
        sim_time = get_simulated_time(solve_log)
        
        if exec_times and len(exec_times) > 1:
            # Calculate time per step (excluding startup overhead in first step)
            # Diffs between cumulative execution times
            steps = []
            for j in range(1, len(exec_times)):
                dt = exec_times[j] - exec_times[j-1]
                steps.append(dt)
            
            run_data['steps_computed'] = len(steps)
            run_data['avg_time_per_step'] = statistics.mean(steps) if steps else 0.0
            run_data['total_solver_time'] = exec_times[-1]
        
        # Real Time Factor
        if sim_time > 0 and wall_time > 0:
            rtf = sim_time / wall_time
            run_data['simulated_time'] = sim_time
            run_data['real_time_factor'] = rtf
            
        results['runs'].append(run_data)
        
        logger.info(f"  > Wall Time: {wall_time:.2f}s")
        if 'cell_count' in run_data:
            logger.info(f"  > Cells: {run_data['cell_count']}")
        if 'real_time_factor' in run_data:
             logger.info(f"  > speed: {run_data['real_time_factor']:.4f}x real-time ({1.0/run_data['real_time_factor']:.1f}s/sim-sec)")

    # Aggregate
    if results['runs']:
        avg_step = statistics.mean([r.get('avg_time_per_step', 0) for r in results['runs']])
        avg_rtf = statistics.mean([r.get('real_time_factor', 0) for r in results['runs']])
        logger.info(f"Benchmark Complete. Avg Time/Step: {avg_step:.4f}s. Speed: {avg_rtf:.4f}x")
        
        # Save results
        results_dir = Path("benchmarks")
        results_dir.mkdir(exist_ok=True)
        
        # Use datetime for filename
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = results_dir / f"results_{case_name}_{date_str}.json"
        
        with out_file.open('w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Saved results to {out_file}")

@click.command()
@click.option("--case", default="kcs_hull", help="Case name to benchmark")
@click.option("--runs", default=1, type=int, help="Number of repetitions")
def main(case, runs):
    """Run OpenFOAM Benchmark."""
    run_benchmark(case, runs)

if __name__ == "__main__":
    main()
