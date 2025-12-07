import jax
import jax.numpy as jnp
from typing import NamedTuple
from .core import ShipModel

class LinearShipState(NamedTuple):
    """State for the linear ship model (Surge, Sway, Yaw, SurgeRate, SwayRate, YawRate)."""
    # Using a simplified 3-DOF model (Surge, Sway, Yaw) for the linear example initially
    # x, y, psi, u, v, r
    pose: jnp.ndarray  # [x, y, psi]
    vel: jnp.ndarray   # [u, v, r]

class LinearShipParams(NamedTuple):
    """Parameters for the linear ship model."""
    M: jnp.ndarray  # Mass matrix
    D: jnp.ndarray  # Damping matrix
    # Simplified linear model: M * nu_dot + D * nu = tau

class LinearShipModel(ShipModel):
    def __init__(self, params: LinearShipParams):
        self.params = params
        self.M_inv = jnp.linalg.inv(params.M)

    def step(self, state: LinearShipState, control: jnp.ndarray, dt: float) -> LinearShipState:
        """
        Linear model step:
        M * nu_dot + D * nu = tau (control)
        nu_dot = M_inv * (tau - D * nu)
        """
        pose = state.pose
        vel = state.vel
        
        # Calculate acceleration
        # control is assumed to be forces/moments [tau_u, tau_v, tau_r]
        acc = self.M_inv @ (control - self.params.D @ vel)
        
        # Euler integration for velocity
        next_vel = vel + acc * dt
        
        # Kinematics: eta_dot = R(psi) * nu
        psi = pose[2]
        c = jnp.cos(psi)
        s = jnp.sin(psi)
        R = jnp.array([
            [c, -s, 0],
            [s, c, 0],
            [0, 0, 1]
        ])
        
        pose_dot = R @ vel
        next_pose = pose + pose_dot * dt
        
        return LinearShipState(pose=next_pose, vel=next_vel)

    def reset(self, rng_key: jnp.ndarray) -> LinearShipState:
        return LinearShipState(
            pose=jnp.zeros(3),
            vel=jnp.zeros(3)
        )
