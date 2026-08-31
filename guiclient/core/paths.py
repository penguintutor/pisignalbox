import os
from pathlib import Path

# Static application paths
ROOT_DIR = Path(__file__).resolve().parent.parent
RESOURCES_DIR = ROOT_DIR / "resources"

# Dynamic data path with an environment variable override
env_data_dir = os.getenv("PISIGNALBOX_DATA_DIR")

if env_data_dir:
    # User or maintainer has overridden the path
    DATA_DIR = Path(env_data_dir)
else:
    # Fallback to the default local directory
    DATA_DIR = ROOT_DIR / "data"

# Ensure the directory actually exists 
# If not create
DATA_DIR.mkdir(parents=True, exist_ok=True)