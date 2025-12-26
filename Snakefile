import os
from pathlib import Path

configfile: "config.yaml"

BUILD_DIR = Path(config["build_dir"])

# Helper functions
def get_hull_target(hull):
    return f"build/{hull}/report.html"

# Targets
ALL_CASES = []
if "cases" in config:
    for case in config["cases"]:
        case_name = f"{case['hull']}_{case['wave']}_{case['motion']}_{case['load']}"
        ALL_CASES.append(str(BUILD_DIR / case_name / "report.html"))

rule all:
    input:
        ALL_CASES

# -----------------------------------------------------------------------------
# Component Generation
# -----------------------------------------------------------------------------

rule generate_profile:
    input:
        config="config.yaml"
    output:
        profile=str(BUILD_DIR / "{hull}" / "profile.json")
    shell:
        "uv run python scripts/utils/dump_profile.py --config {input.config} --hull {wildcards.hull} --output {output.profile}"

# Specialized rule for Wigley hull (monolithic generation)
rule generate_wigley_hull:
    output:
        hull=str(BUILD_DIR / "wigley" / "hull.stl")
    params:
        blender=config["blender_path"]
    shell:
        "{params.blender} -b -P scripts/generators/blender_operations.py -- --task wigley --output {output.hull}"

# Generic assembly (fallback for other hulls - TBD)
rule assemble_hull_generic:
    input:
        config="config.yaml"
    output:
        hull=str(BUILD_DIR / "{hull}" / "hull.stl")
    wildcard_constraints:
        hull="((?!wigley).)*" # Matches anything EXCEPT wigley
    params:
        blender=config["blender_path"]
    shell:
        "{params.blender} -b -P scripts/generators/blender_operations.py -- --task assemble --output {output.hull}" # Placeholder arguments

# -----------------------------------------------------------------------------
# Pre-checks & Setup
# -----------------------------------------------------------------------------

rule verify_hull:
    input:
        hull=str(BUILD_DIR / "{hull}" / "hull.stl"),
        profile=str(BUILD_DIR / "{hull}" / "profile.json")
    output:
        report=str(BUILD_DIR / "{hull}" / "check_report.json")
    shell:
        "uv run python scripts/core/verify_hull.py --hull {input.hull} --profile {input.profile} --output {output.report}"

# -----------------------------------------------------------------------------
# Meshing (OpenFOAM)
# -----------------------------------------------------------------------------
# Using a dummy output directory marker to handle the directory output
rule mesh_hull:
    input:
        hull=str(BUILD_DIR / "{hull}" / "hull.stl"),
        check=str(BUILD_DIR / "{hull}" / "check_report.json")
    output:
        directory(str(BUILD_DIR / "{hull}" / "constant" / "polyMesh"))
    threads: 4
    params:
        template="templates/floating_hull"
    shell:
        """
        # Ensure we use the docker container logic
        # CRITICAL: Keep this stage separate from openfoam.
        # OpenFOAM environment settings (bashrc) are incompatible with Python venvs.
        # Do NOT merge these stages.
        
        # 1. Prepare Case Directory from Template
        mkdir -p {BUILD_DIR}/{wildcards.hull}
        cp -r {params.template}/* {BUILD_DIR}/{wildcards.hull}/
        cp {input.hull} {BUILD_DIR}/{wildcards.hull}/constant/triSurface/hull.stl
        
        # Configure Default Includes for Meshing (Static)
        cp {BUILD_DIR}/{wildcards.hull}/system/include/functions.static {BUILD_DIR}/{wildcards.hull}/system/include/functions_active
        cp {BUILD_DIR}/{wildcards.hull}/system/include/dynamicMesh.static {BUILD_DIR}/{wildcards.hull}/system/include/dynamicMesh_active
        cp {BUILD_DIR}/{wildcards.hull}/system/include/setFields.still {BUILD_DIR}/{wildcards.hull}/system/include/setFields_active
        
        # 2. Run Mesh Generation (OpenFOAM Container)
        ./scripts/utils/run_openfoam_docker.sh blockMesh -case {BUILD_DIR}/{wildcards.hull}
        ./scripts/utils/run_openfoam_docker.sh surfaceFeatureExtract -case {BUILD_DIR}/{wildcards.hull}
        ./scripts/utils/run_openfoam_docker.sh snappyHexMesh -overwrite -case {BUILD_DIR}/{wildcards.hull}
        """

# -----------------------------------------------------------------------------
# Simulation (OpenFOAM + Monitoring)
# -----------------------------------------------------------------------------

rule run_simulation:
    input:
        # We link the hull's mesh to the simulation case
        mesh=str(BUILD_DIR / "{hull}" / "constant" / "polyMesh"),
        check=str(BUILD_DIR / "{hull}" / "check_report.json")
    output:
        log=str(BUILD_DIR / "{hull}_{wave}_{motion}_{load}" / "log.interFoam"),
        plot=str(BUILD_DIR / "{hull}_{wave}_{motion}_{load}" / "monitor_plot.png")
    threads: 8
    params:
        hull_dir=str(BUILD_DIR / "{hull}"),
        func_file=lambda w: f"functions.{w.motion}",
        mesh_file=lambda w: "dynamicMesh.static" if w.motion == "static" else f"dynamicMesh.{w.motion}.{w.load}",
        sf_file=lambda w: "setFields.still" if w.wave == "still" else "setFields.waves"
    shell:
        """
        CASE_DIR={BUILD_DIR}/{wildcards.hull}_{wildcards.wave}_{wildcards.motion}_{wildcards.load}
        mkdir -p $CASE_DIR
        
        # Copy Mesh from Hull directory
        cp -r {params.hull_dir}/* $CASE_DIR/
        
        # Configure Simulation Includes based on Parameters
        cp $CASE_DIR/system/include/{params.func_file} $CASE_DIR/system/include/functions_active
        cp $CASE_DIR/system/include/{params.mesh_file} $CASE_DIR/constant/dynamicMeshDict
        cp $CASE_DIR/system/include/{params.sf_file} $CASE_DIR/system/include/setFields_active

        # Handle Wave Properties (Issue #26)
        if [ "{wildcards.wave}" == "regular" ]; then
            # Copy waveProperties
            cp templates/floating_hull/constant/waveProperties $CASE_DIR/constant/
            
            # Revert to wave templates for U and alpha.water
            cp templates/floating_hull/0/U.waves $CASE_DIR/0/U
            cp templates/floating_hull/0/alpha.water.waves $CASE_DIR/0/alpha.water
        fi

        # Patch Dynamic Mesh with Hull Properties (CoM, Mass)
        uv run python scripts/core/configure_case.py --report {input.check} --dict $CASE_DIR/constant/dynamicMeshDict
        uv run python scripts/core/configure_case.py --report {input.check} --dict $CASE_DIR/0/pointDisplacement

        # 1. Start Monitoring (Python Container/Local)
        uv run python scripts/core/monitor_floating.py $CASE_DIR --output {output.plot} --auto-exit &
        MONITOR_PID=$!
        trap "kill $MONITOR_PID" EXIT
        
        # 2. Run Simulation (OpenFOAM Container)
        
        # 2. Run Simulation (OpenFOAM Container)
        # CRITICAL: Keep this stage separate from openfoam.
        # 2. Run Simulation (OpenFOAM Container)
        # CRITICAL: Keep this stage separate from openfoam.
        # 2. Run Simulation (OpenFOAM Container - Parallel)
        
        # Decompose
        ./scripts/utils/run_openfoam_docker.sh setFields -case $CASE_DIR
        ./scripts/utils/run_openfoam_docker.sh decomposePar -case $CASE_DIR -force
        
        # Run Parallel Solver
        ./scripts/utils/run_openfoam_docker.sh mpirun -np 8 interFoam -parallel -case $CASE_DIR > {output.log}

        
        # Reconstruct (Optional during run, but good for post-processing)
        # We might do this after? No, keeping it simple.
        # ./scripts/utils/run_openfoam_docker.sh reconstructPar -case $CASE_DIR
        
        # 3. Stop Monitoring
        kill $MONITOR_PID || true
        """

# -----------------------------------------------------------------------------
# Post-processing
# -----------------------------------------------------------------------------

rule verify_run:
    input:
        log=str(BUILD_DIR / "{hull}_{wave}_{motion}_{load}" / "log.interFoam")
    output:
        report=str(BUILD_DIR / "{hull}_{wave}_{motion}_{load}" / "verification_report.json"),
        marker=str(BUILD_DIR / "{hull}_{wave}_{motion}_{load}" / "verification_passed")
    shell:
        """
        # Run verification script
        CASE_DIR={BUILD_DIR}/{wildcards.hull}_{wildcards.wave}_{wildcards.motion}_{wildcards.load}
        uv run python scripts/core/verify_simulation_run.py $CASE_DIR --output {output.report}
        touch {output.marker}
        """

rule post_process:
    input:
        log=str(BUILD_DIR / "{hull}_{wave}_{motion}_{load}" / "log.interFoam"),
        plot=str(BUILD_DIR / "{hull}_{wave}_{motion}_{load}" / "monitor_plot.png"),
        verification=str(BUILD_DIR / "{hull}_{wave}_{motion}_{load}" / "verification_passed"),
        report=str(BUILD_DIR / "{hull}_{wave}_{motion}_{load}" / "verification_report.json")
    output:
        str(BUILD_DIR / "{hull}_{wave}_{motion}_{load}" / "report.html")
    shell:
        """
        uv run python scripts/utils/generate_report.py \
            --json {input.report} \
            --log {input.log} \
            --plot {input.plot} \
            --output {output} \
            --hull {wildcards.hull} \
            --wave {wildcards.wave} \
            --motion {wildcards.motion} \
            --load {wildcards.load}
        """
