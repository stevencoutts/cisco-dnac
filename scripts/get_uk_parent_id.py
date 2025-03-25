#!/usr/bin/env python3
"""
Script to retrieve the UK site ID from DNA Center.
This tool helps diagnose issues with finding the correct parent ID for the UK.
"""

import os
import sys
import json
import logging
import requests
import argparse
import yaml  # Add YAML support
from pprint import pprint

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='uk_parent_id.log',
    filemode='w'
)

# Add console handler
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s: %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

def get_auth_token(host, username, password, verify=False):
    """Get authentication token from DNAC"""
    try:
        url = f"{host.rstrip('/')}/dna/system/api/v1/auth/token"
        session = requests.Session()
        session.verify = verify
        
        response = session.post(
            url,
            auth=(username, password),
            verify=verify
        )
        response.raise_for_status()
        token = response.json()["Token"]
        logging.info("Successfully obtained authentication token")
        return token, session
    except Exception as e:
        logging.error(f"Failed to get auth token: {str(e)}")
        raise

def get_parent_id_method1(host, session, token):
    """Get UK ID using method 1: Search all sites"""
    url = f"{host.rstrip('/')}/dna/intent/api/v1/site"
    
    try:
        response = session.get(
            url,
            headers={"x-auth-token": token}
        )
        response.raise_for_status()
        
        data = response.json()
        print("\n==== METHOD 1: SEARCHING ALL SITES ====")
        
        if 'response' in data and isinstance(data['response'], list):
            print(f"Found {len(data['response'])} sites")
            
            # Print all sites for reference
            print("\nSite List:")
            for site in data['response']:
                if isinstance(site, dict):
                    name = site.get('name', 'Unknown')
                    site_id = site.get('id', 'No ID')
                    site_type = site.get('siteType', 'Unknown')
                    print(f" - {name} (ID: {site_id}, Type: {site_type})")
            
            # Find sites with UK in the name
            print("\nUK Matches:")
            for site in data['response']:
                if isinstance(site, dict) and 'UK' in site.get('name', ''):
                    name = site.get('name', 'Unknown')
                    site_id = site.get('id', 'No ID')
                    site_type = site.get('siteType', 'Unknown')
                    print(f" - {name} (ID: {site_id}, Type: {site_type})")
                    
                    # Print detailed info for UK sites
                    print("\nDetailed UK Site Info:")
                    pprint(site)
        else:
            print("No sites found or unexpected response format")
            print("Response structure:")
            pprint(data)
    
    except Exception as e:
        print(f"ERROR in Method 1: {str(e)}")
        logging.error(f"Error in method 1: {str(e)}")

def get_parent_id_method2(host, session, token):
    """Get UK ID using method 2: Direct name search"""
    url = f"{host.rstrip('/')}/dna/intent/api/v1/site?name=UK"
    
    try:
        response = session.get(
            url,
            headers={"x-auth-token": token}
        )
        
        print("\n==== METHOD 2: DIRECT NAME SEARCH ====")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("Response Data:")
            pprint(data)
            
            if 'response' in data and data['response']:
                if isinstance(data['response'], list):
                    for item in data['response']:
                        if isinstance(item, dict):
                            print(f"\nFound UK site (list item):")
                            print(f"Name: {item.get('name')}")
                            print(f"ID: {item.get('id')}")
                            print(f"Type: {item.get('siteType')}")
                elif isinstance(data['response'], dict):
                    print(f"\nFound UK site (dict):")
                    print(f"Name: {data['response'].get('name')}")
                    print(f"ID: {data['response'].get('id')}")
                    print(f"Type: {data['response'].get('siteType')}")
            else:
                print("No UK site found in the response")
        else:
            print(f"Error response: {response.text}")
    
    except Exception as e:
        print(f"ERROR in Method 2: {str(e)}")
        logging.error(f"Error in method 2: {str(e)}")

def get_parent_id_method3(host, session, token):
    """Get UK ID using method 3: Get site hierarchy"""
    url = f"{host.rstrip('/')}/dna/intent/api/v1/site-hierarchy"
    
    try:
        response = session.get(
            url,
            headers={"x-auth-token": token}
        )
        
        print("\n==== METHOD 3: SITE HIERARCHY ====")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Search for UK in the hierarchy
            def find_uk_in_hierarchy(node, path=None):
                if path is None:
                    path = []
                
                if not isinstance(node, dict):
                    return
                
                name = node.get('name', '')
                node_id = node.get('id', '')
                node_type = node.get('siteType', '')
                current_path = path + [name]
                
                if 'UK' in name:
                    print(f"\nFound UK in hierarchy:")
                    print(f"Name: {name}")
                    print(f"ID: {node_id}")
                    print(f"Type: {node_type}")
                    print(f"Path: {' > '.join(current_path)}")
                    print("Full node data:")
                    pprint(node)
                
                # Recursively search children
                children = node.get('children', [])
                for child in children:
                    find_uk_in_hierarchy(child, current_path)
            
            # Start search from the root
            if 'response' in data:
                print("Searching hierarchy for UK...")
                find_uk_in_hierarchy(data['response'])
            else:
                print("Unexpected response format")
                print("Response structure:")
                pprint(data)
        else:
            print(f"Error response: {response.text}")
    
    except Exception as e:
        print(f"ERROR in Method 3: {str(e)}")
        logging.error(f"Error in method 3: {str(e)}")

def get_parent_id_method4(host, session, token):
    """Get UK ID using method 4: Try different UK name variations"""
    base_url = host.rstrip('/')
    
    print("\n==== METHOD 4: UK NAME VARIATIONS ====")
    
    # Try different variations of UK site names
    variations = [
        "UK",
        "United Kingdom",
        "UK/",
        "Europe/UK",
        "Global/Europe/UK",
        "%UK%"  # Wildcard search if supported
    ]
    
    for variation in variations:
        try:
            encoded_name = variation
            url = f"{base_url}/dna/intent/api/v1/site?name={encoded_name}"
            
            print(f"\nTrying name variation: '{variation}'")
            response = session.get(
                url,
                headers={"x-auth-token": token}
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if we got a response
                if 'response' in data and data['response']:
                    print(f"Found match for '{variation}'")
                    
                    if isinstance(data['response'], list):
                        for item in data['response']:
                            site_name = item.get('name', 'Unknown')
                            site_id = item.get('id', 'No ID')
                            site_type = item.get('siteType', 'Unknown')
                            print(f" - {site_name} (ID: {site_id}, Type: {site_type})")
                    else:
                        site_name = data['response'].get('name', 'Unknown')
                        site_id = data['response'].get('id', 'No ID')
                        site_type = data['response'].get('siteType', 'Unknown')
                        print(f" - {site_name} (ID: {site_id}, Type: {site_type})")
                else:
                    print(f"No matches for '{variation}'")
        
        except Exception as e:
            print(f"Error trying '{variation}': {str(e)}")

def load_config(config_file=None):
    """Load configuration from file or environment"""
    config = {}
    
    # Try config file if provided
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
                config = extract_config(config_data)
        except Exception as e:
            logging.error(f"Error loading config file: {str(e)}")
    
    # Try default config.yaml if no file specified
    elif not config_file and os.path.exists("config.yaml"):
        try:
            with open("config.yaml", 'r') as f:
                config_data = yaml.safe_load(f)
                logging.info("Loaded config from default config.yaml")
                
                # Extract credentials
                config = extract_config(config_data)
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
    
    return config

def extract_config(config_data):
    """Extract DNA Center configuration from various formats"""
    config = {}
    
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
    return config

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Get UK site ID from Cisco DNA Center.')
    parser.add_argument('-c', '--config', help='Path to configuration file')
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
    
    # Validate config
    required_keys = ["host", "username", "password"]
    missing_keys = [key for key in required_keys if key not in config or not config[key]]
    
    if missing_keys:
        logging.error(f"Missing required configuration: {', '.join(missing_keys)}")
        print(f"ERROR: Missing required configuration: {', '.join(missing_keys)}")
        print("Please provide host, username, and password via config file, environment variables, or command line arguments.")
        return 1
    
    try:
        # Get auth token
        token, session = get_auth_token(
            host=config['host'],
            username=config['username'],
            password=config['password'],
            verify=config.get('verify', False)
        )
        
        # Try all methods to get UK site ID
        get_parent_id_method1(config['host'], session, token)
        get_parent_id_method2(config['host'], session, token)
        get_parent_id_method3(config['host'], session, token)
        get_parent_id_method4(config['host'], session, token)
        
        print("\nComplete! Check the log file for more details: uk_parent_id.log")
        return 0
    
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        print(f"ERROR: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 