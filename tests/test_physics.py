import pytest
import logging
import numpy as np
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Path to the templates directory (assuming tests runs from root)
# Using pathlib to resolve the path relative to this file
TEMPLATES_DIR = (Path(__file__).parent.parent / 'templates').resolve()

def read_probe_data(case_name: str, probe_name: str, field_name: str) -> tuple[np.ndarray, np.ndarray]:
    """
    Reads probe data from postProcessing/<probe_name>/0/<field_name>.
    Returns time array and data array (n_times, n_probes).
    """
    path = TEMPLATES_DIR / case_name / "postProcessing" / probe_name / "0" / field_name
    
    # Check if file exists (simulation might not have run)
    if not path.exists():
        logger.warning(f"Data not found at {path}. Simulation may not have run.")
        pytest.skip(f"Data not found at {path}. Simulation may not have run.")
    
    logger.info(f"Reading probe data from {path}")
    
    # OpenFOAM probe format: # Time    prob1    probe2 ...
    data = []
    times = []
    
    with path.open('r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.split()
            try:
                times.append(float(parts[0]))
                
                # Handle vector fields (U) which look like (x y z)
                if field_name == 'U':
                    # Clean parens: (1 2 3) (4 5 6) -> 1 2 3 4 5 6
                    cleaned = line.replace('(', '').replace(')', '')
                    vals = [float(x) for x in cleaned.split()[1:]]
                    data.append(vals)
                else:
                    data.append([float(x) for x in parts[1:]])
            except ValueError as e:
                logger.error(f"Failed to parse line: {line.strip()} - {e}")
                continue
                
    return np.array(times), np.array(data)

def test_still_water_stationarity():
    """
    Verify that in the still_water case, velocity remains negligible and alpha is stable.
    """
    case = 'still_water'
    
    # 1. Check Velocity (should be near 0 at center)
    times, u_data = read_probe_data(case, 'velocityProbe', 'U')
    
    # u_data shape: (n_times, n_probes * 3) -> we have 1 probe, so 3 cols (u, v, w)
    if u_data.size == 0:
        pytest.fail("No velocity data read")

    # Check max velocity magnitude
    u_mag = np.sqrt(u_data[:,0]**2 + u_data[:,1]**2 + u_data[:,2]**2)
    max_u = np.max(u_mag)
    
    logger.info(f"Max velocity in still_water: {max_u}")

    # Allow some very small numerical noise, e.g. < 1e-2 m/s
    assert max_u < 1e-2, f"Water is moving in still_water case! Max U={max_u}"

    # 2. Check Alpha (should be 1.0 for water)
    times, alpha_data = read_probe_data(case, 'velocityProbe', 'alpha.water')
    # Probe is at z=-5, should be fully ideal water (1.0)
    
    if alpha_data.size == 0:
        pytest.fail("No alpha data read")
        
    mean_alpha = np.mean(alpha_data)
    logger.info(f"Mean alpha in still_water: {mean_alpha}")
    
    assert np.allclose(alpha_data, 1.0, atol=1e-2), "Alpha at center is not 1.0 (Water)"

def test_wave_tank_propagation():
    """
    Verify that in wave_tank, the wave propagates from inlet to outlet.
    We check alpha at 3 probes: x=-50 (upstream), x=0 (mid), x=50 (downstream).
    Probe height z=0.5 (just above initial water level 0).
    Ideally, alpha should stay 0 until wave hits, then spike.
    """
    case = 'wave_tank'
    times, alpha_data = read_probe_data(case, 'waveProbes', 'alpha.water')
    
    # alpha_data cols: 0->(-50), 1->(0), 2->(50)
    if alpha_data.shape[1] < 2:
        pytest.skip("Not enough probes found in wave_tank data")

    # Check if wave reaches middle probe (x=0)
    # Max alpha should increase significantly > 0
    max_alpha_mid = np.max(alpha_data[:, 1])
    logger.info(f"Max alpha at mid probe: {max_alpha_mid}")
    
    if times[-1] < 1.0:
        logger.warning("Simulation time too short (<1s). Skipping wave propagation check.")
        pytest.skip("Simulation time too short to observe wave propagation.")

    assert max_alpha_mid > 0.5, "Wave did not reach middle probe (x=0)!"
    
    # Check causality: Upstream (-50) should rise before Downstream (50)
    # Find time of first arrival (e.g. alpha > 0.1)
    def arrival_time(idx):
        indices = np.where(alpha_data[:, idx] > 0.1)[0]
        return times[indices[0]] if len(indices) > 0 else float('inf')

    t_upstream = arrival_time(0)
    t_mid = arrival_time(1)
    
    logger.info(f"Wave arrival times: Upstream={t_upstream}, Mid={t_mid}")
    
    assert t_upstream < t_mid, f"Causality violation or wave not propagated (t_up={t_upstream}, t_mid={t_mid})"

def test_base_case_forces():
    """
    Verify that the base_case (ship) generates resistance forces.
    """
    case = 'base_case'
    # forces.dat format is specific: Time forces(px py pz) moments(vx vy vz) ...
    path = TEMPLATES_DIR / case / "postProcessing/forces/0/forces.dat"
    
    if not path.exists():
        logger.warning("Forces data not found.")
        pytest.skip("Forces data not found.")
        
    data = []
    with path.open('r') as f:
        for line in f:
            if line.startswith('#'): continue
            # Remove parens
            cleaned = line.replace('(', '').replace(')', '')
            try:
                data.append([float(x) for x in cleaned.split()])
            except ValueError:
                continue
            
    forces = np.array(data)
    if forces.size == 0:
        pytest.fail("Empty forces file")
        
    # forces columns: 0:Time, 1:F_p_x, ...
    # Standard forces output has: Time(0) (Fp_x Fp_y Fp_z)(1-3) (Fv_x Fv_y Fv_z)(4-6) ...
    
    # Total X force = Pressure X + Viscous X
    total_fx = forces[:, 1] + forces[:, 4] # Pres + Visc X
    
    avg_drag = np.mean(total_fx[-10:]) # Average last few steps
    logger.info(f"Average Drag Force: {avg_drag}")
    
    assert avg_drag > 0, f"Drag is negative or zero! ({avg_drag})"

def test_inverse_barometer():
    """
    Verify the Inverse Barometer effect.
    Case 'inverse_barometer' has a pressure gradient:
    High Pressure at Inlet (x=-100) -> Should depress water level.
    Low Pressure at Outlet (x=400) -> Should raise water level.
    We check alpha at inlet and outlet probes.
    """
    case = 'inverse_barometer'
    
    # TODO: Add probe to inverse_barometer controlDict similar to wave_tank
    path = TEMPLATES_DIR / case / "postProcessing/barometerProbes/0/alpha.water"
    
    if not path.exists():
        logger.warning("Barometer probes not found.")
        pytest.skip("Barometer probes not found. Needs configuration.")
        
    times, alpha_data = read_probe_data(case, 'barometerProbes', 'alpha.water')
    
    # Use data columns: 0:Inlet(-100), 1:Outlet(400)
    alpha_inlet = alpha_data[-1, 0]
    alpha_outlet = alpha_data[-1, 1]
    
    logger.info(f"Inverse Barometer Levels: Inlet={alpha_inlet}, Outlet={alpha_outlet}")
    
    assert alpha_inlet < 0.5, f"Inlet water level did not drop enough (Alpha={alpha_inlet})"
    assert alpha_outlet > 0.5, f"Outlet water level is not maintained (Alpha={alpha_outlet})"

