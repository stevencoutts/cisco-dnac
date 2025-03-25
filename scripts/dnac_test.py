#!/usr/bin/env python3
"""
Test script for DNAC connectivity and authentication.
"""

import os
import sys
import argparse
import logging
import yaml
import json
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
    handlers=[
        logging.FileHandler("dnac_test.log"),
        logging.StreamHandler()
    ]
)

# Try to import from dnac module
try:
    from dnac.core.api import Dnac as DNAC  # Try importing Dnac as DNAC
except ImportError:
    try:
        # Alternative import if the class name is different
        from dnac.core.api import DNACenter as DNAC
    except ImportError:
        # If both fail, provide a fallback implementation
        class DNAC:
            def __init__(self, host, username=None, password=None, verify=True):
                self.host = host
                self.username = username
                self.password = password
                self.verify = verify
                self.token = None
                self.session = requests.Session()
                self.session.verify = verify
                
            def login(self):
                """Get authentication token from DNAC"""
                url = f"{self.host.rstrip('/')}/dna/system/api/v1/auth/token"
                response = self.session.post(
                    url,
                    auth=(self.username, self.password),
                    verify=self.verify
                )
                response.raise_for_status()
                self.token = response.json()["Token"]
                return self.token

def load_dnac_config(config_file=None):
    """Load DNAC configuration from a file"""
    # Default config paths to try
    default_paths = [
        config_file,                         # First try the provided config file
        os.environ.get('DNAC_CONFIG_FILE'),  # Then try env var
        'config.yaml',                       # Then try config.yaml in current dir
        'dnac_config.yaml',                  # Then try dnac_config.yaml
        'config.json',                       # Then try config.json
        os.path.expanduser('~/.dnac.yaml'),  # Finally try .dnac.yaml in home dir
    ]
    
    # Filter out None values
    paths_to_try = [p for p in default_paths if p]
    
    # Try each path
    for path in paths_to_try:
        if os.path.exists(path):
            logging.info(f"Loading config from {path}")
            try:
                with open(path, 'r') as f:
                    # Determine file type based on extension
                    if path.lower().endswith(('.yaml', '.yml')):
                        config = yaml.safe_load(f)
                        logging.info(f"Loaded YAML config from {path}")
                    else:
                        config = json.load(f)
                        logging.info(f"Loaded JSON config from {path}")
                    
                    return config
            except Exception as e:
                logging.warning(f"Failed to load config from {path}: {e}")
    
    # If we get here, no config was loaded
    logging.warning("No config file found. Will use environment variables if available.")
    return {}

def main():
    parser = argparse.ArgumentParser(description='Test DNAC connectivity')
    parser.add_argument('-c', '--config', help='Path to DNA Center config file')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug output')
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.getLogger().setLevel(log_level)
    
    try:
        # Load config
        config = load_dnac_config(args.config)
        
        # Get config from environment if not in file
        host = config.get('host') or os.environ.get('DNAC_HOST')
        username = config.get('username') or os.environ.get('DNAC_USERNAME')
        password = config.get('password') or os.environ.get('DNAC_PASSWORD')
        
        if not all([host, username, password]):
            logging.error("Missing required configuration. Please provide host, username, and password.")
            print("ERROR: Missing DNA Center configuration. Please provide host, username, and password.")
            print("You can do this via a config file, environment variables, or the DNAC_CONFIG_FILE environment variable.")
            return 1
        
        # Initialize DNAC client
        dnac = DNAC(
            host=host,
            username=username,
            password=password,
            verify=False
        )
        
        # Log in to get token
        try:
            token = dnac.login()
            print(f"Successfully authenticated to DNAC at {host}")
        except Exception as e:
            logging.error(f"Authentication failed: {str(e)}")
            print(f"Authentication failed: {str(e)}")
            return 1
        
        # Print success message
        print("DNAC import and authentication successful")
        
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        print(f"Error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    main() 