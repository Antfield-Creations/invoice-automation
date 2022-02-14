from typing import Dict, Union

import yaml

# Type alias for the config object
# Three-level max nesting of str -> str -> str
Config = Dict[str, Union[str, Dict[str, Dict[str, str]]]]


def load_config(path: str = 'config.yaml') -> Config:
    with open(path, 'r') as f:
        config = yaml.safe_load(f)

    return config
