#!/usr/bin/env python

import re
import pandas as pd
import matplotlib.pyplot as plt
import argparse
import os
import sys

def parse_log(log_path):
    """Parses OpenFOAM log file for Time, deltaT, Courant, and 6DoF motion."""
    data = {
        "Time": [],
        "deltaT": [],
        "maxCo": [],
        "CoM_z": [],
        "LinVel_x": [],
        "AngVel_y": [] # Pitch rate
    }
    
    # Regex patterns
    # Time = 0.001
    time_pat = re.compile(r"^Time = ([\d\.e\-\+]+)")
    # deltaT = 0.001
    dt_pat = re.compile(r"^deltaT = ([\d\.e\-\+]+)")
    # Courant Number mean: 0 max: 0
    co_pat = re.compile(r"Courant Number mean: [\d\.e\-\+]+ max: ([\d\.e\-\+]+)")
    
    # 6-DoF rigid body motion
    # Centre of mass: (67.5 0 2.00819)
    com_pat = re.compile(r"\s+Centre of mass: \(([\d\.e\-\+]+) ([\d\.e\-\+]+) ([\d\.e\-\+]+)\)")
    # Linear velocity: (0 0 0)
    lin_vel_pat = re.compile(r"\s+Linear velocity: \(([\d\.e\-\+]+) ([\d\.e\-\+]+) ([\d\.e\-\+]+)\)")
    # Angular velocity: (0 0 0)
    ang_vel_pat = re.compile(r"\s+Angular velocity: \(([\d\.e\-\+]+) ([\d\.e\-\+]+) ([\d\.e\-\+]+)\)")

    current_time = None
    
    with open(log_path, 'r') as f:
        for line in f:
            # Time block start
            m_time = time_pat.match(line)
            if m_time:
                current_time = float(m_time.group(1))
                data["Time"].append(current_time)
                # Fill placeholders for this timestep (will be updated if found)
                data["deltaT"].append(None)
                data["maxCo"].append(None)
                data["CoM_z"].append(None)
                data["LinVel_x"].append(None)
                data["AngVel_y"].append(None)
                continue
            
            if current_time is None:
                continue
                
            # DeltaT (often appears after Time)
            m_dt = dt_pat.match(line)
            if m_dt:
                data["deltaT"][-1] = float(m_dt.group(1))
                
            # Courant
            m_co = co_pat.search(line)
            if m_co:
                data["maxCo"][-1] = float(m_co.group(1))
            
            # 6DoF
            m_com = com_pat.match(line)
            if m_com:
                data["CoM_z"][-1] = float(m_com.group(3))
            
            m_lin = lin_vel_pat.match(line)
            if m_lin:
                data["LinVel_x"][-1] = float(m_lin.group(1))
                
            m_ang = ang_vel_pat.match(line)
            if m_ang:
                data["AngVel_y"][-1] = float(m_ang.group(2))

    df = pd.DataFrame(data)
    # Forward fill to handle optional outputs not printing every line if format varies (though usually standard)
    # But here we initialized with None. Drop incomplete rows if critical?
    return df

def generate_plots(df, output_dir):
    """Generates stability plots."""
    if df.empty:
        print("No data found in log.")
        return

    fig, axs = plt.subplots(3, 2, figsize=(15, 10))
    fig.suptitle('Simulation Stability Report', fontsize=16)

    # 1. Delta T
    axs[0, 0].plot(df["Time"], df["deltaT"], 'b-')
    axs[0, 0].set_title('Delta T')
    axs[0, 0].set_ylabel('s')
    axs[0, 0].grid(True)
    axs[0, 0].set_yscale('log')

    # 2. Max Courant
    axs[0, 1].plot(df["Time"], df["maxCo"], 'r-')
    axs[0, 1].set_title('Max Courant Number')
    axs[0, 1].grid(True)
    axs[0, 1].axhline(y=1.0, color='k', linestyle='--')

    # 3. Heave (CoM Z)
    if "CoM_z" in df and not df["CoM_z"].isnull().all():
        axs[1, 0].plot(df["Time"], df["CoM_z"], 'g-')
        axs[1, 0].set_title('Heave (CoM Z)')
        axs[1, 0].set_ylabel('m')
        axs[1, 0].grid(True)
    else:
        axs[1, 0].text(0.5, 0.5, 'No 6DoF Data', ha='center')

    # 4. Pitch Rate (Ang Vel Y)
    if "AngVel_y" in df and not df["AngVel_y"].isnull().all():
        axs[1, 1].plot(df["Time"], df["AngVel_y"], 'm-')
        axs[1, 1].set_title('Pitch Rate (rad/s)')
        axs[1, 1].grid(True)
    else:
         axs[1, 1].text(0.5, 0.5, 'No 6DoF Data', ha='center')

    # 5. Linear Velocity X
    if "LinVel_x" in df and not df["LinVel_x"].isnull().all():
        axs[2, 0].plot(df["Time"], df["LinVel_x"], 'c-')
        axs[2, 0].set_title('Surge Velocity (m/s)')
        axs[2, 0].grid(True)
    else:
         axs[2, 0].text(0.5, 0.5, 'No 6DoF Data', ha='center')

    # Layout
    plt.tight_layout()
    plt.subplots_adjust(top=0.9)
    
    plot_path = os.path.join(output_dir, "stability_plots.png")
    plt.savefig(plot_path)
    print(f"Plots saved to {plot_path}")

def generate_markdown_report(df, output_dir):
    """Generates summary.md."""
    if df.empty:
        return

    last_row = df.iloc[-1]
    
    failed = False
    fail_reason = ""
    
    if last_row["deltaT"] is not None and last_row["deltaT"] < 1e-5:
        failed = True
        fail_reason = f"deltaT dropped below 1e-5 ({last_row['deltaT']})"
    
    # Check for explosion (only if velocity exists)
    max_surge = 0.0
    if "LinVel_x" in df and not df["LinVel_x"].isnull().all():
         max_surge = df['LinVel_x'].abs().max()
         if max_surge > 100: # Arbitrary unphysical threshold
            failed = True
            fail_reason = f"Velocity Divergence detected (Max Surge: {max_surge:.2e})"
    
    max_pitch = 0.0
    if "AngVel_y" in df and not df["AngVel_y"].isnull().all():
        max_pitch = df['AngVel_y'].abs().max()

    status = "FAILED" if failed else "STABLE (Likely)"
    color = "red" if failed else "green"

    md = f"""# Simulation Verification Report

## Status: <span style="color:{color}">{status}</span>

**Reason**: {fail_reason if failed else "No obvious divergence detected."}

## Statistics
| Metric | Value |
| :--- | :--- |
| **Duration** | {last_row['Time']:.4f} s |
| **Final dt** | {last_row['deltaT'] if last_row['deltaT'] is not None else 'N/A'} |
| **Max Courant** | {df['maxCo'].max() if 'maxCo' in df else 'N/A'} |
| **Max Surge Vel** | {max_surge:.2f} m/s |
| **Max Pitch Rate** | {max_pitch:.2f} rad/s |

## Stability Plots
![Stability Plots](stability_plots.png)
"""
    
    report_path = os.path.join(output_dir, "summary.md")
    with open(report_path, "w") as f:
        f.write(md)
    print(f"Report saved to {report_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True, help="Path to log.interFoam")
    parser.add_argument("--out", required=True, help="Output directory for report")
    args = parser.parse_args()
    
    if not os.path.exists(args.log):
        print(f"ERROR: Log file not found: {args.log}")
        sys.exit(1)
        
    if not os.path.exists(args.out):
        os.makedirs(args.out)
        
    df = parse_log(args.log)
    
    if df.empty:
        print("WARNING: Parsed DataFrame is empty!")
    else:
        generate_plots(df, args.out)
        generate_markdown_report(df, args.out)
    
    # Try visualization if requested or always
    try:
        import pyvista as pv
        print("PyVista found. Generating water surface visualization...")
        
        # Determine latest time directory
        case_dir = os.path.dirname(args.log)
        # List directories that look like numbers
        time_dirs = [d for d in os.listdir(case_dir) if re.match(r'^[\d\.]+$', d)]
        if not time_dirs:
            print("No time directories found for visualization.")
        else:
            final_time = sorted(time_dirs, key=float)[-1]
            print(f"Visualizing time: {final_time}")
            
            # Read OpenFOAM data
            # Point to system/controlDict as the reader file
            reader = pv.POpenFOAMReader(os.path.join(case_dir, "system", "controlDict"))
            reader.set_active_time_value(float(final_time))
            
            # Read mesh
            mesh = reader.read()
            
            # Extract internal mesh block (usually 'internalMesh' or index 0)
            if "internalMesh" in mesh:
                grid = mesh["internalMesh"]
            else:
                grid = mesh[0] # Fallback
                
            # Extract Surface (alpha.water = 0.5)
            if "alpha.water" in grid.point_data:
                water = grid.contour([0.5], scalars="alpha.water")
                
                # Setup Plotter
                pl = pv.Plotter(off_screen=True)
                pl.add_mesh(water, color="azure", opacity=0.8, smooth_shading=True, show_scalar_bar=False)
                
                # Add Hull (Patches)
                if "boundary" in mesh:
                    boundary = mesh["boundary"]
                    if "hull" in boundary:
                        hull = boundary["hull"]
                        pl.add_mesh(hull, color="darkgrey", smooth_shading=True)
                
                # Camera setup
                pl.camera_position = 'xy'
                pl.camera.azimuth = 45
                pl.camera.elevation = 30
                pl.enable_eye_dome_lighting()  # Better depth perception
                
                vis_path = os.path.join(args.out, "water_surface.png")
                pl.screenshot(vis_path)
                print(f"Visualization saved to {vis_path}")
                
            else:
                 print("alpha.water not found in mesh data.")

    except ImportError as e:
        print(f"PyVista import/dependency error: {e}")
    except Exception as e:
        print(f"Visualization failed: {e}")

