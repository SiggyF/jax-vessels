import click
import yaml
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command()
@click.option("--config", required=True, type=click.Path(exists=True, path_type=Path), help="Path to config.yaml")
@click.option("--hull", required=True, type=str, help="Hull name key in config")
@click.option("--output", required=True, type=click.Path(path_type=Path), help="Output JSON profile")
def main(config, hull, output):
    """Extracts a specific hull profile from config.yaml."""
    try:
        with open(config, 'r') as f:
            cfg = yaml.safe_load(f)
        
        specs = cfg.get("hull_specs", {})
        if hull not in specs:
            raise KeyError(f"Hull '{hull}' not found in hull_specs")
        
        profile_data = specs[hull]
        # Add the name to the profile
        profile_data["name"] = hull

        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, 'w') as f:
            json.dump(profile_data, f, indent=2)
            
        logger.info(f"Exported profile for {hull} to {output}")

    except Exception as e:
        logger.error(f"Failed to dump profile: {e}")
        exit(1)

if __name__ == "__main__":
    main()
