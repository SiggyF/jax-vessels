import click
import logging
import re
from pathlib import Path
import sys

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

@click.command()
@click.argument("case_dir", type=click.Path(exists=True, path_type=Path))
@click.option("--max-courant", default=1.0, help="Maximum allowable Courant number")
@click.option("--min-dt", default=1e-4, help="Minimum allowable timestep")
@click.option("--max-velocity", default=50.0, help="Maximum allowable velocity magnitude (Global)")
@click.option("--max-velocity-hull", default=20.0, help="Maximum allowable velocity magnitude (Hull)")
@click.option("--output", required=True, type=click.Path(path_type=Path), help="Output JSON report")
def verify(case_dir, max_courant, min_dt, max_velocity, max_velocity_hull, output):
    """Verifies OpenFOAM simulation logs for stability and physical checks."""
    import json
    
    log_file = case_dir / "log.interFoam"
    if not log_file.exists():
        logger.error(f"Log file not found: {log_file}")
        sys.exit(1)

    logger.info(f"Verifying {case_dir}...")
    
    issues = []
    
    # regex patterns
    re_courant = re.compile(r"Courant Number mean: .+ max: ([\d\.eE\+\-]+)")
    re_dt = re.compile(r"deltaT = ([\d\.eE\+\-]+)")
    # "fieldMinMax minMaxU output: min = 0 max = 1.234"
    re_minmax_u_mag = re.compile(r"fieldMinMax minMaxU output:.*max = ([\d\.eE\+\-]+)")
    
    # surfaceFieldValue maxU_Hull
    re_hull_u = re.compile(r"surfaceFieldValue maxU_Hull output:.*max\(U\) = \(([\d\.eE\+\-]+)\s+([\d\.eE\+\-]+)\s+([\d\.eE\+\-]+)\)")

    # Tracking max values encountered
    peak_courant = 0.0
    min_encountered_dt = 1.0
    peak_u_global = 0.0
    peak_u_hull = 0.0

    with open(log_file, 'r') as f:
        for line in f:
            # Courant
            m = re_courant.search(line)
            if m:
                c = float(m.group(1))
                peak_courant = max(peak_courant, c)

            # DeltaT
            m = re_dt.search(line)
            if m:
                dt = float(m.group(1))
                min_encountered_dt = min(min_encountered_dt, dt)

            # Global U
            m = re_minmax_u_mag.search(line)
            if m:
                u_mag = float(m.group(1))
                peak_u_global = max(peak_u_global, u_mag)

            # Hull U
            m = re_hull_u.search(line)
            if m:
                vx, vy, vz = float(m.group(1)), float(m.group(2)), float(m.group(3))
                mag = (vx**2 + vy**2 + vz**2)**0.5
                peak_u_hull = max(peak_u_hull, mag)

    # Check against limits
    if peak_courant > max_courant:
        issues.append(f"Max Courant {peak_courant:.2f} exceeded limit {max_courant}")
    
    if min_encountered_dt < min_dt:
        issues.append(f"Min timestep {min_encountered_dt} below limit {min_dt}")

    if peak_u_global > max_velocity:
        issues.append(f"Max Global Velocity {peak_u_global:.2f} exceeded limit {max_velocity}")
        
    if peak_u_hull > max_velocity_hull:
        issues.append(f"Max Hull Velocity {peak_u_hull:.2f} exceeded limit {max_velocity_hull}")

    # Summary
    logger.info("-" * 40)
    logger.info(f"Peak Courant: {peak_courant:.2f}")
    logger.info(f"Min DeltaT:   {min_encountered_dt:.2e}")
    logger.info(f"Peak U (Glob):{peak_u_global:.2f}")
    logger.info(f"Peak U (Hull):{peak_u_hull:.2f}")
    logger.info("-" * 40)

    report_data = {
        "case_dir": str(case_dir),
        "metrics": {
            "peak_courant": peak_courant,
            "min_delta_t": min_encountered_dt,
            "peak_u_global": peak_u_global,
            "peak_u_hull": peak_u_hull
        },
        "limits": {
            "max_courant": max_courant,
            "min_dt": min_dt,
            "max_velocity": max_velocity,
            "max_velocity_hull": max_velocity_hull
        },
        "issues": issues,
        "status": "FAILED" if issues else "PASSED"
    }

    with open(output, 'w') as f:
        json.dump(report_data, f, indent=2)

    if issues:
        logger.error("Verification FAILED:")
        for i in issues:
            logger.error(f"  - {i}")
        # We exit with 0 to allow Snakemake to proceed if we want to record the failure in the report,
        # but usually verification failure should stop the pipeline or be handled.
        # For now, let's exit with 1 if it fails to ensure we notice.
        sys.exit(1)
    else:
        logger.info("Verification PASSED")

if __name__ == "__main__":
    verify()
