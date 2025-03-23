#!/usr/bin/env python3
"""
Script to add a new site to Cisco Catalyst Centre using a curses-based UI.
Author: Steven Coutts
"""

import os
import sys
import argparse
import logging
import yaml
import json
import curses
from typing import Dict, Any, Optional, List

from dnac.core.api import Dnac
from dnac.ui.forms import show_form, show_dropdown_menu
from dnac.ui.colors import initialize_colors

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


def get_parent_sites(dnac):
    """Get available parent sites from DNAC."""
    try:
        parent_sites = []
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
            
            # Convert to simple name and ID for use in UI
            for site in available_sites:
                parent_sites.append({
                    "name": site["name"],
                    "id": site["id"]
                })
                
            return parent_sites
            
    except Exception as e:
        logging.error(f"Error fetching sites: {e}")
        return []


def create_site_data(site_type_idx, site_name, parent_site_idx, parent_sites, additional_attrs=None):
    """Create the site data payload."""
    # Convert from index to actual values
    site_types = ["area", "building", "floor"]
    site_type = site_types[site_type_idx]
    
    parent_name = parent_sites[parent_site_idx]["name"] if parent_site_idx < len(parent_sites) else "Global"
    
    # Initialize site data
    site_data = {
        "site": {
            site_type: {
                "name": site_name,
                "parentName": parent_name
            }
        }
    }
    
    # Add additional attributes if provided
    if additional_attrs:
        # Building attributes
        if site_type == "building":
            if "latitude" in additional_attrs and additional_attrs["latitude"]:
                try:
                    site_data["site"]["building"]["latitude"] = float(additional_attrs["latitude"])
                except (ValueError, TypeError):
                    pass
                    
            if "longitude" in additional_attrs and additional_attrs["longitude"]:
                try:
                    site_data["site"]["building"]["longitude"] = float(additional_attrs["longitude"])
                except (ValueError, TypeError):
                    pass
                    
            if "address" in additional_attrs and additional_attrs["address"]:
                site_data["site"]["building"]["address"] = additional_attrs["address"]
                
        # Floor attributes
        elif site_type == "floor":
            if "floor_number" in additional_attrs and additional_attrs["floor_number"]:
                try:
                    site_data["site"]["floor"]["floorNumber"] = int(additional_attrs["floor_number"])
                except (ValueError, TypeError):
                    pass
                    
            if "rf_model_idx" in additional_attrs and additional_attrs["rf_model_idx"] >= 0:
                rf_models = [
                    "Indoor High Ceiling",
                    "Outdoor Open Space",
                    "Indoor Low Ceiling",
                    "Cubes And Walled Offices"
                ]
                rf_model = rf_models[additional_attrs["rf_model_idx"]]
                site_data["site"]["floor"]["rfModel"] = rf_model
    
    return site_data


def add_site_ui(stdscr, args):
    """Main UI for adding a site."""
    # Initialize curses, but be cautious about the existing state
    try:
        curses.curs_set(0)  # Hide cursor
    except:
        pass  # Ignore if this fails
        
    stdscr.clear()
    stdscr.refresh()
    
    # Initialize colors if not already done
    try:
        initialize_colors()
    except:
        pass  # Ignore if this fails
        
    # Initialize window and screen dimensions
    h, w = stdscr.getmaxyx()
    
    # Title
    title = "Add Site to Catalyst Centre"
    stdscr.addstr(0, (w - len(title)) // 2, title, curses.A_BOLD)
    stdscr.refresh()
    
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
        stdscr.addstr(2, 2, "Error: Missing required configuration (hostname, username, or password)")
        stdscr.addstr(4, 2, "Press any key to exit")
        stdscr.refresh()
        stdscr.getch()
        return
    
    # Show connection message
    stdscr.addstr(2, 2, "Connecting to Catalyst Centre...")
    stdscr.refresh()
    
    try:
        # Initialize DNAC client
        dnac = Dnac(hostname)
        
        # Set SSL verification
        dnac.verify = verify

        # Login and get token
        dnac.login(username, password)
        
        # Get parent sites for dropdown
        stdscr.addstr(3, 2, "Fetching available sites...")
        stdscr.refresh()
        
        parent_sites = get_parent_sites(dnac)
        parent_site_names = [site["name"] for site in parent_sites]
        
        # Clear screen for main form
        stdscr.clear()
        stdscr.refresh()
        
        # Main site type selection
        site_type_options = ["Area", "Building", "Floor"]
        
        # Create form fields for initial screen
        basic_fields = [
            {
                "name": "site_type",
                "label": "Site Type",
                "type": "dropdown",
                "options": site_type_options,
                "default": 0,
                "required": True
            },
            {
                "name": "site_name", 
                "label": "Site Name",
                "type": "text",
                "default": "",
                "required": True
            },
            {
                "name": "parent_site",
                "label": "Parent Site",
                "type": "dropdown",
                "options": parent_site_names,
                "default": 0,
                "required": True
            }
        ]
        
        # Get basic site info
        basic_form_data = show_form(stdscr, "Add Site - Basic Information", basic_fields)
        
        if not basic_form_data:
            # User cancelled
            return
            
        # Get additional attributes based on site type
        additional_attrs = {}
        site_type_idx = basic_form_data["site_type"]
        
        if site_type_idx == 1:  # Building
            # Building form fields
            building_fields = [
                {
                    "name": "latitude",
                    "label": "Latitude",
                    "type": "number",
                    "default": "",
                    "required": False
                },
                {
                    "name": "longitude",
                    "label": "Longitude",
                    "type": "number", 
                    "default": "",
                    "required": False
                },
                {
                    "name": "address",
                    "label": "Address",
                    "type": "text",
                    "default": "",
                    "required": False
                }
            ]
            
            additional_attrs = show_form(stdscr, "Add Building - Additional Information", building_fields)
            if not additional_attrs:
                # User cancelled
                return
                
        elif site_type_idx == 2:  # Floor
            # Floor form fields
            floor_fields = [
                {
                    "name": "floor_number",
                    "label": "Floor Number",
                    "type": "number",
                    "default": "",
                    "required": False
                },
                {
                    "name": "rf_model_idx",
                    "label": "RF Model",
                    "type": "dropdown",
                    "options": [
                        "Indoor High Ceiling",
                        "Outdoor Open Space",
                        "Indoor Low Ceiling",
                        "Cubes And Walled Offices"
                    ],
                    "default": 0,
                    "required": False
                }
            ]
            
            additional_attrs = show_form(stdscr, "Add Floor - Additional Information", floor_fields)
            if not additional_attrs:
                # User cancelled
                return
        
        # Create site data from form inputs
        site_data = create_site_data(
            site_type_idx,
            basic_form_data["site_name"],
            basic_form_data["parent_site"],
            parent_sites,
            additional_attrs
        )
        
        # Show confirmation screen
        stdscr.clear()
        stdscr.addstr(0, (w - len("Confirm Site Creation")) // 2, "Confirm Site Creation", curses.A_BOLD)
        
        # Display summary
        site_type_name = site_type_options[site_type_idx]
        parent_name = parent_site_names[basic_form_data["parent_site"]]
        
        stdscr.addstr(2, 2, f"Site Type: {site_type_name}")
        stdscr.addstr(3, 2, f"Site Name: {basic_form_data['site_name']}")
        stdscr.addstr(4, 2, f"Parent Site: {parent_name}")
        
        row = 5
        if additional_attrs:
            for key, value in additional_attrs.items():
                if value != "" and key != "rf_model_idx":  # Skip displaying rf_model_idx directly
                    display_key = key.replace("_", " ").title()
                    stdscr.addstr(row, 2, f"{display_key}: {value}")
                    row += 1
                elif key == "rf_model_idx" and isinstance(value, int) and value >= 0:
                    rf_models = [
                        "Indoor High Ceiling",
                        "Outdoor Open Space",
                        "Indoor Low Ceiling",
                        "Cubes And Walled Offices"
                    ]
                    if value < len(rf_models):
                        stdscr.addstr(row, 2, f"RF Model: {rf_models[value]}")
                        row += 1
        
        # Prompt for confirmation
        stdscr.addstr(row + 1, 2, "Create this site? (y/n): ")
        stdscr.refresh()
        
        # Get confirmation
        curses.echo()
        curses.curs_set(1)
        confirm = stdscr.getstr(row + 1, 25, 1).decode('utf-8').lower()
        curses.noecho()
        curses.curs_set(0)
        
        if confirm != 'y':
            stdscr.addstr(row + 3, 2, "Site creation cancelled")
            stdscr.addstr(row + 5, 2, "Press any key to return")
            stdscr.refresh()
            stdscr.getch()
            return
        
        # Create the site
        stdscr.clear()
        stdscr.addstr(0, (w - len("Creating Site")) // 2, "Creating Site", curses.A_BOLD)
        stdscr.addstr(2, 2, "Sending request to Catalyst Centre...")
        stdscr.refresh()
        
        try:
            response = dnac.post("site", ver="v1", data=site_data)
            
            if hasattr(response, 'response') and hasattr(response.response, 'status_code'):
                if 200 <= response.response.status_code < 300:
                    # Get the task ID from the response
                    if hasattr(response, 'response') and hasattr(response.response, 'json'):
                        resp_data = response.response.json()
                        
                        if isinstance(resp_data, dict) and 'taskId' in resp_data:
                            task_id = resp_data['taskId']
                            
                            # Wait for task completion
                            stdscr.addstr(3, 2, f"Site creation initiated. Task ID: {task_id}")
                            stdscr.addstr(4, 2, "Waiting for task to complete...")
                            stdscr.refresh()
                            
                            try:
                                task_result = dnac.wait_on_task(task_id)
                                if task_result.get('isError', False):
                                    stdscr.addstr(5, 2, f"Error: {task_result.get('failureReason', 'Unknown error')}")
                                else:
                                    stdscr.addstr(5, 2, "Site was successfully created!")
                            except Exception as e:
                                stdscr.addstr(5, 2, f"Error waiting for task: {str(e)}")
                else:
                    stdscr.addstr(3, 2, f"Error creating site: {response.response.status_code}")
                    if hasattr(response.response, 'text'):
                        stdscr.addstr(4, 2, response.response.text[:80])  # Show first part of error
            else:
                stdscr.addstr(3, 2, "Error: Unexpected response format")
                
        except Exception as e:
            stdscr.addstr(3, 2, f"Error creating site: {str(e)}")
        
        stdscr.addstr(7, 2, "Press any key to return")
        stdscr.refresh()
        stdscr.getch()

    except Exception as e:
        stdscr.addstr(3, 2, f"Error: {str(e)}")
        stdscr.addstr(5, 2, "Press any key to exit")
        stdscr.refresh()
        stdscr.getch()


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="Add a new site to Cisco Catalyst Centre")
    parser.add_argument("-c", "--config", help=f"Config file (default: {DEFAULT_CONFIG_FILE})")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--from-menu", action="store_true", help="Indicates script is being run from the menu")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("urllib3.connectionpool").setLevel(logging.DEBUG)

    # Always use curses wrapper - the menu.py will handle proper curses cleanup/restore
    curses.wrapper(add_site_ui, args)


if __name__ == "__main__":
    main() 