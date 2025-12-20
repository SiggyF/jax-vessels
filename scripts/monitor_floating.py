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
    pass
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import re

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_log_file(logfile: Path):
    """
    Parses OpenFOAM log file for 6DoF motion state.
    Looks for:
    Time = 0.5
    ...
    6-DoF rigid body motion
        Centre of mass: (x y z)
    """
    times = []
    heaves = []
    pitches = [] # Not parsing pitch yet, placeholder
    
    current_time = 0.0
    
    try:
        with open(logfile, 'r') as f:
            for line in f:
                # Time = 0.123
                if line.startswith("Time ="):
                    try:
                        current_time = float(line.split("=")[1].strip())
                    except ValueError:
                        pass
                
                # Centre of mass: (67.5 0 2.2)
                if "Centre of mass:" in line:
                    # Regex to extract (x y z)
                    match = re.search(r'\(([\d\.\-eE]+)\s+([\d\.\-eE]+)\s+([\d\.\-eE]+)\)', line)
                    if match:
                        z = float(match.group(3))
                        times.append(current_time)
                        heaves.append(z)
                        pitches.append(0.0)
                        
    except Exception as e:
        logger.error(f"Failed to parse log file {logfile}: {e}")
        
    return times, heaves, pitches

def update(frame): # Frame arg is dummy
    log_file = CASE_DIR / "log.interFoam"
    if not log_file.exists():
        logger.warning(f"Log file not found: {log_file}")
        return line_heave, line_pitch
        
    times, heaves, pitches = parse_log_file(log_file)
    
    # Sort by time
    if times:
        # No need to sort if parsed sequentially, but good practice if multiple logs
        # Here we just assume sequential from one log
        
        logger.info(f"Found {len(times)} data points. Last: t={times[-1]:.2f}, Z={heaves[-1]:.2f}")
        
        line_heave.set_data(times, heaves)
        line_pitch.set_data(times, pitches)
        
        ax[0].relim()
        ax[0].autoscale_view()
        ax[1].relim()
        ax[1].autoscale_view()
        
        ax[0].set_title(f"Heave vs Time (t={times[-1]:.2f}s)")
    else:
        logger.warning("No data points found in log!")
    
    return line_heave, line_pitch

def parse_state_file(filepath: Path):
    """
    Parses a sixDoFRigidBodyMotionState file to extract the Centre of Mass (CoM) position.
    Format example:
    (
        (67.5 0 2)
        (1 0 0 0 1 0 0 0 1)
        (0 0 0)
        (0 0 0)
        (0 0 0)
        (0 0 0)
    )
    We want the Z component of the first vector (position).
    """
    try:
        content = filepath.read_text()
        # Find the first vector inside the outer parens
        # This regex looks for: ( x y z )
        match = re.search(r'\(\s*([\d\.\-eE]+)\s+([\d\.\-eE]+)\s+([\d\.\-eE]+)\s*\)', content)
        if match:
            z = float(match.group(3))
            return z
    except Exception as e:
        logger.error(f"Failed to parse {filepath}: {e}")
    return None
def monitor(case_dir: Path, output: Path = None):
    """
    Monitors processor0 directories for uniform/sixDoFRigidBodyMotionState
    """
    proc0 = case_dir / "processor0"
    

    global CASE_DIR, fig, ax, line_heave, line_pitch
    CASE_DIR = case_dir
    
    fig, ax = plt.subplots(3, 1, figsize=(10, 12), sharex=True)
    
    # Heave
    line_heave, = ax[0].plot([], [], 'b-', label='Heave (Z)')
    ax[0].set_ylabel('Position Z [m]')
    ax[0].grid(True)
    ax[0].legend()
    
    # Annotations for "Container Loading"
    # Staged simulation: Load added at t=0.5s
    ax[0].axvline(x=0.5, color='k', linestyle='--', alpha=0.5)
    ax[0].text(0.52, 0.95, 'Container Loaded (t=0.5s)', transform=ax[0].transAxes, verticalalignment='top')
    ax[0].text(0.25, 0.1, 'Stability Check', transform=ax[0].transAxes, horizontalalignment='center')
    ax[0].text(0.75, 0.1, 'Settling Phase', transform=ax[0].transAxes, horizontalalignment='center')

    
    # Pitch
    line_pitch, = ax[1].plot([], [], 'r-', label='Pitch (deg)')
    ax[1].set_ylabel('Pitch [deg]')
    ax[1].grid(True)
    ax[1].legend()

    # Draft (Derived)
    # Draft = WaterLevel(1.42) - Keel_Z
    # Keel_Z = CoM_Z - 2.0 (Approx)
    # Draft = 1.42 - (z - 2.0) = 3.42 - z
    # In future, read WaterLevel from args
    
    # Parse data for Draft plot
    log_file = CASE_DIR / "log.interFoam"
    times_d, heaves_d, _ = parse_log_file(log_file)
    
    if len(heaves_d) > 0:
        drafts = [3.42 - z for z in heaves_d]
        ax[2].plot(times_d, drafts, 'g-', label='Draft (m)')
        ax[2].set_ylabel('Draft [m]')
        ax[2].set_ylim(1.0, 1.6) # Focus around 1.30
        ax[2].axhline(y=1.30, color='k', linestyle='--', alpha=0.5, label='Target (1.30)')
        ax[2].legend()
    else:
        logger.warning("No data for Draft plot")

    ax[2].set_xlabel('Time [s]')
    ax[2].grid(True)

    if output:
        # Static plot for non-interactive mode
        # We need to manually call update once with a dummy frame or just run logic
        update(0)
        logger.info(f"Saving plot to {output}")
        plt.savefig(output)
    else:
        ani = FuncAnimation(fig, update, interval=1000, blit=True) # Check every 1s
        plt.show()

@click.command()
@click.argument("case_dir", type=click.Path(exists=True, path_type=Path))
@click.option("--output", type=click.Path(path_type=Path), default=None, help="Path to save the plot image")
def main(case_dir, output):
    """Monitor the simulation progress."""
    logger.info(f"Monitoring {case_dir}...")
    monitor(case_dir, output=output)

if __name__ == "__main__":
    main()

