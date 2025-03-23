#!/usr/bin/env python3
"""
Script to display site hierarchy from Cisco Catalyst Centre.
Author: Steven Coutts
"""

import os
import sys
import argparse
import logging
import yaml
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


def format_hierarchy(site_data, depth=0, is_last=False):
    """Format site hierarchy as a tree structure with improved visual appearance."""
    indent = "  " * depth
    
    # Determine connector symbol based on position in tree
    connector = "└─" if is_last else "├─"
    
    # Extract site type and name
    site_type = ""
    name = site_data.get("name", "Unknown")
    
    if "area" in site_data:
        site_type = "Area"
        name = site_data["area"]["name"]
        parent_name = site_data["area"].get("parentName", "")
        site_details = site_data["area"]
    elif "building" in site_data:
        site_type = "Building"
        name = site_data["building"]["name"]
        parent_name = site_data["building"].get("parentName", "")
        site_details = site_data["building"]
    elif "floor" in site_data:
        site_type = "Floor"
        name = site_data["floor"]["name"]
        parent_name = site_data["floor"].get("parentName", "")
        site_details = site_data["floor"]
    else:
        site_details = {}
        parent_name = ""
    
    # Format site information
    site_id = site_details.get("id", "")
    site_addr = site_details.get("address", "")
    
    # Create base output line with tree structure
    output = f"{indent}{connector} {name}"
    
    # Add type and additional details when available
    type_str = f" ({site_type})" if site_type else ""
    addr_str = f" - {site_addr}" if site_addr and site_type == "Building" else ""
    
    output += f"{type_str}{addr_str}\n"
    
    # Process children recursively with proper tree structure
    children = site_data.get("children", [])
    for i, child in enumerate(children):
        is_last_child = (i == len(children) - 1)
        child_indent = "  " * (depth + 1)
        # Add connecting lines for better visual structure
        output += format_hierarchy(child, depth + 1, is_last_child)
    
    return output


def get_hierarchy_with_details(dnac, args):
    """Fetch site hierarchy with additional details from DNAC."""
    try:
        # Get site topology
        print("Fetching site hierarchy...")
        sites_response = dnac.get("site", ver="v1")
        
        if hasattr(sites_response, 'response') and hasattr(sites_response.response, 'json'):
            sites_data = sites_response.response.json()
            
            # Handle the response format
            if isinstance(sites_data, dict) and 'response' in sites_data:
                sites_data = sites_data['response']
            
            # Sometimes the API returns a list instead of the expected hierarchy
            if isinstance(sites_data, list):
                output = "Global\n"
                
                # Process each top-level site
                for i, site in enumerate(sites_data):
                    is_last = (i == len(sites_data) - 1)
                    connector = "└─" if is_last else "├─"
                    
                    if 'name' in site:
                        site_id = site.get('id', 'unknown')
                        site_name = site.get('name', 'Unknown')
                        output += f"  {connector} {site_name}\n"
                        
                        # If this is a parent site, try to get its detailed hierarchy
                        try:
                            hierarchy_response = dnac.get(f"site/{site_id}/hierarchy", ver="v1")
                            if hasattr(hierarchy_response, 'response') and hasattr(hierarchy_response.response, 'json'):
                                hierarchy_data = hierarchy_response.response.json()
                                if isinstance(hierarchy_data, dict) and hierarchy_data.get('hierarchy'):
                                    output += format_hierarchy(hierarchy_data['hierarchy'], depth=2, is_last=is_last)
                        except Exception as e:
                            if args.verbose:
                                output += f"    ├─ Error fetching hierarchy: {e}\n"
                
                return output
            else:
                # Handle the case where the API returns the full hierarchy directly
                return format_hierarchy(sites_data)
    
    except Exception as e:
        return f"Error processing site data: {e}"


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="Display site hierarchy from Cisco Catalyst Centre")
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
        print("Successfully authenticated")
        
        # Get and display site hierarchy with the improved formatting
        print("\nSite Hierarchy:")
        print("=" * 80)
        
        # Use our new detailed hierarchy function
        hierarchy_output = get_hierarchy_with_details(dnac, args)
        print(hierarchy_output)
            
        print("=" * 80)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 
