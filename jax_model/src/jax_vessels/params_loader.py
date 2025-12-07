import json
import jax.numpy as jnp
from pathlib import Path
from .linear_model import LinearShipParams

def load_params_from_json(json_path: Path) -> LinearShipParams:
    """
    Loads ship parameters from a JSON file.
    
    Expected JSON structure:
    {
        "M": [[...], ...],
        "D": [[...], ...]
    }
    """
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    return LinearShipParams(
        M=jnp.array(data["M"]),
        D=jnp.array(data["D"])
    )
