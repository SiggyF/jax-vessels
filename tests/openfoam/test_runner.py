import subprocess
import logging
from pathlib import Path

def test_run_analysis_with_examples():
    """
    End-to-end test: Generate hull -> Run Analysis (Mock)
    """
    root = Path(__file__).parent.parent.parent
    gen_script = root / "examples" / "scripts" / "generate_hull.py"
    test_hull = root / "test_output" / "test_barge.stl"
    out_dir = root / "test_output" / "analysis"
    
    test_hull.parent.mkdir(parents=True, exist_ok=True)
    
    # 1. Generate Hull
    subprocess.check_call(
        ["uv", "run", "python", str(gen_script), "--type", "barge", "--out", str(test_hull)],
        cwd=root
    )
    assert test_hull.exists()
    
    # 2. Run Analysis
    subprocess.check_call(
        ["uv", "run", "openfoam-run", str(test_hull), "--out-dir", str(out_dir)],
        cwd=root
    )
    
    # 3. Verify Output
    # Since mocked, we expect directory creation and maybe logs?
    # The runner creates case_{stem}_0
    case_dir = out_dir / "case_test_barge_0"
    assert case_dir.exists()
    assert (case_dir / "constant" / "triSurface" / "hull.stl").exists()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_run_analysis_with_examples()
    logging.info("Test passed!")
