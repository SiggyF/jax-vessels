import abc
import jax.numpy as jnp
from typing import Any, Protocol, Tuple

class ShipModel(Protocol):
    """Protocol defining the interface for ship models."""

    @abc.abstractmethod
    def step(self, state: Any, control: Any, dt: float) -> Any:
        """
        Advances the simulation by one time step.

        Args:
            state: Current state of the ship.
            control: Control inputs (e.g., rudder angle, propeller speed).
            dt: Time step duration.

        Returns:
            Next state of the ship.
        """
        ...

    @abc.abstractmethod
    def reset(self, rng_key: Any) -> Any:
        """
        Resets the simulation to an initial state.

        Args:
            rng_key: JAX random number generator key.

        Returns:
            Initial state.
        """
        ...
