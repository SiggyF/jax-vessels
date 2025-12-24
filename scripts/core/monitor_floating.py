import sys
import time
import click
import logging
from pathlib import Path
import matplotlib
# Force interactive backend if available, otherwise fallback is often Agg
try:
    matplotlib.use('MacOSX') 
except:
    matplotlib.use('Agg') # Fallback if no display
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import re

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_log_file(case_dir: Path):
    """
    Parses log.interFoam for 6DoF motion data (fallback if postProcessing is missing).
    Extracts: Time, Centre of mass (Z component for heave).
    """
    log_path = case_dir / "log.interFoam"
    times = []
    heaves = []
    
    if not log_path.exists():
        return [], [], [] # format match

    current_time = None
    
    # Simple state machine parser
    # Time = 0.5
    # ...
    # Centre of mass: (x y z)
    
    try:
        with open(log_path, 'r') as f:
            for line in f:
                if line.startswith("Time ="):
                    try:
                        current_time = float(line.split("=")[1].strip())
                    except:
                        pass
                
                if "Centre of mass:" in line and current_time is not None:
                    # Centre of mass: (3.18086e-05 0 -1.61063)
                    try:
                        # Clean brackets
                        clean = line.split(":")[1].strip().replace('(', '').replace(')', '')
                        parts = clean.split()
                        if len(parts) == 3:
                            z = float(parts[2])
                            times.append(current_time)
                            heaves.append(z)
                    except:
                        pass
    except Exception as e:
        logger.warning(f"Error parsing log file: {e}")
        
    # Return dummy rotations for now as we focus on Heave
    return times, [[0,0,h] for h in heaves], rotations

def save_csv(case_dir: Path, times, positions, rotations):
    """Saves parsed 6DoF data to CSV."""
    import csv
    import math
    
    csv_path = case_dir / "6dof.csv"
    
    # Do not append, write fresh every time to avoid duplicates or use append if careful.
    # Since we parse the whole log every time (inefficient but simple), we overwrite.
    
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Time", "CoM_X", "CoM_Y", "CoM_Z", "Pitch_deg", "Roll_deg", "Yaw_deg"])
        
        for i, t in enumerate(times):
            pos = positions[i]
            rot = rotations[i]
            
            # Extract basic orientation
            # Assuming rot is flattened row-major 3x3
            # Pitch = -asin(R[6])
            try:
                pitch = math.degrees(math.asin(max(-1.0, min(1.0, -rot[6])))) if hasattr(rot, '__getitem__') and len(rot) > 6 else 0.0
            except:
                pitch = 0.0
            
            writer.writerow([t, pos[0], pos[1], pos[2], pitch, 0.0, 0.0])

def update(frame, case_dir, output, auto_exit):
    log_file = case_dir / "log.interFoam"
    
    times, positions, rotations = parse_sixdof_dat(case_dir)
    
    # Save to CSV
    if times:
        save_csv(case_dir, times, positions, rotations)
    
    heaves = [p[2] for p in positions]
    # Simple pitch approx: -asin(R[6]) ? (Element 3,1 in 1-based, index 6 in 0-based row-major 0,1,2, 3,4,5, 6,7,8)
    # OpenFOAM tensor output is Row-Major? ((xx xy xz) (yx yy yz) (zx zy zz)) -> 9 values
    # Pitch (theta) in aerospace sequence (ZYX): sin(theta) = -R_31 (index 2,0 -> index 6 if flattened row-major?)
    # or R_13 depending on definition. Assuming standard:
    # Let's just use rotation[6] (zx) or similar for plotting. 
    # Actually, Rerun handles full 3D, so we trust Rerun.
    # For 2D plot, we can just assume 0 or try to parse.
    # We'll use 0.0 for 2D plot pitch to avoid confusion if math is unsure, 
    # but since user has Rerun 3D, the 2D plot is secondary.
    # Let's try to extract relevant component for "Pitch" (usually rotation around Y).
    # R31 = -sin(theta). theta = -asin(R31).
    # If rot is (r0 r1 r2 r3 r4 r5 r6 r7 r8), R31 is r6.
    import math
    pitches = []
    for r in rotations:
         # Clamp for asin domain
         if hasattr(r, '__getitem__') and len(r) > 6:
             val = -r[6]
             val = max(-1.0, min(1.0, val))
             pitches.append(math.degrees(math.asin(val)))
         else:
             pitches.append(0.0)

    if not times:
        if not log_file.exists():
             logger.warning("Waiting for simulation to start...")
        else:
             logger.warning("No 6DoF data yet.")
        return line_heave, line_pitch
    
    # Update Matplotlib (Legacy/Report)
    line_heave.set_data(times, heaves)
    line_pitch.set_data(times, pitches)
    ax[0].relim()
    ax[0].autoscale_view()
    ax[1].relim()
    ax[1].autoscale_view()
    ax[0].set_title(f"Heave vs Time (t={times[-1]:.2f}s)")
    if output:
        plt.savefig(output)

    return line_heave, line_pitch

def monitor(case_dir: Path, output: Path = None, auto_exit: bool = False):
    """
    Monitors simulation using postProcessing data.
    """
    logger.info(f"Monitoring case: {case_dir}")
    
    global fig, ax, line_heave, line_pitch
    fig, ax = plt.subplots(2, 1, figsize=(10, 8))
    line_heave, = ax[0].plot([], [], 'b-', label='Heave (Z)')
    ax[0].set_ylabel('Position Z [m]')
    ax[0].grid(True)
    line_pitch, = ax[1].plot([], [], 'r-', label='Pitch (deg)')
    ax[1].set_ylabel('Pitch [deg]')
    ax[1].set_xlabel('Time [s]')
    ax[1].grid(True)

    def update_wrapper(frame):
        return update(frame, case_dir, output, auto_exit)

    if auto_exit:
        logger.info("Running in background loop...")
        while True:
            update(0, case_dir, output, auto_exit)
            time.sleep(2)
    else:
        # Interactive
        ani = FuncAnimation(fig, update_wrapper, interval=1000, blit=False)
        plt.show()

@click.command()
@click.argument("case_dir", type=click.Path(exists=True, path_type=Path))
@click.option("--output", type=click.Path(path_type=Path), default=None, help="Path to save the plot image")
@click.option("--auto-exit", is_flag=True, help="Run in non-interactive background mode")
def main(case_dir, output, auto_exit):
    """Monitor simulation charts."""
    monitor(case_dir, output=output, auto_exit=auto_exit)

if __name__ == "__main__":
    main()
