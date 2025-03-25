#!/usr/bin/env python3
"""
Simple script to add a new site to Cisco Catalyst Centre.
Author: Steven Coutts
"""

import os
import sys
import argparse
import logging
import yaml
import json
import curses
import time
from typing import Dict, Any, Optional, List
import urllib.parse
import requests

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
                
                # Disable SSL verification warnings and verification if verify is False
                if not verify:
                    import urllib3
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                    self.session.verify = False
                
            def login(self):
                """Get authentication token from DNAC"""
                url = f"{self.host.rstrip('/')}/dna/system/api/v1/auth/token"
                try:
                    # Make the request with SSL verification disabled if configured
                    response = self.session.post(
                        url,
                        auth=(self.username, self.password),
                        verify=self.verify
                    )
                    response.raise_for_status()
                    self.token = response.json()["Token"]
                    return self.token
                except requests.exceptions.SSLError as e:
                    logging.error(f"SSL Error: {str(e)}")
                    if not self.verify:
                        logging.warning("SSL verification is disabled. If this is unexpected, check your configuration.")
                    raise
                except requests.exceptions.RequestException as e:
                    logging.error(f"Request failed: {str(e)}")
                    raise

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
    handlers=[
        logging.FileHandler("dnac_add_site.log"),
        logging.StreamHandler()
    ]
)

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
                    
                    # Extract DNAC configuration from the standard format
                    server_config = config.get('server', {})
                    auth_config = config.get('auth', {})
                    
                    # Get verify_ssl setting from both possible locations
                    # Root level takes precedence over server level
                    verify_ssl = config.get('verify_ssl', server_config.get('verify_ssl', True))
                    
                    # If verify_ssl is False, we want verify=False
                    verify = not verify_ssl
                    
                    dnac_config = {
                        'host': server_config.get('host', ''),
                        'username': auth_config.get('username', ''),
                        'password': auth_config.get('password', ''),
                        'verify': verify
                    }
                    
                    # Log SSL verification status
                    if not verify:
                        logging.warning(f"SSL verification is disabled based on configuration (verify_ssl: {verify_ssl})")
                    else:
                        logging.info(f"SSL verification is enabled based on configuration (verify_ssl: {verify_ssl})")
                    
                    return dnac_config
            except Exception as e:
                logging.warning(f"Failed to load config from {path}: {e}")
    
    # If we get here, no config was loaded
    logging.warning("No config file found. Will use environment variables if available.")
    return {}

def get_parent_sites(dnac, parent_id=None, level=0, path=""):
    """Get list of parent sites with their full paths"""
    try:
        # Get sites from DNAC
        response = dnac.session.get(
            f"{dnac.host.rstrip('/')}/dna/intent/api/v1/site",
            headers={'X-Auth-Token': dnac.token},
            verify=dnac.verify
        )
        response.raise_for_status()
        sites = response.json().get('response', [])
        
        # Filter sites by parent ID and build paths
        parent_sites = []
        for site in sites:
            if site.get('parentId') == parent_id:
                site_name = site.get('name', '')
                full_path = f"{path} -> {site_name}" if path else site_name
                parent_sites.append({
                    'id': site.get('id'),
                    'name': site_name,
                    'path': full_path,
                    'level': level
                })
                # Recursively get child sites
                child_sites = get_parent_sites(dnac, site.get('id'), level + 1, full_path)
                parent_sites.extend(child_sites)
        
        return parent_sites
    except Exception as e:
        logging.error(f"Failed to get parent sites: {str(e)}")
        return []

def create_site_data(site_type, site_name, parent_site, parent_id):
    """Create site data structure for API request"""
    logging.info(f"Creating {site_type} '{site_name}' under {parent_site} (ID: {parent_id})")
    
    # Create the payload in the format expected by the API
    if site_type == "area":
        site_data = {
            "type": site_type,
            "site": {
                "area": {
                    "name": site_name,
                    "parentName": parent_site if parent_site else "Global",
                    "parentId": parent_id if parent_id and parent_id != "global" else None,
                    "type": "area"
                }
            }
        }
            
    elif site_type == "building":
        # For buildings, we need special handling for various parent sites
        building_data = {
            "name": site_name,
            "address": "1 Main Street",
            "latitude": "51.50853",  # London coordinates as strings
            "longitude": "-0.12574",
            "country": "United Kingdom",  # Required field
            "city": "London",
            "parentName": parent_site if parent_site else "Global",
            "type": "building"
        }
        
        # Add parentId only if valid (not empty and not "global")
        if parent_id and parent_id.lower() != "global":
            logging.debug(f"Adding parentId '{parent_id}' to building data")
            building_data["parentId"] = parent_id
            # Add siteHierarchy based on parent's hierarchy
            if parent_site == "UK":
                # UK's hierarchy: e5a9d183-53bb-4e34-82e0-421174285ebc/0a364f1b-14e9-4356-8786-799baef3644d/76ab9636-eaf5-4add-8b8e-cfbfddaab3d1
                building_data["siteHierarchy"] = "e5a9d183-53bb-4e34-82e0-421174285ebc/0a364f1b-14e9-4356-8786-799baef3644d/76ab9636-eaf5-4add-8b8e-cfbfddaab3d1"
        else:
            logging.debug(f"Using only parentName '{parent_site}' for building (no valid parentId)")
        
        # Create the site data structure
        site_data = {
            "type": site_type,
            "site": {
                "building": building_data
            }
        }
        
    elif site_type == "floor":
        site_data = {
            "type": site_type,
            "site": {
                "floor": {
                    "name": site_name,
                    "parentName": parent_site if parent_site else "Global",
                    "rfModel": "Cubes And Walled Offices",
                    "width": "100",
                    "length": "100",
                    "height": "10",
                    "type": "floor"
                }
            }
        }
        # Add parentId if available (more reliable than parentName)
        if parent_id and parent_id != "global":
            site_data["site"]["floor"]["parentId"] = parent_id
    else:
        site_data = {}
    
    # Log the final site data for debugging
    logging.debug(f"Final site data: {json.dumps(site_data, indent=2)}")
    
    return site_data

def create_site(dnac, site_data):
    """Create a site using the DNAC API"""
    try:
        # Create the site using direct API call
        base_url = dnac.host.rstrip('/')
        api_url = f"{base_url}/dna/intent/api/v1/site"
        
        headers = {
            "x-auth-token": dnac.token,
            "Content-Type": "application/json"
        }
        
        # Log request details
        logging.info(f"Creating site with URL: {api_url}")
        logging.info(f"Headers: {headers}")
        logging.info(f"Site data: {json.dumps(site_data, indent=2)}")
        
        # Make the request
        response = dnac.session.post(
            api_url,
            headers=headers,
            json=site_data,
            timeout=30
        )
        
        # Log detailed response information
        logging.info(f"Response status code: {response.status_code}")
        logging.info(f"Response headers: {dict(response.headers)}")
        
        try:
            response_json = response.json()
            logging.info(f"Response body: {json.dumps(response_json, indent=2)}")
            
            # Check for error messages in the response
            if 'error' in response_json:
                logging.error(f"Error in response: {response_json['error']}")
                print(f"Error creating site: {response_json['error']}")
                return response
                
            # Check for executionStatus in the response
            if 'executionStatus' in response_json:
                logging.info(f"Execution status: {response_json['executionStatus']}")
                if response_json['executionStatus'] == 'FAILURE':
                    error_msg = response_json.get('failureReason', 'Unknown error')
                    logging.error(f"Site creation failed: {error_msg}")
                    print(f"Site creation failed: {error_msg}")
                    return response
        except json.JSONDecodeError:
            logging.warning(f"Response body is not JSON: {response.text}")
        
        # Check if the request was successful
        if response.status_code in (200, 201, 202):
            print(f"Site creation request successful. Status code: {response.status_code}")
            
            # Get the site name and type from the request data
            site_name = None
            site_type = site_data.get('type', '')
            
            if site_type == 'area':
                site_name = site_data.get('site', {}).get('area', {}).get('name')
            elif site_type == 'building':
                site_name = site_data.get('site', {}).get('building', {}).get('name')
            elif site_type == 'floor':
                site_name = site_data.get('site', {}).get('floor', {}).get('name')
            
            if site_name:
                print(f"Verifying site creation for {site_type} '{site_name}'...")
                
                # Get the parent ID from the site data
                parent_id = None
                if site_type == 'area':
                    parent_id = site_data.get('site', {}).get('area', {}).get('parentId')
                elif site_type == 'building':
                    parent_id = site_data.get('site', {}).get('building', {}).get('parentId')
                elif site_type == 'floor':
                    parent_id = site_data.get('site', {}).get('floor', {}).get('parentId')
                
                logging.info(f"Verifying site creation with parameters:")
                logging.info(f"  Site name: {site_name}")
                logging.info(f"  Site type: {site_type}")
                logging.info(f"  Parent ID: {parent_id}")
                
                # Verify the site was created
                if verify_site_creation(dnac, site_name, site_type, parent_id):
                    print(f"Successfully created {site_type} '{site_name}'")
                else:
                    print(f"Warning: Site creation may have succeeded but verification failed.")
            else:
                print("Warning: Could not determine site name for verification")
        else:
            print(f"Failed to create site. Status code: {response.status_code}")
            print(f"Response: {response.text}")
        
        return response
        
    except Exception as e:
        logging.error(f"Error creating site: {str(e)}")
        print(f"Error creating site: {str(e)}")
        raise

def verify_site_creation(dnac, site_name, site_type, parent_id=None, max_attempts=30):
    """Verify that a site was created successfully"""
    try:
        base_url = dnac.host.rstrip('/')
        verify_found = False
        
        for attempt in range(max_attempts):
            logging.info(f"Verification attempt {attempt + 1}/{max_attempts}")
            
            # Method 1: Check site list
            try:
                verify_url = f"{base_url}/dna/intent/api/v1/site"
                logging.info(f"Method 1: Checking site list at {verify_url}")
                
                verify_response = dnac.session.get(
                    verify_url,
                    headers={"x-auth-token": dnac.token},
                    timeout=10
                )
                
                logging.info(f"Site list response status: {verify_response.status_code}")
                try:
                    verify_data = verify_response.json()
                    logging.info(f"Site list response: {json.dumps(verify_data, indent=2)}")
                except json.JSONDecodeError:
                    logging.warning(f"Site list response is not JSON: {verify_response.text}")
                
                if verify_response.status_code == 200:
                    verify_data = verify_response.json()
                    
                    if 'response' in verify_data and isinstance(verify_data['response'], list):
                        for site in verify_data['response']:
                            if site.get('name') == site_name:
                                logging.info(f"Site '{site_name}' found in site list!")
                                logging.info(f"Site details: {json.dumps(site, indent=2)}")
                                return True
            except Exception as e:
                logging.warning(f"Error in verification method 1: {str(e)}")
            
            # Method 2: Try getting site by name
            if not verify_found:
                try:
                    encoded_name = urllib.parse.quote(site_name)
                    verify_url = f"{base_url}/dna/intent/api/v1/site?name={encoded_name}"
                    logging.info(f"Method 2: Checking site by name at {verify_url}")
                    
                    verify_response = dnac.session.get(
                        verify_url,
                        headers={"x-auth-token": dnac.token},
                        timeout=10
                    )
                    
                    logging.info(f"Site by name response status: {verify_response.status_code}")
                    try:
                        verify_data = verify_response.json()
                        logging.info(f"Site by name response: {json.dumps(verify_data, indent=2)}")
                    except json.JSONDecodeError:
                        logging.warning(f"Site by name response is not JSON: {verify_response.text}")
                    
                    if verify_response.status_code == 200:
                        verify_data = verify_response.json()
                        if 'response' in verify_data:
                            response_obj = verify_data['response']
                            if isinstance(response_obj, list):
                                for site in response_obj:
                                    if site.get('name') == site_name:
                                        logging.info(f"Site '{site_name}' found in name query!")
                                        logging.info(f"Site details: {json.dumps(site, indent=2)}")
                                        return True
                            elif isinstance(response_obj, dict):
                                if response_obj.get('name') == site_name:
                                    logging.info(f"Site '{site_name}' found in name query!")
                                    logging.info(f"Site details: {json.dumps(response_obj, indent=2)}")
                                    return True
                except Exception as e:
                    logging.warning(f"Error in verification method 2: {str(e)}")
            
            # Method 3: Check parent site if available
            if not verify_found and parent_id and parent_id != "global":
                try:
                    verify_url = f"{base_url}/dna/intent/api/v1/site/{parent_id}"
                    logging.info(f"Method 3: Checking parent site at {verify_url}")
                    
                    verify_response = dnac.session.get(
                        verify_url,
                        headers={"x-auth-token": dnac.token},
                        timeout=10
                    )
                    
                    logging.info(f"Parent site response status: {verify_response.status_code}")
                    try:
                        verify_data = verify_response.json()
                        logging.info(f"Parent site response: {json.dumps(verify_data, indent=2)}")
                    except json.JSONDecodeError:
                        logging.warning(f"Parent site response is not JSON: {verify_response.text}")
                    
                    if verify_response.status_code == 200:
                        verify_data = verify_response.json()
                        if site_name in json.dumps(verify_data):
                            logging.info(f"Site '{site_name}' found in parent data!")
                            return True
                except Exception as e:
                    logging.warning(f"Error in verification method 3: {str(e)}")
            
            # Wait before next attempt
            if attempt < max_attempts - 1:
                logging.info("Waiting 3 seconds before next verification attempt...")
                time.sleep(3)
        
        logging.error(f"Failed to verify site creation after {max_attempts} attempts")
        return False
        
    except Exception as e:
        logging.error(f"Error during site verification: {str(e)}")
        return False

def show_menu(stdscr):
    """Show the main menu and get user selection"""
    stdscr.clear()
    stdscr.addstr(0, 0, "Cisco Catalyst Centre - Site Creation")
    stdscr.addstr(1, 0, "=" * 50)
    stdscr.addstr(2, 0, "1. Create Area")
    stdscr.addstr(3, 0, "2. Create Building")
    stdscr.addstr(4, 0, "3. Create Floor")
    stdscr.addstr(5, 0, "4. Exit")
    stdscr.addstr(7, 0, "Enter your choice (1-4): ")
    stdscr.refresh()
    
    while True:
        key = stdscr.getch()
        if key in [ord('1'), ord('2'), ord('3'), ord('4')]:
            return chr(key)
        elif key == ord('q'):
            return '4'

def get_input(stdscr, prompt, y, x):
    """Get input from user at specified position"""
    curses.echo()
    stdscr.addstr(y, x, prompt)
    stdscr.refresh()
    
    # Get input
    input_str = ""
    while True:
        key = stdscr.getch()
        if key == ord('\n'):
            break
        elif key == curses.KEY_BACKSPACE or key == 127:
            if input_str:
                input_str = input_str[:-1]
                stdscr.addstr(y, x + len(prompt), " " * (len(input_str) + 1))
                stdscr.addstr(y, x + len(prompt), input_str)
                stdscr.refresh()
        else:
            input_str += chr(key)
            stdscr.addstr(y, x + len(prompt), input_str)
            stdscr.refresh()
    
    curses.noecho()
    return input_str.strip()

def show_message(stdscr, message, y, x):
    """Show a message at specified position"""
    stdscr.addstr(y, x, message)
    stdscr.refresh()
    time.sleep(2)

def get_parent_site_selection(stdscr, parent_sites):
    """Get parent site selection from user"""
    stdscr.clear()
    stdscr.addstr(0, 0, "Select parent site:")
    stdscr.addstr(1, 0, "=" * 50)
    
    # Show available sites with numbers
    for i, site in enumerate(parent_sites):
        stdscr.addstr(i + 2, 0, f"{i + 1}. {site['name']}")
    
    # Show instructions
    stdscr.addstr(len(parent_sites) + 2, 0, "=" * 50)
    stdscr.addstr(len(parent_sites) + 3, 0, "Enter number (1-{}) or 'q' to cancel: ".format(len(parent_sites)))
    stdscr.refresh()
    
    # Get input
    input_str = ""
    while True:
        key = stdscr.getch()
        if key == ord('q'):
            return None
        elif key == ord('\n'):
            try:
                selection = int(input_str)
                if 1 <= selection <= len(parent_sites):
                    return parent_sites[selection - 1]
            except ValueError:
                pass
        elif key == curses.KEY_BACKSPACE or key == 127:
            if input_str:
                input_str = input_str[:-1]
                stdscr.addstr(len(parent_sites) + 3, 0, "Enter number (1-{}) or 'q' to cancel: ".format(len(parent_sites)))
                stdscr.addstr(len(parent_sites) + 3, len("Enter number (1-{}) or 'q' to cancel: ".format(len(parent_sites))), input_str)
                stdscr.refresh()
        elif chr(key).isdigit():
            input_str += chr(key)
            stdscr.addstr(len(parent_sites) + 3, len("Enter number (1-{}) or 'q' to cancel: ".format(len(parent_sites))), input_str)
            stdscr.refresh()

def main():
    parser = argparse.ArgumentParser(description='Add sites to DNA Center')
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
        verify = config.get('verify', False)
        
        if not all([host, username, password]):
            logging.error("Missing required configuration. Please provide host, username, and password.")
            print("ERROR: Missing DNA Center configuration. Please provide host, username, and password.")
            print("You can do this via a config file, environment variables, or the DNAC_CONFIG_FILE environment variable.")
            return 1
        
        # Initialize DNAC client with SSL verification disabled
        dnac = DNAC(
            host=host,
            username=username,
            password=password,
            verify=False  # Always disable SSL verification for now
        )
        
        # Log in to get token
        try:
            token = dnac.login()
            print(f"Successfully authenticated to DNAC at {host}")
        except Exception as e:
            logging.error(f"Authentication failed: {str(e)}")
            print(f"Authentication failed: {str(e)}")
            if "SSL" in str(e):
                print("\nNote: If you're using a self-signed certificate, make sure 'verify_ssl: false' is set in your config.yaml")
            return 1
        
        while True:
            print("\nDNA Center Site Management")
            print("1. Add Area")
            print("2. Add Building")
            print("3. Add Floor")
            print("4. Exit")
            
            choice = input("\nEnter your choice (1-4): ")
            
            if choice == '1':
                # Get parent sites for area
                parent_sites = get_parent_sites(dnac)
                if not parent_sites:
                    print("No parent sites found. Please create a parent site first.")
                    continue
                
                print("\nAvailable parent sites:")
                for i, site in enumerate(parent_sites, 1):
                    print(f"{i}. {site['path']}")
                
                parent_choice = input("\nEnter the number of the parent site: ")
                try:
                    parent_index = int(parent_choice) - 1
                    if 0 <= parent_index < len(parent_sites):
                        parent_site = parent_sites[parent_index]
                        name = input("Enter area name: ")
                        site_data = create_site_data("area", name, parent_site['name'], parent_site['id'])
                        create_site(dnac, site_data)
                    else:
                        print("Invalid choice")
                except ValueError:
                    print("Please enter a valid number")
            
            elif choice == '2':
                # Get parent sites for building
                parent_sites = get_parent_sites(dnac)
                if not parent_sites:
                    print("No parent sites found. Please create a parent site first.")
                    continue
                
                print("\nAvailable parent sites:")
                for i, site in enumerate(parent_sites, 1):
                    print(f"{i}. {site['path']}")
                
                parent_choice = input("\nEnter the number of the parent site: ")
                try:
                    parent_index = int(parent_choice) - 1
                    if 0 <= parent_index < len(parent_sites):
                        parent_site = parent_sites[parent_index]
                        name = input("Enter building name: ")
                        site_data = create_site_data("building", name, parent_site['name'], parent_site['id'])
                        create_site(dnac, site_data)
                    else:
                        print("Invalid choice")
                except ValueError:
                    print("Please enter a valid number")
            
            elif choice == '3':
                # Get parent sites for floor
                parent_sites = get_parent_sites(dnac)
                if not parent_sites:
                    print("No parent sites found. Please create a parent site first.")
                    continue
                
                print("\nAvailable parent sites:")
                for i, site in enumerate(parent_sites, 1):
                    print(f"{i}. {site['path']}")
                
                parent_choice = input("\nEnter the number of the parent site: ")
                try:
                    parent_index = int(parent_choice) - 1
                    if 0 <= parent_index < len(parent_sites):
                        parent_site = parent_sites[parent_index]
                        name = input("Enter floor name: ")
                        site_data = create_site_data("floor", name, parent_site['name'], parent_site['id'])
                        create_site(dnac, site_data)
                    else:
                        print("Invalid choice")
                except ValueError:
                    print("Please enter a valid number")
            
            elif choice == '4':
                print("Goodbye!")
                break
            
            else:
                print("Invalid choice. Please try again.")

    except Exception as e:
        logging.error(f"Error: {str(e)}")
        print(f"Error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    main() 