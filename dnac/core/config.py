#!/usr/bin/env python3
"""
Configuration module for loading and saving DNAC configuration.
Author: Steven Coutts
"""
import os
import yaml
from typing import Dict, Any

DEFAULT_CONFIG = {
    'server': {
        'host': 'https://sandboxdnac.cisco.com',
        'port': 443,
        'verify_ssl': False,
        'timeout': 30
    },
    'auth': {
        'username': 'devnetuser',
        'password': 'Cisco123!'
    }
}

def load_config(config_path: str = 'config.yaml') -> Dict[str, Any]:
    """Load configuration from config.yaml file."""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return DEFAULT_CONFIG


def save_config(config: Dict[str, Any], config_path: str = 'config.yaml') -> None:
    """Save configuration to config.yaml file."""
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False) 