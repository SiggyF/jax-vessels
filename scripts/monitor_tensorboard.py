import os
import re
import time
import argparse
from tensorboardX import SummaryWriter
import sys

def parse_log_and_stream(log_files, log_dir):
    """
    Tails multiple log files (sequentially or generally the latest active one) and streams metrics to TensorBoard.
    """
    writer = SummaryWriter(log_dir=log_dir)
    print(f"Logging to TensorBoard dir: {log_dir}")
    
    # regex patterns
    re_time = re.compile(r"^Time = ([\d\.eE\-\+]+)")
    re_com = re.compile(r"Centre of mass: \(([\d\.eE\-\+]+)\s+([\d\.eE\-\+]+)\s+([\d\.eE\-\+]+)\)")
    re_orient = re.compile(r"Orientation: \(([\d\.eE\-\+]+)\s+([\d\.eE\-\+]+)\s+([\d\.eE\-\+]+)\)") # Euler angles often
    re_lin_vel = re.compile(r"Linear velocity: \(([\d\.eE\-\+]+)\s+([\d\.eE\-\+]+)\s+([\d\.eE\-\+]+)\)")
    re_ang_vel = re.compile(r"Angular velocity: \(([\d\.eE\-\+]+)\s+([\d\.eE\-\+]+)\s+([\d\.eE\-\+]+)\)")
    re_courant = re.compile(r"Courant Number mean: ([\d\.eE\-\+]+) max: ([\d\.eE\-\+]+)")
    re_deltat = re.compile(r"deltaT = ([\d\.eE\-\+]+)")
    # Solving for p_rgh, Initial residual = 0.00366291, Final residual = ...
    re_residual = re.compile(r"Solving for ([a-zA-Z0-9_]+).*, Initial residual = ([\d\.eE\-\+]+), Final residual = ([\d\.eE\-\+]+)")
    
    current_time = 0.0
    
    # If passed a list of files, we might need to handle them. For now, let's assume one main log file or a glob?
    # Or just tail the one file provided.
    
    filename = log_files[0]
    
    # Wait for file to exist
    while not os.path.exists(filename):
        print(f"Waiting for {filename} to exist...")
        time.sleep(2)
        
    print(f"Streaming from {filename}...")
    
    f = open(filename, 'r')
    
    while True:
        line = f.readline()
        if not line:
            time.sleep(0.1)
            continue
            
        # Parse Time
        m_time = re_time.search(line)
        if m_time:
            current_time = float(m_time.group(1))
            # Use 1/10000s as step to handle deltaT=0.0005 (5 steps)
            step = int(current_time * 10000) 
            
            # Flush periodically?
            
        # CoM (Heave)
        m_com = re_com.search(line)
        if m_com and current_time > 0:
            x, y, z = map(float, m_com.groups())
            step = int(current_time * 10000)
            writer.add_scalar('Motion/Heave', z, step)
            writer.add_scalar('Motion/Surge', x, step)
            writer.add_scalar('Motion/Sway', y, step)
            
        # Velocity
        m_vel = re_lin_vel.search(line)
        if m_vel and current_time > 0:
            vx, vy, vz = map(float, m_vel.groups())
            step = int(current_time * 10000)
            writer.add_scalar('Velocity/Linear_Z', vz, step)
            
        # Orientation (Pitch/Roll/Yaw)
        m_rot = re_orient.search(line)
        if m_rot and current_time > 0:
            r, p, y = map(float, m_rot.groups())
            step = int(current_time * 10000)
            writer.add_scalar('Orientation/Roll', r, step)
            writer.add_scalar('Orientation/Pitch', p, step)
            writer.add_scalar('Orientation/Yaw', y, step)
            
        # Courant
        m_co = re_courant.search(line)
        if m_co:
            mean_co, max_co = map(float, m_co.groups())
            step = int(current_time * 10000)
            writer.add_scalar('Solver/Courant_Mean', mean_co, step)
            writer.add_scalar('Solver/Courant_Max', max_co, step)
            
        # DeltaT
        m_dt = re_deltat.search(line)
        if m_dt:
            dt = float(m_dt.group(1))
            step = int(current_time * 10000)
            writer.add_scalar('Solver/DeltaT', dt, step)
            
        # Residuals
        m_res = re_residual.search(line)
        if m_res:
            field, init_res, final_res = m_res.groups()
            step = int(current_time * 10000)
            writer.add_scalar(f'Residuals/{field}_Initial', float(init_res), step)
            writer.add_scalar(f'Residuals/{field}_Final', float(final_res), step)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('logfile', help='Path to log file to monitor')
    parser.add_argument('--logdir', help='TensorBoard log dir', default='runs/vessel_sim')
    args = parser.parse_args()
    
    try:
        parse_log_and_stream([args.logfile], args.logdir)
    except KeyboardInterrupt:
        print("Stopping monitor...")
