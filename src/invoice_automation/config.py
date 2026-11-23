from typing import Any, Dict

import yaml

# Type alias for the config object: free-form nested mapping
Config = Dict[str, Any]


def load_config(path: str = 'config.yaml') -> Config:
    with open(path, 'r') as f:
        config = yaml.safe_load(f)

    return config
