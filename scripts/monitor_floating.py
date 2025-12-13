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

def parse_state_file(filepath: Path):
    """
    Parses OpenFOAM sixDoFRigidBodyMotionState dictionary.
    Format:
    centreOfRotation ( 67.5 0 2 );
    orientation ( 1 0 0 ... );
    """
    try:
        content = filepath.read_text()
        
        # Parse Position (Heave) from centreOfRotation
        pos_match = re.search(r'centreOfRotation\s*\(\s*([-\d\.eE]+)\s+([-\d\.eE]+)\s+([-\d\.eE]+)\s*\)', content)
        if pos_match:
            # z = float(pos_match.group(3))
            # Actually, check if it translates?
            # CoR moves with the body.
            return float(pos_match.group(3))
            
    except Exception as e:
        pass
    return None

def monitor(case_dir: Path):
    """
    Monitors processor0 directories for uniform/sixDoFRigidBodyMotionState
    """
    proc0 = case_dir / "processor0"
    
    fig, ax1 = plt.subplots(1, 1)
    ax1.set_ylabel('Heave (Z) [m]')
    ax1.set_xlabel('Time [s]')
    
    line, = ax1.plot([], [], 'b-o', markersize=3)
    
    # Store history
    history = {'t': [], 'z': []}
    
    def update(frame):
        if not proc0.exists():
            return line,
            
        # Find all time directories
        # Filter for numeric names
        try:
            time_dirs = sorted(
                [d for d in proc0.iterdir() if d.is_dir() and re.match(r'^[\d\.]+$', d.name)],
                key=lambda x: float(x.name)
            )
        except:
            return line,

        # We can optimize by only checking new ones, but for now re-scan is fine for robustness
        # Clear/Rebuild to handle restarts
        history['t'] = []
        history['z'] = []
        
        for t_dir in time_dirs:
            t_val = float(t_dir.name)
            fpath = t_dir / "uniform/sixDoFRigidBodyMotionState"
            
            if fpath.exists():
                z = parse_state_file(fpath)
                if z is not None:
                    history['t'].append(t_val)
                    history['z'].append(z)
        
        if history['t']:
            line.set_data(history['t'], history['z'])
            ax1.set_xlim(min(history['t']), max(history['t']) + 0.1)
            # Dynamic Z scaling
            z_min, z_max = min(history['z']), max(history['z'])
            span = max(0.1, z_max - z_min)
            ax1.set_ylim(z_min - span*0.2, z_max + span*0.2)
            ax1.set_title(f"Time: {history['t'][-1]:.3f}s | Heave: {history['z'][-1]:.4f}m")
            
        return line,

    ani = FuncAnimation(fig, update, interval=1000) # Check every 1s
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
