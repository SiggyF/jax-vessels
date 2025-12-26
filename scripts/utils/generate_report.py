import json
import sys
import argparse
from pathlib import Path

def generate_report(report_json, log_file, plot_file, output_html, hull, wave, motion, load):
    with open(report_json) as f:
        data = json.load(f)

    status = data["status"]
    status_class = "passed" if status == "PASSED" else "failed"
    metrics = data["metrics"]
    limits = data["limits"]

    # Read log tail
    log_tail = ""
    try:
        with open(log_file, "r") as log:
            lines = log.readlines()[-50:]
            log_tail = "".join(lines)
    except Exception as e:
        log_tail = f"Could not read log file: {e}"

    html_template = """
<html>
<head>
    <style>
        body {{ font-family: sans-serif; max-width: 800px; margin: auto; padding: 20px; }}
        h1 {{ border-bottom: 2px solid #333; }}
        .metric {{ margin: 10px 0; padding: 10px; background: #f4f4f4; border-radius: 5px; }}
        .passed {{ color: green; font-weight: bold; }}
        .failed {{ color: red; font-weight: bold; }}
        pre {{ background: #eee; padding: 10px; overflow-x: auto; }}
    </style>
</head>
<body>
    <h1>Report: {hull}</h1>
    <p><strong>Wave:</strong> {wave} | <strong>Motion:</strong> {motion} | <strong>Load:</strong> {load}</p>
    
    <h2>Verification</h2>
    <div class="metric">
        Status: <span class="{status_class}">{status}</span><br>
        Peak Courant: {metrics[peak_courant]:.2f} (Limit: {limits[max_courant]})<br>
        Min DeltaT: {metrics[min_delta_t]:.2e} (Limit: {limits[min_dt]})<br>
        Peak Velocity (Global): {metrics[peak_u_global]:.2f} (Limit: {limits[max_velocity]})<br>
        Peak Velocity (Hull): {metrics[peak_u_hull]:.2f} (Limit: {limits[max_velocity_hull]})
    </div>

    <h2>Monitoring</h2>
    <img src="{plot_path}" style="max-width:100%"/>

    <h2>Log Tail</h2>
    <pre>
{log_tail}
    </pre>
</body>
</html>
    """

    content = html_template.format(
        hull=hull,
        wave=wave,
        motion=motion,
        load=load,
        status=status,
        status_class=status_class,
        metrics=metrics,
        limits=limits,
        plot_path=Path(plot_file).name, # Assume in same dir
        log_tail=log_tail
    )

    with open(output_html, "w") as f:
        f.write(content)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True)
    parser.add_argument("--log", required=True)
    parser.add_argument("--plot", required=True)
    parser.add_argument("--output", required=True)
    # Metadata
    parser.add_argument("--hull", required=True)
    parser.add_argument("--wave", required=True)
    parser.add_argument("--motion", required=True)
    parser.add_argument("--load", required=True)
    
    args = parser.parse_args()
    
    generate_report(args.json, args.log, args.plot, args.output, args.hull, args.wave, args.motion, args.load)
