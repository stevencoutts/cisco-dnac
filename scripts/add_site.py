#!/usr/bin/env python3
"""
Script to add a new site to Cisco Catalyst Centre.
Author: Steven Coutts
"""

import os
import sys
import argparse
import logging
import yaml
import json
from typing import Dict, Any, Optional, List

from dnac.core.api import Dnac

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s"
)

DEFAULT_CONFIG_FILE = "config.yaml"


def load_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from file."""
    if config_file is None:
        config_file = DEFAULT_CONFIG_FILE

    if not os.path.exists(config_file):
        print(f"Config file {config_file} not found")
        sys.exit(1)

    with open(config_file) as f:
        return yaml.safe_load(f)


def get_site_type():
    """Get the site type from user input."""
    while True:
        print("\nSite Type:")
        print("1. Area")
        print("2. Building")
        print("3. Floor")
        choice = input("Select site type (1-3): ")
        
        if choice == "1":
            return "area"
        elif choice == "2":
            return "building"
        elif choice == "3":
            return "floor"
        else:
            print("Invalid choice. Please select 1, 2, or 3.")


def get_parent_sites(dnac):
    """Get available parent sites from DNAC."""
    try:
        print("\nFetching available sites...")
        response = dnac.get("site", ver="v1")
        
        if hasattr(response, 'response') and hasattr(response.response, 'json'):
            sites_data = response.response.json()
            
            # Handle response format
            if isinstance(sites_data, dict) and 'response' in sites_data:
                sites_data = sites_data['response']
                
            # Build list of available sites
            available_sites = []
            
            # Add Global as first option
            available_sites.append({"name": "Global", "id": "global", "parentId": None})
            
            if isinstance(sites_data, list):
                for site in sites_data:
                    if 'name' in site and 'id' in site:
                        available_sites.append({
                            "name": site['name'],
                            "id": site['id'],
                            "parentId": site.get('parentId')
                        })
            
            return available_sites
            
    except Exception as e:
        print(f"Error fetching sites: {e}")
        return []


def select_parent_site(sites):
    """Let user select a parent site."""
    if not sites:
        print("No parent sites available. Using Global.")
        return "global", "Global"
        
    print("\nAvailable Parent Sites:")
    for i, site in enumerate(sites):
        print(f"{i+1}. {site['name']}")
        
    while True:
        choice = input(f"Select parent site (1-{len(sites)}): ")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(sites):
                return sites[idx]['id'], sites[idx]['name']
            else:
                print(f"Please enter a number between 1 and {len(sites)}")
        except ValueError:
            print("Please enter a valid number")


def create_site_data(site_type, site_name, parent_name, latitude=None, longitude=None, address=None, floor_number=None, rf_model=None):
    """Create the site data payload."""
    site_data = {
        "site": {
            site_type: {
                "name": site_name,
                "parentName": parent_name
            }
        }
    }
    
    # Add additional building attributes
    if site_type == "building" and (latitude or longitude or address):
        if latitude and longitude:
            site_data["site"]["building"]["latitude"] = float(latitude)
            site_data["site"]["building"]["longitude"] = float(longitude)
        if address:
            site_data["site"]["building"]["address"] = address
            
    # Add additional floor attributes
    if site_type == "floor" and (floor_number or rf_model):
        if floor_number:
            site_data["site"]["floor"]["floorNumber"] = int(floor_number)
        if rf_model:
            site_data["site"]["floor"]["rfModel"] = rf_model
    
    return site_data


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="Add a new site to Cisco Catalyst Centre")
    parser.add_argument("-c", "--config", help=f"Config file (default: {DEFAULT_CONFIG_FILE})")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("urllib3.connectionpool").setLevel(logging.DEBUG)

    # Load configuration
    config = load_config(args.config)
    
    # Extract nested configuration values
    server_config = config.get("server", {})
    hostname = server_config.get("host")
    verify = server_config.get("verify_ssl", False)
    
    auth_config = config.get("auth", {})
    username = auth_config.get("username")
    password = auth_config.get("password")
    
    if not all([hostname, username, password]):
        print("Missing required configuration: hostname, username, or password")
        sys.exit(1)
    
    # Initialize DNAC client
    dnac = Dnac(hostname)
    
    # Set SSL verification
    dnac.verify = verify

    try:
        # Login and get token
        dnac.login(username, password)
        print("Successfully authenticated to Catalyst Centre")
        
        # Get available sites
        available_sites = get_parent_sites(dnac)
        
        # Get site type
        site_type = get_site_type()
        
        # Get site name
        site_name = input("\nEnter site name: ")
        if not site_name:
            print("Site name is required")
            sys.exit(1)
            
        # Select parent site
        parent_id, parent_name = select_parent_site(available_sites)
        
        # Get additional attributes based on site type
        additional_attrs = {}
        
        if site_type == "building":
            print("\nBuilding attributes (optional):")
            additional_attrs["latitude"] = input("Latitude: ")
            additional_attrs["longitude"] = input("Longitude: ")
            additional_attrs["address"] = input("Address: ")
            
        elif site_type == "floor":
            print("\nFloor attributes (optional):")
            additional_attrs["floor_number"] = input("Floor Number: ")
            
            print("\nRF Model options:")
            print("1. Indoor High Ceiling")
            print("2. Outdoor Open Space")
            print("3. Indoor Low Ceiling")
            print("4. Cubes And Walled Offices")
            rf_choice = input("Select RF Model (1-4): ")
            
            rf_models = {
                "1": "Indoor High Ceiling",
                "2": "Outdoor Open Space",
                "3": "Indoor Low Ceiling",
                "4": "Cubes And Walled Offices"
            }
            
            additional_attrs["rf_model"] = rf_models.get(rf_choice)
        
        # Create site data
        site_data = create_site_data(site_type, site_name, parent_name, **additional_attrs)
        
        print("\nCreating site with the following details:")
        print(f"Site Type: {site_type.capitalize()}")
        print(f"Site Name: {site_name}")
        print(f"Parent: {parent_name}")
        
        for key, value in additional_attrs.items():
            if value:
                print(f"{key.replace('_', ' ').capitalize()}: {value}")
                
        confirm = input("\nProceed with creation? (y/n): ")
        if confirm.lower() != 'y':
            print("Site creation cancelled")
            sys.exit(0)
            
        # Create the site
        response = dnac.post("site", ver="v1", data=site_data)
        
        # Check the response
        if hasattr(response, 'response') and hasattr(response.response, 'status_code'):
            if 200 <= response.response.status_code < 300:
                print("\nSite created successfully!")
                
                # Get the task ID from the response
                if hasattr(response, 'response') and hasattr(response.response, 'json'):
                    resp_data = response.response.json()
                    
                    if isinstance(resp_data, dict) and 'taskId' in resp_data:
                        task_id = resp_data['taskId']
                        print(f"Task ID: {task_id}")
                        
                        # Wait for task completion
                        print("\nWaiting for task to complete...")
                        try:
                            task_result = dnac.wait_on_task(task_id)
                            print(f"Task Status: {task_result.get('isError', False) and 'Error' or 'Success'}")
                            
                            if task_result.get('isError', False):
                                print(f"Error: {task_result.get('failureReason', 'Unknown error')}")
                            else:
                                print("Site was successfully created!")
                        except Exception as e:
                            print(f"Error waiting for task: {e}")
            else:
                print(f"\nError creating site: {response.response.status_code} - {response.response.text}")
        else:
            print("\nError: Unexpected response format")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 