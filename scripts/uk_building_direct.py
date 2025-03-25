#!/usr/bin/env python3
"""
Standalone script to create a building under the UK area.
This is a simplified version without UI or complex verification.
"""

import os
import sys
import json
import time
import logging
import requests
import argparse
import yaml  # Add YAML support
from typing import Dict, Any
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='uk_building_direct.log',
    filemode='w'
)

# Add console handler
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s: %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

class SimpleDNAC:
    """Simple DNAC client with just the essentials"""
    def __init__(self, host, username, password, verify=False):
        self.host = host
        self.username = username
        self.password = password
        self.verify = verify
        self.token = None
        self.session = requests.Session()
        self.session.verify = verify
        
        # Get auth token
        self.get_auth_token()
    
    def get_auth_token(self):
        """Get authentication token from DNAC"""
        try:
            url = f"{self.host.rstrip('/')}/dna/system/api/v1/auth/token"
            response = self.session.post(
                url,
                auth=(self.username, self.password),
                verify=self.verify
            )
            response.raise_for_status()
            self.token = response.json()["Token"]
            logging.info("Successfully obtained authentication token")
            return self.token
        except Exception as e:
            logging.error(f"Failed to get auth token: {str(e)}")
            raise

def load_config(config_file=None):
    """Load configuration from file or environment"""
    config = {}
    
    # Try config file first
    if config_file and os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                # Determine file type based on extension
                if config_file.lower().endswith('.yaml') or config_file.lower().endswith('.yml'):
                    config_data = yaml.safe_load(f)
                    logging.info(f"Loaded YAML config from {config_file}")
                else:
                    config_data = json.load(f)
                    logging.info(f"Loaded JSON config from {config_file}")
                
                # Extract credentials from different possible structures
                # Structure 1: Directly at top level
                if 'host' in config_data and 'username' in config_data and 'password' in config_data:
                    config = {
                        'host': config_data.get('host'),
                        'username': config_data.get('username'),
                        'password': config_data.get('password'),
                        'verify': config_data.get('verify', False)
                    }
                # Structure 2: Under 'server' and 'auth'
                elif 'server' in config_data and 'auth' in config_data:
                    config = {
                        'host': config_data.get('server', {}).get('host') or config_data.get('server', {}).get('url'),
                        'username': config_data.get('auth', {}).get('username'),
                        'password': config_data.get('auth', {}).get('password'),
                        'verify': config_data.get('server', {}).get('verify', False)
                    }
                # Special case for just server with host but no auth section
                elif 'server' in config_data and config_data.get('server', {}).get('host'):
                    # Handle case where auth might be outside server section or in environment
                    config = {
                        'host': config_data.get('server', {}).get('host'),
                        'username': config_data.get('username', os.environ.get('DNAC_USERNAME')),
                        'password': config_data.get('password', os.environ.get('DNAC_PASSWORD')),
                        'verify': config_data.get('server', {}).get('verify', False)
                    }
                    logging.info("Found server.host format - will look for credentials elsewhere")
                # Structure 3: Under 'dnac' or 'dna_center'
                elif 'dnac' in config_data:
                    dnac_config = config_data.get('dnac', {})
                    config = {
                        'host': dnac_config.get('host') or dnac_config.get('url'),
                        'username': dnac_config.get('username'),
                        'password': dnac_config.get('password'),
                        'verify': dnac_config.get('verify', False)
                    }
                elif 'dna_center' in config_data:
                    dnac_config = config_data.get('dna_center', {})
                    config = {
                        'host': dnac_config.get('host') or dnac_config.get('url'),
                        'username': dnac_config.get('username'),
                        'password': dnac_config.get('password'),
                        'verify': dnac_config.get('verify', False)
                    }
                
                logging.info(f"Extracted config: host={config.get('host')}, username={config.get('username')}")
        except Exception as e:
            logging.error(f"Error loading config file: {str(e)}")
    
    # Default to config.yaml in the current directory if no file specified
    elif not config_file and os.path.exists("config.yaml"):
        try:
            with open("config.yaml", 'r') as f:
                config_data = yaml.safe_load(f)
                logging.info("Loaded config from default config.yaml")
                
                # Extract credentials (same logic as above)
                # Structure 1: Directly at top level
                if 'host' in config_data and 'username' in config_data and 'password' in config_data:
                    config = {
                        'host': config_data.get('host'),
                        'username': config_data.get('username'),
                        'password': config_data.get('password'),
                        'verify': config_data.get('verify', False)
                    }
                # Structure 2: Under 'server' and 'auth'
                elif 'server' in config_data and 'auth' in config_data:
                    config = {
                        'host': config_data.get('server', {}).get('host') or config_data.get('server', {}).get('url'),
                        'username': config_data.get('auth', {}).get('username'),
                        'password': config_data.get('auth', {}).get('password'),
                        'verify': config_data.get('server', {}).get('verify', False)
                    }
                # Special case for just server with host but no auth section
                elif 'server' in config_data and config_data.get('server', {}).get('host'):
                    # Handle case where auth might be outside server section or in environment
                    config = {
                        'host': config_data.get('server', {}).get('host'),
                        'username': config_data.get('username', os.environ.get('DNAC_USERNAME')),
                        'password': config_data.get('password', os.environ.get('DNAC_PASSWORD')),
                        'verify': config_data.get('server', {}).get('verify', False)
                    }
                    logging.info("Found server.host format - will look for credentials elsewhere")
                # Structure 3: Under 'dnac' or 'dna_center'
                elif 'dnac' in config_data:
                    dnac_config = config_data.get('dnac', {})
                    config = {
                        'host': dnac_config.get('host') or dnac_config.get('url'),
                        'username': dnac_config.get('username'),
                        'password': dnac_config.get('password'),
                        'verify': dnac_config.get('verify', False)
                    }
                elif 'dna_center' in config_data:
                    dnac_config = config_data.get('dna_center', {})
                    config = {
                        'host': dnac_config.get('host') or dnac_config.get('url'),
                        'username': dnac_config.get('username'),
                        'password': dnac_config.get('password'),
                        'verify': dnac_config.get('verify', False)
                    }
                
                logging.info(f"Extracted config: host={config.get('host')}, username={config.get('username')}")
        except Exception as e:
            logging.error(f"Error loading default config.yaml: {str(e)}")

    # Check environment variables
    env_vars = {
        "DNAC_HOST": "host",
        "DNAC_USERNAME": "username",
        "DNAC_PASSWORD": "password",
    }
    
    for env_var, config_key in env_vars.items():
        if env_var in os.environ:
            config[config_key] = os.environ[env_var]
            logging.info(f"Using {config_key} from environment variable")
    
    # Validate config
    required_keys = ["host", "username", "password"]
    missing_keys = [key for key in required_keys if key not in config or not config[key]]
    
    if missing_keys:
        logging.error(f"Missing required configuration: {', '.join(missing_keys)}")
        return None
    
    return config

def get_uk_site_id(dnac):
    """Get the site ID for UK"""
    try:
        # First try to get all sites
        base_url = dnac.host.rstrip('/')
        url = f"{base_url}/dna/intent/api/v1/site"
        
        response = dnac.session.get(
            url,
            headers={"x-auth-token": dnac.token}
        )
        response.raise_for_status()
        
        # Parse the response
        sites_data = response.json()
        logging.debug(f"Sites response: {json.dumps(sites_data, indent=2)}")
        
        # Look for UK in the response
        uk_id = None
        
        # Try different approaches to find UK
        
        # Method 1: Look in response array
        if 'response' in sites_data and isinstance(sites_data['response'], list):
            for site in sites_data['response']:
                if isinstance(site, dict) and site.get('name') == 'UK':
                    uk_id = site.get('id')
                    logging.info(f"Found UK site ID (method 1): {uk_id}")
                    break
                    
                # Also check if UK is in the name
                if isinstance(site, dict) and 'UK' in site.get('name', ''):
                    uk_id = site.get('id')
                    logging.info(f"Found UK site ID (partial match): {uk_id}")
                    break
        
        # Method 2: Try searching for UK specifically
        if not uk_id:
            url = f"{base_url}/dna/intent/api/v1/site?name=UK"
            response = dnac.session.get(
                url,
                headers={"x-auth-token": dnac.token}
            )
            
            if response.status_code == 200:
                uk_data = response.json()
                logging.debug(f"UK search response: {json.dumps(uk_data, indent=2)}")
                
                if 'response' in uk_data and uk_data['response']:
                    if isinstance(uk_data['response'], list) and uk_data['response']:
                        uk_id = uk_data['response'][0].get('id')
                        logging.info(f"Found UK site ID (method 2): {uk_id}")
                    elif isinstance(uk_data['response'], dict):
                        uk_id = uk_data['response'].get('id')
                        logging.info(f"Found UK site ID (method 2 dict): {uk_id}")
        
        if not uk_id:
            logging.error("Could not find UK site ID")
            
        return uk_id
    except Exception as e:
        logging.error(f"Error getting UK site ID: {str(e)}")
        return None

def create_uk_building(dnac, uk_id, building_name):
    """Create a building under UK with minimal payload"""
    try:
        if not uk_id:
            logging.error("Cannot create building without UK site ID")
            return False
            
        # Create minimal building payload
        payload = {
            "type": "building",
            "site": {
                "building": {
                    "name": building_name,
                    "parentId": uk_id,
                    "address": "1 Main Street",
                    "latitude": 51.50853,
                    "longitude": -0.12574,
                    "country": "United Kingdom"
                }
            }
        }
        
        logging.info(f"Creating building '{building_name}' under UK (ID: {uk_id})")
        logging.debug(f"Building payload: {json.dumps(payload, indent=2)}")
        
        # Make API call
        base_url = dnac.host.rstrip('/')
        url = f"{base_url}/dna/intent/api/v1/site"
        
        response = dnac.session.post(
            url,
            headers={
                "x-auth-token": dnac.token,
                "Content-Type": "application/json"
            },
            data=json.dumps(payload)  # Use data with manually serialized JSON
        )
        
        logging.info(f"Response status: {response.status_code}")
        logging.debug(f"Response headers: {dict(response.headers)}")
        logging.debug(f"Response text: {response.text}")
        
        if response.status_code in (200, 201, 202):
            logging.info("Successfully initiated building creation")
            
            # Get execution ID if available
            try:
                response_data = response.json()
                execution_id = response_data.get('executionId')
                
                if execution_id:
                    logging.info(f"Tracking execution ID: {execution_id}")
                    
                    # Wait for completion
                    for attempt in range(5):
                        time.sleep(3)
                        logging.info(f"Checking execution status (attempt {attempt+1})")
                        
                        status_url = f"{base_url}/dna/platform/management/business-api/v1/execution-status/{execution_id}"
                        status_response = dnac.session.get(
                            status_url,
                            headers={"x-auth-token": dnac.token}
                        )
                        
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            logging.debug(f"Status response: {json.dumps(status_data, indent=2)}")
                            
                            status = status_data.get('status', '')
                            logging.info(f"Execution status: {status}")
                            
                            if status.lower() == 'success':
                                logging.info("Building creation successful!")
                                return True
                            elif status.lower() in ('failed', 'error'):
                                logging.error(f"Building creation failed: {status_data.get('bapiError')}")
                                return False
            except Exception as e:
                logging.warning(f"Error checking execution status: {str(e)}")
            
            # If we can't check status or don't have an execution ID, assume success
            return True
        else:
            logging.error(f"Failed to create building: {response.text}")
            return False
    except Exception as e:
        logging.error(f"Error creating building: {str(e)}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Create a building under UK in Cisco DNA Center.')
    parser.add_argument('-c', '--config', help='Path to configuration file')
    parser.add_argument('-n', '--name', required=True, help='Name of the building to create')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--host', help='DNA Center hostname/IP')
    parser.add_argument('--username', help='DNA Center username')
    parser.add_argument('--password', help='DNA Center password')
    
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        console.setLevel(logging.DEBUG)
    
    # Load configuration
    config = load_config(args.config)
    
    # Override with command line args if provided
    if args.host:
        config['host'] = args.host
    if args.username:
        config['username'] = args.username
    if args.password:
        config['password'] = args.password
    
    if not config:
        logging.error("No valid configuration found. Please provide either a config file or environment variables.")
        return 1
    
    try:
        # Initialize DNAC client
        dnac = SimpleDNAC(
            host=config['host'],
            username=config['username'],
            password=config['password'],
            verify=config.get('verify', False)
        )
        
        # Get UK site ID
        uk_id = get_uk_site_id(dnac)
        
        if not uk_id:
            logging.error("Could not find UK site ID. Aborting.")
            return 1
        
        # Create building under UK
        success = create_uk_building(dnac, uk_id, args.name)
        
        if success:
            logging.info(f"Successfully created building '{args.name}' under UK")
            return 0
        else:
            logging.error(f"Failed to create building '{args.name}' under UK")
            return 1
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 