import sys
import time
import argparse
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

def update(frame):
    # Scan all processor directories
    # processor*/0.05/uniform/sixDoFRigidBodyMotionState
    # sort by time
    
    times = []
    heaves = []
    pitches = []
    
    # Iterate over all processor* directories
    for proc_dir in CASE_DIR.glob("processor*"):
        # Look for time directories inside
        for time_dir in proc_dir.iterdir():
            if not time_dir.is_dir(): continue
            try:
                t = float(time_dir.name)
            except ValueError:
                continue
                
            state_file = time_dir / "uniform/sixDoFRigidBodyMotionState"
            if state_file.exists():
                z_val = parse_state_file(state_file)
                if z_val is not None:
                    times.append(t)
                    heaves.append(z_val)
                    pitches.append(0.0) # Placeholder for pitch
    
    # Sort by time
    if times:
        sorted_pairs = sorted(zip(times, heaves, pitches))
        t_sorted, h_sorted, p_sorted = zip(*sorted_pairs)
        
        line_heave.set_data(t_sorted, h_sorted)
        line_pitch.set_data(t_sorted, p_sorted)
        
        ax[0].relim()
        ax[0].autoscale_view()
        ax[1].relim()
        ax[1].autoscale_view()
        
        ax[0].set_title(f"Heave vs Time (t={t_sorted[-1]:.2f}s)")

    return line_heave, line_pitch
def monitor(case_dir: Path):
    """
    Monitors processor0 directories for uniform/sixDoFRigidBodyMotionState
    """
    proc0 = case_dir / "processor0"
    

    global CASE_DIR, fig, ax, line_heave, line_pitch
    CASE_DIR = case_dir
    
    fig, ax = plt.subplots(2, 1, figsize=(10, 8))
    
    # Heave
    line_heave, = ax[0].plot([], [], 'b-', label='Heave (Z)')
    ax[0].set_ylabel('Position Z [m]')
    ax[0].grid(True)
    ax[0].legend()
    
    # Pitch
    line_pitch, = ax[1].plot([], [], 'r-', label='Pitch (deg)')
    ax[1].set_ylabel('Pitch [deg]')
    ax[1].set_xlabel('Time [s] / Step') # ambiguous units
    ax[1].grid(True)
    ax[1].legend()

    ani = FuncAnimation(fig, update, interval=1000, blit=True) # Check every 1s
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("case_dir", type=Path, help="Path to simulation case directory")
    args = parser.parse_args()
    
    if not args.case_dir.exists():
        logger.error(f"Case directory {args.case_dir} does not exist.")
        sys.exit(1)
        
    logger.info(f"Monitoring {args.case_dir}...")
    monitor(args.case_dir)

