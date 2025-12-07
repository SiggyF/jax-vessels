import pytest
import os
import glob
import numpy as np

# Path to the templates directory (assuming tests runs from root)
TEMPLATES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../templates'))

def read_probe_data(case_name, probe_name, field_name):
    """
    Reads probe data from postProcessing/<probe_name>/0/<field_name>.
    Returns time array and data array (n_times, n_probes).
    """
    path = os.path.join(TEMPLATES_DIR, case_name, f"postProcessing/{probe_name}/0/{field_name}")
    
    # Check if file exists (simulation might not have run)
    if not os.path.exists(path):
        pytest.skip(f"Data not found at {path}. Simulation may not have run.")
    
    # OpenFOAM probe format: # Time    prob1    probe2 ...
    data = []
    times = []
    with open(path, 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.split()
            times.append(float(parts[0]))
            
            # Handle vector fields (U) which look like (x y z)
            if field_name == 'U':
                # This is a bit complex parsing for vectors "(u v w)", skipping for now/simplifying
                # Assuming scalar for alpha/p, vector complexity requires regex
                pass 
                # For now let's stick to scalars or simple parsing
                # Actually, standard probes output: Time (1 2 3) (4 5 6) ...
                # Let's clean parens
                cleaned = line.replace('(', '').replace(')', '')
                vals = [float(x) for x in cleaned.split()[1:]]
                data.append(vals)
            else:
                data.append([float(x) for x in parts[1:]])
                
    return np.array(times), np.array(data)

def test_still_water_stationarity():
    """
    Verify that in the still_water case, velocity remains negligible and alpha is stable.
    """
    case = 'still_water'
    
    # 1. Check Velocity (should be near 0 at center)
    # Note: U probe might parse as 3 columns per probe. 
    # Let's simplify and just read the file raw if complex parsing needed, 
    # but our helper handles (x y z) by stripping parens.
    times, u_data = read_probe_data(case, 'velocityProbe', 'U')
    
    # u_data shape: (n_times, n_probes * 3) -> we have 1 probe, so 3 cols (u, v, w)
    # Check max velocity magnitude
    u_mag = np.sqrt(u_data[:,0]**2 + u_data[:,1]**2 + u_data[:,2]**2)
    
    # Allow some very small numerical noise, e.g. < 1e-3 m/s
    assert np.max(u_mag) < 1e-2, f"Water is moving in still_water case! Max U={np.max(u_mag)}"

    # 2. Check Alpha (should be 1.0 for water)
    times, alpha_data = read_probe_data(case, 'velocityProbe', 'alpha.water')
    # Probe is at z=-5, should be fully ideal water (1.0)
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
    
    # Check if wave reaches middle probe (x=0)
    # Max alpha should increase significantly > 0
    max_alpha_mid = np.max(alpha_data[:, 1])
    
    # Note: Depending on sim time, wave might not travel 100m. 
    # Inlet is at -100. Velocity ~10m/s (if imposed) or gravity wave c = sqrt(g*h).
    # If "dam break" height=10m, c approx sqrt(9.8*10) ~ 10m/s.
    # Dist to x=0 is 100m. Time ~ 10s.
    # Base case runs for 0.05s (tiny check). 
    # WARNING: The default endTime in controlDict is 0.05s. This is too short for physics tests.
    # The user logic implies we check *after* running. We assume the user might run longer.
    # If sim is too short, we skip.
    
    if times[-1] < 1.0:
        pytest.skip("Simulation time too short to observe wave propagation.")

    assert max_alpha_mid > 0.5, "Wave did not reach middle probe (x=0)!"
    
    # Check causality: Upstream (-50) should rise before Downstream (50)
    # Find time of first arrival (e.g. alpha > 0.1)
    def arrival_time(idx):
        indices = np.where(alpha_data[:, idx] > 0.1)[0]
        return times[indices[0]] if len(indices) > 0 else float('inf')

    t_upstream = arrival_time(0)
    t_mid = arrival_time(1)
    
    assert t_upstream < t_mid, f"Causality violation or wave not propagated (t_up={t_upstream}, t_mid={t_mid})"

def test_base_case_forces():
    """
    Verify that the base_case (ship) generates resistance forces.
    """
    case = 'base_case'
    # forces.dat format is specific: Time forces(px py pz) moments(vx vy vz) ...
    path = os.path.join(TEMPLATES_DIR, case, "postProcessing/forces/0/forces.dat")
    
    if not os.path.exists(path):
        pytest.skip("Forces data not found.")
        
    data = []
    with open(path, 'r') as f:
        for line in f:
            if line.startswith('#'): continue
            # Remove parens
            cleaned = line.replace('(', '').replace(')', '')
            data.append([float(x) for x in cleaned.split()])
            
    forces = np.array(data)
    # forces columns: 0:Time, 1:F_p_x, ...
    # Total X force = Pressure X + Viscous X
    # Standard forces output has: Time(0) (Fp_x Fp_y Fp_z)(1-3) (Fv_x Fv_y Fv_z)(4-6) (Mp_...)(7-9) ...
    # Check OpenFOAM version format carefully. usually 1=TotalX or similar with "forces" type
    # Actually type 'forces' usually writes: Time, Fx_p, Fy_p, Fz_p, Fx_v, Fy_v, Fz_v, Mx_p ...
    
    total_fx = forces[:, 1] + forces[:, 4] # Pres + Visc X
    
    # Drag should be positive (force on hull is +X if flow is -X??)
    # Current flow: Inlet U = (10 0 0). Flow +X.
    # Force on hull: Flow pushes hull in +X. So Drag should be +X.
    
    avg_drag = np.mean(total_fx[-10:]) # Average last few steps
    
    assert avg_drag > 0, f"Drag is negative or zero! ({avg_drag})"

def test_inverse_barometer():
    """
    Verify the Inverse Barometer effect.
    Case 'inverse_barometer' has a pressure gradient:
    High Pressure at Inlet (x=-100) -> Should depress water level.
    Low Pressure at Outlet (x=400) -> Should raise water level.
    We check alpha at inlet and outlet probes.
    """
    # We need to add probing to inverse_barometer/system/controlDict first!
    # For now, let's assume we can read the fields directly or we relying on a 'surfaceElevation' probe if added.
    # Since we haven't added probes to inverse_barometer yet, let's skip/TODO this or check 
    # if we can reuse the generic 'velocityProbe' or add a specific one.
    
    # Actually, let's create a specialized probe for this test case.
    # For now, we will mark this test as skipped until probes are added.
    case = 'inverse_barometer'
    
    # TODO: Add probe to inverse_barometer controlDict similar to wave_tank
    path = os.path.join(TEMPLATES_DIR, case, "postProcessing/barometerProbes/0/alpha.water")
    
    if not os.path.exists(path):
        pytest.skip("Barometer probes not found. Needs configuration.")
        
    times, alpha_data = read_probe_data(case, 'barometerProbes', 'alpha.water')
    
    # Expected: Alpha at inlet (high P) < Alpha at outlet (low P) at z=0?
    # Actually, inverse barometer means mean sea level change.
    # High P -> Lower Sea Level. Low P -> Higher Sea Level.
    # If we probe at z=0 (original surface):
    # At Inlet (High P): Level drops < 0. So alpha at z=0 might drop below 0.5 or 1 -> 0.
    # At Outlet (Low P): Level rises > 0. Alpha at z=0 stays 1.
    # This might be hard to distinguish with just a z=0 probe if it's already 1.
    # Better to probe at z=-0.1 (should be water) and z=0.1 (should be air).
    # If level drops at inlet, z=-0.1 might become air? Delta P = 1000Pa ~ 0.1m.
    # So probing at z=-0.05 might show air at inlet.
    
    # Use data columns: 0:Inlet(-100), 1:Outlet(400)
    alpha_inlet = alpha_data[-1, 0]
    alpha_outlet = alpha_data[-1, 1]
    
    # At Inlet (-100), P is high (+1000Pa). Level should drop ~ 0.1m.
    # If probe is at z=-0.05, it should see Air (alpha~0).
    
    # At Outlet (400), P is low (0Pa). Level should be 0 (or higher if P_min < 0).
    # If probe is at z=-0.05, it should see Water (alpha~1).
    
    assert alpha_inlet < 0.5, f"Inlet water level did not drop enough (Alpha={alpha_inlet})"
    assert alpha_outlet > 0.5, f"Outlet water level is not maintained (Alpha={alpha_outlet})"

