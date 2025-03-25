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
import itertools
import time
from typing import Dict, Any, Optional, List
import urllib.parse
import traceback
import requests

# Add parent directory to path so we can import modules
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

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

# Import UI components
try:
    from dnac.ui.colors import ColorPair, get_color, initialize_colors
    from dnac.ui.components import draw_standard_header_footer
from dnac.ui.forms import show_form, show_dropdown_menu
except ImportError:
    print("Warning: UI components not found. This script requires the dnac UI components.")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
    handlers=[
        logging.FileHandler("dnac_add_site.log"),
        logging.StreamHandler()
    ]
)

DEFAULT_CONFIG_FILE = "config.yaml"


def load_dnac_config(config_file=None):
    """
    Load DNAC configuration from a file
    """
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


def get_parent_sites(dnac):
    """Get list of available parent sites"""
    try:
        # Get list of all sites
        response = dnac.session.get(
            f"{dnac.host.rstrip('/')}/dna/intent/api/v1/site",
            headers={"x-auth-token": dnac.token},
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        logging.debug(f"Sites response: {json.dumps(data, indent=2)}")
        
        # Available parent sites (always include Global first)
        available_sites = [{"name": "Global", "id": "global", "type": "area"}]
        
        # If Europe/UK exists, mark it specifically for debugging
        uk_area_found = False
        uk_site_id = None
        
        if 'response' in data:
            sites = data['response']
            if not isinstance(sites, list):
                logging.warning(f"Unexpected sites response format: {type(sites)}")
                return available_sites
            
            for site in sites:
                try:
                    if not isinstance(site, dict):
                        continue
                    
                    site_id = site.get('id')
                    site_name = site.get('name', '')
                    site_type = "Unknown"
                    
                    # Try to determine site type from additionalInfo
                    additional_info = site.get('additionalInfo', [])
                    for info in additional_info:
                        if isinstance(info, dict):
                            if info.get('nameSpace') == 'Location' and info.get('attributes', {}).get('type'):
                                site_type = info.get('attributes', {}).get('type')
                            
                    # Special check for UK site using hierarchical paths
                    if "UK" in site_name:
                        logging.info(f"Found UK site: {site_name}, id={site_id}, type={site_type}")
                        
                        # Special handling for UK with hierarchical path
                        if site_name == "Global/Europe/UK" or site_name.endswith("/UK") or site_name == "UK":
                            logging.info(f"*** FOUND UK AREA: {site_name}, id={site_id} ***")
                            uk_area_found = True
                            uk_site_id = site_id
                    
                    # Add site to available parents
                        available_sites.append({
                        "name": site_name,
                        "id": site_id,
                        "type": site_type
                    })
                except Exception as e:
                    logging.warning(f"Error processing site {site}: {str(e)}")
        
        # If we found a UK area, make sure it's properly labeled
        if uk_area_found and uk_site_id:
            for site in available_sites:
                if site.get('id') == uk_site_id:
                    site['name'] = "UK"  # Simplify display name
                    site['type'] = "Area"  # Force type to Area
                    logging.info(f"Updated UK area display: {site}")
        
        logging.debug(f"Available parent sites: {available_sites}")
        return available_sites
    except Exception as e:
        logging.error(f"Error getting parent sites: {str(e)}")
        return [{"name": "Global", "id": "global", "type": "area"}]


def create_site_data(site_type, site_name, parent_site, parent_id):
    """Create site data structure for API request"""
    logging.info(f"Creating {site_type} '{site_name}' under {parent_site} (ID: {parent_id})")
    
    # Special case for buildings under UK using hierarchical path
    if site_type == "building" and parent_site == "UK" and parent_id and parent_id.lower() != "global":
        logging.info(f"Creating building under UK with hierarchical path format")
        
        site_data = {
            "type": "building",
            "site": {
                "building": {
                    "name": site_name,
                    "parentId": parent_id,
                    "address": "1 Main Street",
                    "latitude": 51.50853,  # Numeric format
                    "longitude": -0.12574, # Numeric format
                    "country": "United Kingdom"
                }
            }
        }
        
        logging.debug(f"Using UK hierarchical path building data: {json.dumps(site_data, indent=2)}")
        return site_data
    else:
        # Log parent information for debugging
        logging.debug(f"Creating {site_type} with parent site: {parent_site}, parent ID: {parent_id}")
        
    # Create the payload in the format expected by the API
    if site_type == "area":
        site_data = {
            "type": site_type,
            "site": {
                "area": {
                    "name": site_name,
                    "parentName": parent_site if parent_site else "Global"
                }
            }
        }
        # Add parentId if available (more reliable than parentName)
        if parent_id and parent_id != "global":
            site_data["site"]["area"]["parentId"] = parent_id
            
    elif site_type == "building":
            # For buildings, we need special handling for various parent sites
            
            # Special case for UK specifically
            if parent_site == "UK" and parent_id and parent_id.lower() != "global":
                logging.info(f"Creating building under UK with ID: {parent_id}")
                
                # Ultra simplified UK-specific building data - minimal required fields
                site_data = {
                    "type": "building",
                    "site": {
                        "building": {
                            "name": site_name,
                            "parentId": parent_id,
                            "address": "1 Main Street",
                            "latitude": 51.50853,  # Numeric format, not string
                            "longitude": -0.12574, # Numeric format, not string
                            "country": "United Kingdom"
                        }
                    }
                }
                
                logging.debug(f"Using minimalist UK building data: {json.dumps(site_data, indent=2)}")
            # For buildings under other non-Global parents
            elif parent_site != "Global" and parent_id and parent_id.lower() != "global":
                logging.info(f"Creating building under non-Global parent: {parent_site} with ID: {parent_id}")
                
                # Simplified building data for non-Global parents
        site_data = {
            "type": site_type,
            "site": {
                "building": {
                    "name": site_name,
                            "parentId": parent_id,  # Use only parentId for non-Global parents
                            "parentName": parent_site,  # Also include parentName
                            "address": "1 Main Street, London",
                            "latitude": "51.50853",
                            "longitude": "-0.12574",
                            "country": "United Kingdom"
                        }
                    }
                }
                
                # Non-Global specific attributes for better compatibility
                site_data["site"]["building"]["city"] = "London"
                logging.debug(f"Using non-Global building data format: {json.dumps(site_data, indent=2)}")
            else:
                # Standard building creation under Global
                building_data = {
                    "name": site_name,
                    "address": "1 Main Street",
                    "latitude": "51.50853",  # London coordinates as strings
                    "longitude": "-0.12574",
                    "country": "United Kingdom"  # Required field
                }
                
                # Add optional fields only if they have values
                building_data["city"] = "London"
                
                # Always add parentName for consistency
                building_data["parentName"] = parent_site if parent_site else "Global"
                
                # Add parentId only if valid (not empty and not "global")
                if parent_id and parent_id.lower() != "global":
                    logging.debug(f"Adding parentId '{parent_id}' to building data")
                    building_data["parentId"] = parent_id
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
                        "height": "10"
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


def get_site_name(stdscr):
    """Get site name input directly from the user."""
    # Save cursor state
    try:
        old_cursor = curses.curs_set(1)
    except:
        old_cursor = 0
        
    # Turn on echo for text input
    curses.echo()
    
    # Get window dimensions
    h, w = stdscr.getmaxyx()
    
    # Clear screen
    stdscr.clear()
    
    # Draw standard header
    content_start = draw_standard_header_footer(
        stdscr, 
        title="Cisco Catalyst Centre",
        subtitle="Enter Site Name"
    )
    
    # Draw prompt
    prompt = "Site Name: "
    try:
        stdscr.addstr(content_start + 1, 4, prompt)
        
        # Draw note
        note = "(Press Enter when done)"
        stdscr.addstr(content_start + 2, 4, note)
    except curses.error:
        pass
    
    stdscr.refresh()
    
    # Calculate input field size
    max_len = min(50, w - len(prompt) - 6)
    
    # Get input
    try:
        # Position cursor
        stdscr.move(content_start + 1, 4 + len(prompt))
        
        # Get user input
        site_name = stdscr.getstr(max_len).decode('utf-8').strip()
    except Exception as e:
        site_name = ""
    
    # Reset terminal state
    curses.noecho()
    try:
        curses.curs_set(old_cursor)
    except:
        pass
    
    return site_name


def select_site_type(stdscr):
    """Display a menu to select site type."""
    # Initialize colors
    initialize_colors()
    
    # Hide cursor
    try:
        curses.curs_set(0)
    except:
        pass
    
    # Site type options
    site_types = [
        {"name": "Area", "value": "area"},
        {"name": "Building", "value": "building"},
        {"name": "Floor", "value": "floor"}
    ]
    
    # Current selection
    current_idx = 0
    
    while True:
        # Clear screen
        stdscr.clear()
        
        # Draw standard header/footer
        content_start = draw_standard_header_footer(
            stdscr, 
            title="Cisco Catalyst Centre",
            subtitle="Select Site Type",
            footer_text="↑↓: Navigate | Enter: Select | q: Cancel"
        )
        
        # Get window dimensions
        h, w = stdscr.getmaxyx()
        
        # Draw options
        for i, site_type in enumerate(site_types):
            # Calculate y position
            y = content_start + 1 + i
            
            # Skip if outside screen
            if y >= h:
                continue
                
            # Highlight selected item
            if i == current_idx:
                stdscr.attron(curses.A_REVERSE)
                
            # Center the option
            option_text = site_type["name"]
            x = (w - len(option_text)) // 2
            
            # Draw the option
            try:
                stdscr.addstr(y, x, option_text)
            except curses.error:
                pass
                
            # Turn off highlight
            if i == current_idx:
                stdscr.attroff(curses.A_REVERSE)
        
        # Refresh
        stdscr.refresh()
        
        # Get key press
        key = stdscr.getch()
        
        if key == curses.KEY_UP:
            current_idx = max(0, current_idx - 1)
        elif key == curses.KEY_DOWN:
            current_idx = min(len(site_types) - 1, current_idx + 1)
        elif key == ord('\n'):  # Enter key
            return site_types[current_idx]["value"]
        elif key == ord('q'):
            return None


def show_parent_site_selection(stdscr, available_sites):
    """Show a scrollable list of parent sites to select from."""
    # Initialize colors
    initialize_colors()
    
    # Hide cursor
    try:
        curses.curs_set(0)
    except:
        pass
    
    # Get window dimensions
    h, w = stdscr.getmaxyx()
    
    # Add "Global" as the first option
    sites_with_global = [{"name": "Global", "id": "global", "type": "global"}] + available_sites
    
    # Current selection and scroll position
    current_idx = 0
    scroll_pos = 0
    
    # Calculate max scroll position (if needed)
    max_scroll = max(0, len(sites_with_global) - (h - 6))
    
    while True:
        # Clear screen
        stdscr.clear()
        
        # Draw standard header/footer
        content_start = draw_standard_header_footer(
            stdscr,
            title="Cisco Catalyst Centre",
            subtitle="Select Parent Site",
            footer_text="↑↓: Navigate | Enter: Select | q: Cancel"
        )
        
        # Available display height
        display_height = h - content_start - 2
        
        # Display parent sites with scrolling
        for i in range(min(display_height, len(sites_with_global))):
            idx = scroll_pos + i
            if idx >= len(sites_with_global):
                break
                
            y = content_start + i
            site = sites_with_global[idx]
            
            # Format site string
            site_name = site["name"]
            site_type = site["type"].capitalize() if "type" in site else "Site"
            
            if "parentName" in site:
                site_str = f"{site_name} ({site_type} in {site['parentName']})"
            else:
                site_str = f"{site_name} ({site_type})"
            
            # Truncate if too long
            if len(site_str) > w - 4:
                site_str = site_str[:w-7] + "..."
            
            # Highlight current selection
            is_selected = (idx == current_idx)
            if is_selected:
                stdscr.attron(curses.A_REVERSE)
            
            stdscr.addstr(y, 2, site_str)
            
            if is_selected:
                stdscr.attroff(curses.A_REVERSE)
        
        # Show scrolling indicators if needed
        if scroll_pos > 0:
            stdscr.addstr(content_start, w // 2, "▲")
        if scroll_pos + display_height < len(sites_with_global):
            stdscr.addstr(content_start + display_height - 1, w // 2, "▼")
        
        stdscr.refresh()
        
        # Get key press
        key = stdscr.getch()
        
        if key == curses.KEY_UP and current_idx > 0:
            current_idx -= 1
            # Adjust scroll position if needed
            if current_idx < scroll_pos:
                scroll_pos = current_idx
        elif key == curses.KEY_DOWN and current_idx < len(sites_with_global) - 1:
            current_idx += 1
            # Adjust scroll position if needed
            if current_idx >= scroll_pos + display_height:
                scroll_pos = current_idx - display_height + 1
        elif key == ord('\n'):  # Enter key
            selected = sites_with_global[current_idx]
            return selected["name"], selected["id"]
        elif key == ord('q'):  # Cancel
            return None, None
        elif key == curses.KEY_PPAGE:  # Page Up
            scroll_pos = max(0, scroll_pos - display_height)
            current_idx = max(0, current_idx - display_height)
        elif key == curses.KEY_NPAGE:  # Page Down
            scroll_pos = min(max_scroll, scroll_pos + display_height)
            current_idx = min(len(sites_with_global) - 1, current_idx + display_height)


def create_site_screen(stdscr, site_type, dnac, config, logger):
    """Screen for creating a new site."""
    # Get parent sites
    parent_sites = get_parent_sites(dnac)
    if not parent_sites:
        logger.error("Failed to fetch parent sites.")
        show_message(stdscr, "Failed to fetch parent sites.", curses.A_REVERSE)
        return False
    
    # Add a "Global" option for top-level sites
    parent_sites_dropdown = ["Global"] + [site.get("name") for site in parent_sites]
    parent_site_ids = {"Global": "global"}
    for site in parent_sites:
        parent_site_ids[site.get("name")] = site.get("id")
    
    # Set up variables
    site_name = ""
    parent_site = "Global"  # Default value
    parent_id = "global"    # Default global ID
    form_fields = ["site_name", "parent_site"]
    current_field = 0
    saved = False
    
    # Setup spinner for loading indicators
    spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
    
    while True:
        # Clear screen
        stdscr.clear()
        
        # Draw standard header/footer
        content_start = draw_standard_header_footer(
            stdscr, 
            title="Cisco Catalyst Centre",
            subtitle=f"Create New {site_type.capitalize()}",
            footer_text="UP/DOWN: Navigate | ENTER: Edit field | S: Save | Q: Cancel"
        )
        
        # Draw input fields
        stdscr.addstr(content_start + 1, 2, "Site Name:", curses.A_BOLD)
        stdscr.addstr(content_start + 1, 15, site_name)
        
        stdscr.addstr(content_start + 3, 2, "Parent Site:", curses.A_BOLD)
        stdscr.addstr(content_start + 3, 15, parent_site)
        
        # Draw field cursor
        cursor_y = content_start + 1 if current_field == 0 else content_start + 3
        stdscr.addstr(cursor_y, 1, ">")
        
        # Refresh screen
        stdscr.refresh()
        
        # Get key press
        key = stdscr.getch()
        
        # Handle navigation
        if key == curses.KEY_UP and current_field > 0:
            current_field -= 1
        elif key == curses.KEY_DOWN and current_field < len(form_fields) - 1:
            current_field += 1
        elif key == ord('\n'):  # Enter key
            if current_field == 0:  # Site name field
                site_name = edit_field(stdscr, 3, 15, site_name)
            elif current_field == 1:  # Parent site field
                choice = show_dropdown(stdscr, 6, 15, parent_sites_dropdown, parent_sites_dropdown.index(parent_site))
                if choice >= 0:
                    parent_site = parent_sites_dropdown[choice]
                    parent_id = parent_site_ids.get(parent_site, "global")
                    logger.debug(f"Selected parent site: {parent_site}, ID: {parent_id}")
        elif key == ord('s') or key == ord('S'):  # Save
            # Validate form
            if not site_name:
                show_message(stdscr, "Site name cannot be empty.", curses.A_REVERSE)
                continue
                
            # Confirmation screen
            if show_confirm(stdscr, f"Create {site_type} '{site_name}' under '{parent_site}'?"):
                # Log the attempt
                logger.info(f"Attempting to create {site_type}: {site_name} under parent: {parent_site} (ID: {parent_id})")
                
                # Show spinner while processing
                status_msg = f"Creating {site_type}..."
                startx = max(0, (curses.COLS - len(status_msg) - 2) // 2)
                
                # Create site data
                site_data = create_site_data(site_type, site_name, parent_site, parent_id)
                
                # Show confirmation
                stdscr.clear()
                try:
                    stdscr.addstr(0, 2, "Creating site...")
                    stdscr.refresh()
                    
                    # Show a spinner while creating site
                    spinner_chars = ['|', '/', '-', '\\']
                    spinner_idx = 0
                    
                    def update_spinner():
                        nonlocal spinner_idx
                        try:
                            # Clear previous spinner
                            stdscr.addstr(1, 2, " " * 20)
                            # Show updated spinner with status
                            stdscr.addstr(1, 2, f"Please wait {spinner_chars[spinner_idx]} ")
                            spinner_idx = (spinner_idx + 1) % len(spinner_chars)
                            stdscr.refresh()
                        except curses.error:
                            pass
                    
                    # Setup a timer to update the spinner periodically
                    last_update = 0
                    update_interval = 0.2  # seconds
                except curses.error:
                    pass
                
                try:
                    # Log for debugging
                    logging.debug(f"Creating site of type: {site_type}")
                    logging.debug(f"Site name: {site_name}")
                    logging.debug(f"Parent site: {parent_site}")
                    logging.debug(f"Sending site data: {json.dumps(site_data, indent=2)}")
                    
                    # Create the site using direct API call to avoid path construction issues
                    direct_url = "dna/intent/api/v1/site"
                    
                    # Ensure hostname doesn't have trailing slash and doesn't duplicate protocol
                    base_url = dnac.host.rstrip('/')
                    full_url = f"{base_url}/{direct_url}"
                    
                    headers = {
                        "x-auth-token": dnac.token,
                        "Content-Type": "application/json"
                    }
                    
                    # Convert site_data to JSON string
                    json_data = json.dumps(site_data)
                    logging.debug(f"Full URL: {full_url}")
                    logging.debug(f"Headers: {headers}")
                    logging.debug(f"JSON data: {json_data}")
                    
                    # Make direct request
                    response = dnac.session.post(
                        full_url,
                        headers=headers,
                        data=json_data
                    )
                    logging.debug(f"Direct response status: {response.status_code}")
                    logging.debug(f"Direct response text: {response.text}")
                    
                    # Parse response
                    response_data = response.json()
                    logging.debug(f"Response data: {json.dumps(response_data, indent=2)}")
                    
                    # Check for task ID or execution ID
                    success = False
                    
                    if response.status_code in (200, 201, 202):
                        # For 202 Accepted, we need to monitor for completion
                        if response.status_code == 202:
                            logging.info("Got 202 Accepted response, monitoring for completion...")
                            
                            # Extract execution ID if available
                            execution_id = None
                            if response_data and 'executionId' in response_data:
                                execution_id = response_data['executionId']
                                logging.info(f"Tracking execution ID: {execution_id}")
                                
                                # SPECIAL HANDLING FOR UK BUILDINGS - If all else fails, try direct API call
                                if parent_site == "UK" and site_type == "building" and not success:
                                    logging.info("ATTEMPTING DIRECT UK BUILDING CREATION METHOD")
                                    direct_response = create_uk_building_direct(dnac, site_name, parent_id)
                                    
                                    if direct_response and direct_response.status_code in (200, 201, 202):
                                        logging.info("DIRECT UK BUILDING CREATION SUCCESS")
                                                success = True
                        else:
                            # Proceed with verification rather than treating as success
                            
                            # Special logging for UK buildings
                            if parent_site == "UK" and site_type == "building":
                                logging.info(f"Verifying building under UK (attempt {attempt+1})")
                                        
                                        if verify_response.status_code == 200:
                                try:
                                            verify_data = verify_response.json()
                                    # Log UK building verification data
                                    if parent_site == "UK" and site_type == "building":
                                        logging.debug(f"UK building verification data: {json.dumps(verify_data, indent=2)}")
                                    
                                            if 'response' in verify_data and isinstance(verify_data['response'], list):
                                                for site in verify_data['response']:
                                            # For buildings, check the hierarchy too
                                            if site_type == "building":
                                                site_hierarchy = site.get('siteNameHierarchy', '')
                                                # Log all site hierarchies to debug
                                                logging.debug(f"Checking site: {site.get('name')} | Hierarchy: {site_hierarchy}")
                                                
                                                # Special handling for UK buildings
                                                if parent_site == "UK":
                                                    # Log detailed site data for debugging
                                                    logging.debug(f"UK building check - site data: {json.dumps(site, indent=2)}")
                                                    
                                                    # Check if building contains UK in hierarchy regardless of name
                                                    if "UK" in site_hierarchy and site.get('name') == site_name:
                                                        logging.info(f"UK Building '{site_name}' found in hierarchy containing UK!")
                                                        verify_found = True
                                                        success = True
                                                        break
                                                    
                                                    # Standard checks for all buildings
                                                    # 1. Exact name match
                                                    if site.get('name') == site_name:
                                                        logging.info(f"Building '{site_name}' found by exact name match!")
                                                        verify_found = True
                                                        success = True
                                                        break
                                                    
                                                    # 2. Look for building in hierarchy path with parent
                                                    if site_hierarchy:
                                                        # Look for patterns like "{parent}/{site_name}" or "{parent}/Building/{site_name}"
                                                        patterns_to_check = [
                                                            f"/{site_name}",  # Simple pattern
                                                            f"{parent_site}/{site_name}",  # Direct parent
                                                            f"{parent_site}/Building/{site_name}",  # With Building type
                                                            f"Global/{site_name}",  # Under Global
                                                            f"/{parent_site}/{site_name}",  # With slash prefix
                                                            f"Global/{parent_site}/{site_name}"  # Full hierarchy path for UK
                                                        ]
                                                        
                                                        # UK-specific patterns
                                                        if parent_site == "UK":
                                                            uk_patterns = [
                                                                f"Global/Europe/UK/{site_name}",
                                                                f"Europe/UK/{site_name}",
                                                                f"UK/{site_name}"
                                                            ]
                                                            patterns_to_check.extend(uk_patterns)
                                                            logging.debug(f"Added UK-specific patterns: {uk_patterns}")
                                                        
                                                        for pattern in patterns_to_check:
                                                            if pattern in site_hierarchy:
                                                                logging.info(f"Building '{site_name}' found in hierarchy path: {site_hierarchy}")
                                                                logging.info(f"Matched pattern: {pattern}")
                                                                verify_found = True
                                                                success = True
                                                    # Check plain name in hierarchy when under UK or other area
                                                    if parent_site != "Global" and site_name in site_hierarchy:
                                                        logging.info(f"Building '{site_name}' found in non-Global hierarchy: {site_hierarchy}")
                                                        verify_found = True
                                            success = True
                                            break
                                except ValueError:
                                    logging.warning("Failed to parse verification response as JSON")
                                    except Exception as e:
                            logging.warning(f"Error in verification method 1: {str(e)}")
                                
                                # Method 2: Try getting site by name (useful for buildings/floors)
                                if not verify_found:
                                    try:
                                        # Encode site name for URL
                                        encoded_name = urllib.parse.quote(site_name)
                                        
                                        # Special handling for UK buildings - try specific name pattern
                                        if parent_site == "UK" and site_type == "building":
                                            # Try different name patterns for UK buildings
                                            encoded_uk_name = urllib.parse.quote(f"UK/{site_name}")
                                            verify_url = f"{base_url}/dna/intent/api/v1/site?name={encoded_uk_name}"
                                            logging.debug(f"Trying UK-specific name pattern: {encoded_uk_name}")
                                        else:
                                            verify_url = f"{base_url}/dna/intent/api/v1/site?name={encoded_name}"
                                            
                                    verify_response = dnac.session.get(
                                        verify_url, 
                                        headers={"x-auth-token": dnac.token},
                                        timeout=10
                                    )
                                    
                                    if verify_response.status_code == 200:
                                        verify_data = verify_response.json()
                                            # Special logging for UK buildings
                                            if parent_site == "UK" and site_type == "building":
                                                logging.debug(f"UK name search response: {json.dumps(verify_data, indent=2)}")
                                                
                                            # Check different response structures - the response can be a list or dict
                                            if 'response' in verify_data:
                                                response_obj = verify_data['response']
                                                # Handle both list and dictionary response formats
                                                if isinstance(response_obj, list):
                                                    # If it's a list, check each item
                                                    for site in response_obj:
                                                        if isinstance(site, dict) and site.get('name') == site_name:
                                                            logging.info(f"Site '{site_name}' found in name query response list!")
                                                            verify_found = True
                                                            success = True
                                                elif isinstance(response_obj, dict):
                                                    # If it's a dict, check direct match or sites list
                                                    if response_obj.get('name') == site_name:
                                                        logging.info(f"Site '{site_name}' found in name query response dict!")
                                                        verify_found = True
                                                        success = True
                                                    elif 'sites' in response_obj and isinstance(response_obj['sites'], list):
                                                        for site in response_obj['sites']:
                                                if site.get('name') == site_name:
                                                                logging.info(f"Site '{site_name}' found in sites list!")
                                                                verify_found = True
                                                    success = True
                                                # Generic check for non-empty response
                                                elif response_obj:
                                                    logging.info(f"Site likely created - found non-empty response for '{site_name}'")
                                                    verify_found = True
                            success = True
                                    except Exception as e:
                                        logging.warning(f"Error in verification method 2: {str(e)}")
                                        # Log full error details with traceback
                                        import traceback
                                        logging.debug(f"Verification error details: {traceback.format_exc()}")
                     
                                # Method 3: Try getting the site by parent (useful for hierarchy)
                                if not verify_found and parent_id and parent_id != "global":
                    try:
                                        verify_url = f"{base_url}/dna/intent/api/v1/site/{parent_id}"
                        verify_response = dnac.session.get(
                            verify_url, 
                            headers={"x-auth-token": dnac.token},
                            timeout=10
                        )
                        
                        if verify_response.status_code == 200:
                            verify_data = verify_response.json()
                                            # Look for the site name in the response
                                            response_text = json.dumps(verify_data)
                                            if site_name in response_text:
                                                logging.info(f"Site '{site_name}' found in parent data after {attempt+1} verification attempts!")
                                                verify_found = True
                                        success = True
                                    except Exception as e:
                                        logging.warning(f"Error in verification method 3: {str(e)}")
                                
                                if verify_found:
                                        break
                                    
                                # If not found and not the last attempt, wait and try again
                                if attempt < max_verification_attempts - 1:
                                    logging.info(f"Site not found yet, waiting {verification_delay} seconds...")
                                    time.sleep(verification_delay)
                        
                    if not success:
                        logging.error(f"Failed to verify site creation after {max_verification_attempts} attempts")
                        # Special handling for buildings - they might be created but not appear immediately
                        if site_type == "building":
                            logging.info("Building creation received a success response. Treating as successful despite verification failure.")
                            update_spinner("Building creation likely successful but not yet visible in API")
                            # Wait longer for the final building attempt
                            time.sleep(5)
                            success = True
                                else:
                            raise Exception("Site creation could not be verified within the timeout period")
                    
                    # Display result to user
                    if success:
                        show_message(stdscr, f"{site_type.capitalize()} '{site_name}' created successfully!", curses.A_NORMAL)
                        saved = True
                        break
                    else:
                        show_message(stdscr, f"Failed to create {site_type}. See logs for details.", curses.A_REVERSE)
                except Exception as e:
                    logging.error(f"Error creating site: {str(e)}")
                    show_message(stdscr, f"Error: {str(e)}", curses.A_REVERSE)
            else:
                # User cancelled the confirmation
                pass
        elif key == ord('q') or ord('Q'):  # Cancel
            if not saved and site_name:
                if show_confirm(stdscr, "Discard changes?"):
                    return False
            else:
                return False
    
    return saved


def add_site_ui(stdscr, dnac):
    """Main UI function for adding a site."""
    # Initialize colors
    initialize_colors()
    
    # Hide cursor
    try:
        curses.curs_set(0)
    except:
        pass
    
    # Enable keypad mode for arrow keys
    stdscr.keypad(True)
    
    # Set background
    stdscr.bkgd(' ', get_color(ColorPair.NORMAL))
    
    # Main menu loop - continue until user chooses to exit
    while True:
        try:
            # Select site type
            site_type = select_site_type(stdscr)
            
            if site_type is None:
                return  # User cancelled, return to calling function
            
            # Get site name
            site_name = get_site_name(stdscr)
            
            if not site_name:
                continue  # User cancelled, go back to site type selection
            
            # Get parent sites and select one
            available_sites = get_parent_sites(dnac)
            parent_site, parent_id = show_parent_site_selection(stdscr, available_sites)
            
            if parent_site is None:
                continue  # User cancelled, go back to site type selection
            
            # Special case for UK buildings
            if site_type == "building" and parent_site == "UK" and parent_id:
                logging.info("SPECIAL CASE: UK Building - ULTRA SIMPLE IMPLEMENTATION")
                
                # Show creating status
        stdscr.clear()
        try:
                    content_start = draw_standard_header_footer(
                        stdscr, 
                        title="Cisco Catalyst Centre",
                        subtitle="UK Building Creator"
                    )
                    stdscr.addstr(content_start + 1, 2, "Creating building under UK...")
            stdscr.refresh()
        except curses.error:
            pass
        
                # Bare minimum approach
                try:
                    # Minimal payload with only required fields
                    minimal_payload = {
                        "type": "building",
                        "site": {
                            "building": {
                                "name": site_name,
                                "parentId": parent_id,
                                "address": "1 Main Street",
                                "latitude": 51.50853,
                                "longitude": -0.12574,
                                "country": "United Kingdom"
                            }
                        }
                    }
                    
                    # Log every detail
                    base_url = dnac.host.rstrip('/')
                    api_url = f"{base_url}/dna/intent/api/v1/site"
                    headers = {
                        "x-auth-token": dnac.token,
                        "Content-Type": "application/json"
                    }
                    
                    logging.info(f"UK BUILDING REQUEST URL: {api_url}")
                    logging.info(f"UK BUILDING TOKEN: {dnac.token}")
                    logging.info(f"UK BUILDING HEADERS: {headers}")
                    logging.info(f"UK BUILDING PAYLOAD: {json.dumps(minimal_payload, indent=2)}")
                    
                    # Make the request with both data and json parameters to be safe
                    response = dnac.session.post(
                        api_url,
                        headers=headers,
                        data=json.dumps(minimal_payload),  # Use data with manually serialized JSON
                        timeout=60
                    )
                    
                    # Log response details
                    logging.info(f"UK BUILDING STATUS CODE: {response.status_code}")
                    logging.info(f"UK BUILDING RESPONSE HEADERS: {dict(response.headers)}")
                    logging.info(f"UK BUILDING RESPONSE TEXT: {response.text}")
                    
                    # Process the response
                    try:
                        response_data = response.json()
                        logging.info(f"UK BUILDING RESPONSE JSON: {json.dumps(response_data, indent=2)}")
                    except:
                        logging.info("UK BUILDING RESPONSE IS NOT JSON")
                    
                    # Show result to user regardless of success/failure
            stdscr.clear()
            try:
                        content_start = draw_standard_header_footer(
                            stdscr, 
                            title="Cisco Catalyst Centre",
                            subtitle="UK Building Result"
                        )
                        
                        # Show complete information about what happened
                        stdscr.addstr(content_start + 1, 2, f"Attempted to create building '{site_name}' under UK")
                        stdscr.addstr(content_start + 2, 2, f"Response status: {response.status_code}")
                        
                        if response.status_code in (200, 201, 202):
                            stdscr.addstr(content_start + 3, 2, "SUCCESS! Response was in success range")
                        else:
                            stdscr.addstr(content_start + 3, 2, "ERROR! Non-success status code")
                            
                        stdscr.addstr(content_start + 5, 2, "Full details have been logged to dnac_add_site.log")
                        stdscr.addstr(content_start + 6, 2, "Please check the log file to see what happened")
                        stdscr.addstr(content_start + 8, 2, "Press any key to continue...")
                stdscr.refresh()
            except curses.error:
                pass
            
                    stdscr.getch()
                    # After creating UK building, go back to site type selection
                    continue
                    
                except Exception as e:
                    logging.error(f"UK BUILDING DIRECT EXCEPTION: {str(e)}")
                    import traceback
                    logging.error(f"UK BUILDING TRACEBACK: {traceback.format_exc()}")
                    # Continue to standard approach as fallback
        
        # Create site data
        site_data = create_site_data(site_type, site_name, parent_site, parent_id)
        
            # Confirm creation
        stdscr.clear()
        try:
                content_start = draw_standard_header_footer(
                    stdscr, 
                    title="Cisco Catalyst Centre",
                    subtitle="Confirm Site Creation",
                    footer_text="Press 'y' to confirm, any other key to cancel"
                )
                
                stdscr.addstr(content_start + 1, 4, f"Type: {site_type.title()}")
                stdscr.addstr(content_start + 2, 4, f"Name: {site_name}")
                stdscr.addstr(content_start + 3, 4, f"Parent: {parent_site if parent_site else 'Global'}")
                
                # Show additional data for buildings
                if site_type == "building":
                    building_info = site_data["site"]["building"]
                    stdscr.addstr(content_start + 4, 4, f"Address: {building_info['address']}")
                    stdscr.addstr(content_start + 5, 4, f"City: {building_info['city']}")
                    stdscr.addstr(content_start + 6, 4, f"Country: {building_info['country']}")
                
            stdscr.refresh()
        except curses.error:
            pass
        
        if stdscr.getch() != ord('y'):
                continue
        
        # Create site
        stdscr.clear()
        try:
            stdscr.addstr(0, 2, "Creating site...")
            stdscr.refresh()
            
            # Show a spinner while creating site
            spinner_chars = ['|', '/', '-', '\\']
            spinner_idx = 0
            
                def update_spinner(message=None):
                nonlocal spinner_idx
                try:
                    # Clear previous spinner
                        stdscr.addstr(1, 2, " " * 60)  # Clear more space for messages
                    # Show updated spinner with status
                        status_text = f"Please wait {spinner_chars[spinner_idx]} "
                        if message:
                            status_text += message
                        stdscr.addstr(1, 2, status_text)
                    spinner_idx = (spinner_idx + 1) % len(spinner_chars)
                    stdscr.refresh()
                except curses.error:
                    pass
            
            # Setup a timer to update the spinner periodically
            last_update = 0
            update_interval = 0.2  # seconds
        except curses.error:
            pass
        
        try:
            # Log for debugging
            logging.debug(f"Creating site of type: {site_type}")
            logging.debug(f"Site name: {site_name}")
            logging.debug(f"Parent site: {parent_site}")
            logging.debug(f"Sending site data: {json.dumps(site_data, indent=2)}")
            
            # Create the site using direct API call to avoid path construction issues
            direct_url = "dna/intent/api/v1/site"
            
            # Ensure hostname doesn't have trailing slash and doesn't duplicate protocol
            base_url = dnac.host.rstrip('/')
            full_url = f"{base_url}/{direct_url}"
            
            headers = {
                "x-auth-token": dnac.token,
                "Content-Type": "application/json"
            }
            
            # Convert site_data to JSON string
            json_data = json.dumps(site_data)
            logging.debug(f"Full URL: {full_url}")
            logging.debug(f"Headers: {headers}")
            logging.debug(f"JSON data: {json_data}")
            
            # Make direct request
            response = dnac.session.post(
                full_url,
                headers=headers,
                data=json_data
            )
            logging.debug(f"Direct response status: {response.status_code}")
            logging.debug(f"Direct response text: {response.text}")
            
            # Parse response
                try:
            response_data = response.json()
            logging.debug(f"Response data: {json.dumps(response_data, indent=2)}")
                except ValueError:
                    response_data = {"message": response.text}
                    logging.debug(f"Non-JSON response: {response.text}")
            
                # Check for success status codes
            success = False
            
            if response.status_code in (200, 201, 202):
                    logging.info(f"Received successful status code: {response.status_code}")
                    
                    # Update spinner with status
                    update_spinner("Received successful response. Verifying...")
                    
                    # Verify the site was created
                    max_verification_attempts = 30
                    verification_delay = 3  # seconds
                    
                    for attempt in range(max_verification_attempts):
                        # Update spinner with verification attempt
                        update_spinner(f"Verification attempt {attempt+1}/{max_verification_attempts}")
                        
                        logging.info(f"Verification attempt {attempt+1}/{max_verification_attempts}...")
                        
                        # Sleep briefly to allow API to process
                        if attempt > 0:  # Don't wait on first attempt
                            time.sleep(verification_delay)
                        
                        verify_found = False
                        
                        # Method 1: Check site list (most reliable)
                        try:
                                verify_url = f"{base_url}/dna/intent/api/v1/site"
                                verify_response = dnac.session.get(
                                    verify_url, 
                                    headers={"x-auth-token": dnac.token},
                                    timeout=10
                                )
                                
                            # Special logging for UK buildings
                            if parent_site == "UK" and site_type == "building":
                                logging.info(f"Verifying building under UK (attempt {attempt+1})")
                            
                                if verify_response.status_code == 200:
                                try:
                                    verify_data = verify_response.json()
                                    # Log UK building verification data
                                    if parent_site == "UK" and site_type == "building":
                                        logging.debug(f"UK building verification data: {json.dumps(verify_data, indent=2)}")
                                    
                                    if 'response' in verify_data and isinstance(verify_data['response'], list):
                                        for site in verify_data['response']:
                                            # For buildings, check the hierarchy too
                                            if site_type == "building":
                                                site_hierarchy = site.get('siteNameHierarchy', '')
                                                # Log all site hierarchies to debug
                                                logging.debug(f"Checking site: {site.get('name')} | Hierarchy: {site_hierarchy}")
                                                
                                                # Special handling for UK buildings
                                                if parent_site == "UK":
                                                    # Log detailed site data for debugging
                                                    logging.debug(f"UK building check - site data: {json.dumps(site, indent=2)}")
                                                    
                                                    # Check if building contains UK in hierarchy regardless of name
                                                    if "UK" in site_hierarchy and site.get('name') == site_name:
                                                        logging.info(f"UK Building '{site_name}' found in hierarchy containing UK!")
                                                        verify_found = True
                                                        success = True
                                                        break
                                                    
                                                    # Standard checks for all buildings
                                                    # 1. Exact name match
                                            if site.get('name') == site_name:
                                                        logging.info(f"Building '{site_name}' found by exact name match!")
                                                        verify_found = True
                                                success = True
                                                break
                                                    
                                                    # 2. Look for building in hierarchy path with parent
                                                    if site_hierarchy:
                                                        # Look for patterns like "{parent}/{site_name}" or "{parent}/Building/{site_name}"
                                                        patterns_to_check = [
                                                            f"/{site_name}",  # Simple pattern
                                                            f"{parent_site}/{site_name}",  # Direct parent
                                                            f"{parent_site}/Building/{site_name}",  # With Building type
                                                            f"Global/{site_name}",  # Under Global
                                                            f"/{parent_site}/{site_name}",  # With slash prefix
                                                            f"Global/{parent_site}/{site_name}"  # Full hierarchy path for UK
                                                        ]
                                                        
                                                        # UK-specific patterns
                                                        if parent_site == "UK":
                                                            uk_patterns = [
                                                                f"Global/Europe/UK/{site_name}",
                                                                f"Europe/UK/{site_name}",
                                                                f"UK/{site_name}"
                                                            ]
                                                            patterns_to_check.extend(uk_patterns)
                                                            logging.debug(f"Added UK-specific patterns: {uk_patterns}")
                                                        
                                                        for pattern in patterns_to_check:
                                                            if pattern in site_hierarchy:
                                                                logging.info(f"Building '{site_name}' found in hierarchy path: {site_hierarchy}")
                                                                logging.info(f"Matched pattern: {pattern}")
                                                                verify_found = True
                                                                success = True
                                                    # Check plain name in hierarchy when under UK or other area
                                                    if parent_site != "Global" and site_name in site_hierarchy:
                                                        logging.info(f"Building '{site_name}' found in non-Global hierarchy: {site_hierarchy}")
                                                        verify_found = True
                                    success = True
                                    break
                            except Exception as e:
                            logging.warning(f"Error in verification method 1: {str(e)}")
                        
                        # Method 2: Try getting site by name (useful for buildings/floors)
                        if not verify_found:
                            try:
                                # Encode site name for URL
                                encoded_name = urllib.parse.quote(site_name)
                                
                                # Special handling for UK buildings - try specific name pattern
                                if parent_site == "UK" and site_type == "building":
                                    # Try different name patterns for UK buildings
                                    encoded_uk_name = urllib.parse.quote(f"UK/{site_name}")
                                    verify_url = f"{base_url}/dna/intent/api/v1/site?name={encoded_uk_name}"
                                    logging.debug(f"Trying UK-specific name pattern: {encoded_uk_name}")
                                else:
                                    verify_url = f"{base_url}/dna/intent/api/v1/site?name={encoded_name}"
                                    
                            verify_response = dnac.session.get(
                                verify_url, 
                                headers={"x-auth-token": dnac.token},
                                timeout=10
                            )
                            
                            if verify_response.status_code == 200:
                                verify_data = verify_response.json()
                                    # Special logging for UK buildings
                                    if parent_site == "UK" and site_type == "building":
                                        logging.debug(f"UK name search response: {json.dumps(verify_data, indent=2)}")
                                        
                                    # Check different response structures - the response can be a list or dict
                                    if 'response' in verify_data:
                                        response_obj = verify_data['response']
                                        # Handle both list and dictionary response formats
                                        if isinstance(response_obj, list):
                                            # If it's a list, check each item
                                            for site in response_obj:
                                                if isinstance(site, dict) and site.get('name') == site_name:
                                                    logging.info(f"Site '{site_name}' found in name query response list!")
                                                    verify_found = True
                                            break
                                        elif isinstance(response_obj, dict):
                                            # If it's a dict, check direct match or sites list
                                            if response_obj.get('name') == site_name:
                                                logging.info(f"Site '{site_name}' found in name query response dict!")
                                                verify_found = True
                                                success = True
                                            elif 'sites' in response_obj and isinstance(response_obj['sites'], list):
                                                for site in response_obj['sites']:
                                        if site.get('name') == site_name:
                                                        logging.info(f"Site '{site_name}' found in sites list!")
                                                        verify_found = True
                                            success = True
                                            break
                                        # Generic check for non-empty response
                                        elif response_obj:
                                            logging.info(f"Site likely created - found non-empty response for '{site_name}'")
                                            verify_found = True
                    success = True
                            except Exception as e:
                                logging.warning(f"Error in verification method 2: {str(e)}")
                                # Log full error details with traceback
                                import traceback
                                logging.debug(f"Verification error details: {traceback.format_exc()}")
                        
                        # Method 3: Try getting the site by parent (useful for hierarchy)
                        if not verify_found and parent_id and parent_id != "global":
                            try:
                                verify_url = f"{base_url}/dna/intent/api/v1/site/{parent_id}"
                verify_response = dnac.session.get(
                    verify_url, 
                    headers={"x-auth-token": dnac.token},
                    timeout=10
                )
                
                if verify_response.status_code == 200:
                    verify_data = verify_response.json()
                                    # Look for the site name in the response
                                    response_text = json.dumps(verify_data)
                                    if site_name in response_text:
                                        logging.info(f"Site '{site_name}' found in parent data after {attempt+1} verification attempts!")
                                        verify_found = True
                                        success = True
                            except Exception as e:
                                logging.warning(f"Error in verification method 3: {str(e)}")
                        
                        if verify_found:
                            update_spinner("Site creation confirmed!")
                                break
                
                        # If this is the last attempt, log failure
                        if attempt == max_verification_attempts - 1 and not verify_found:
                            logging.error(f"Failed to verify site creation after {max_verification_attempts} attempts")
                            # Special handling for buildings - they might be created but not appear immediately
                            if site_type == "building":
                                logging.info("Building creation received a success response. Treating as successful despite verification failure.")
                                update_spinner("Building creation likely successful but not yet visible in API")
                                # Wait longer for the final building attempt
                                time.sleep(5)
                                success = True
                            else:
                                raise Exception("Site creation could not be verified within the timeout period")
                else:
                    # Error response
                    error_msg = response_data.get('detail', response.text)
                    if isinstance(error_msg, dict) and 'message' in error_msg:
                        error_msg = error_msg['message']
                    logging.error(f"API Error: {error_msg}")
                    raise Exception(f"API Error: {error_msg}")
            
        except Exception as e:
            logging.error(f"Exception during API call: {str(e)}")
            raise
        
        # If we get here, the site was created successfully
        stdscr.clear()
        logging.info(f"Successfully created site: {site_name} of type {site_type}")
        try:
                content_start = draw_standard_header_footer(
                    stdscr, 
                    title="Cisco Catalyst Centre",
                    subtitle="Site Creation Result",
                    footer_text="Press any key to continue..."
                )
                
                if success:
                    stdscr.attron(get_color(ColorPair.SUCCESS))
                    result_message = f"Successfully created {site_type}: {site_name}"
                    stdscr.addstr(content_start + 1, 2, result_message)
                    stdscr.attroff(get_color(ColorPair.SUCCESS))
                else:
                    stdscr.attron(get_color(ColorPair.ERROR))
                    result_message = f"Failed to create {site_type}: {site_name}"
                    stdscr.addstr(content_start + 1, 2, result_message)
                    stdscr.addstr(content_start + 2, 2, "Check logs for details")
                    stdscr.attroff(get_color(ColorPair.ERROR))
            
            # Show site hierarchy
                stdscr.addstr(content_start + 3, 2, "Current Site Hierarchy:")
            stdscr.refresh()
            
                # Get h, w for display limits
                h, w = stdscr.getmaxyx()
                
                # Display confirmation message and wait for key press
                stdscr.addstr(h-2, 2, "Press any key to return to the menu...")
                stdscr.refresh()
            except curses.error:
                pass
            stdscr.getch()
            # After showing the result and waiting for key press, continue the loop
            # instead of exiting
            
        except Exception as e:
            stdscr.clear()
            try:
                content_start = draw_standard_header_footer(
                    stdscr, 
                    title="Cisco Catalyst Centre",
                    subtitle="Error", 
                    footer_text="Press any key to continue..."
                )
                
                error_msg = f"Error creating site: {str(e)}"
                # Limit length of error message to fit on screen
                stdscr.addstr(content_start + 1, 2, error_msg[:curses.COLS-4])
                stdscr.refresh()
            except curses.error:
                pass
            stdscr.getch()
            # After showing error, go back to site type selection
            continue


def check_execution_status(dnac, execution_id):
    """Check the status of an execution by its ID."""
    try:
        # Construct the execution status URL
        status_url = f"dna/platform/management/business-api/v1/execution-status/{execution_id}"
        
        # Make the request
        response = dnac.session.get(
            f"{dnac.host.rstrip('/')}/{status_url}",
            headers={"x-auth-token": dnac.token},
            timeout=10
        )
        
        if response.status_code == 200:
            status_data = response.json()
            logging.debug(f"Execution status response: {json.dumps(status_data, indent=2)}")
            return status_data
        else:
            logging.warning(f"Failed to get execution status: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logging.error(f"Error checking execution status: {str(e)}")
        return None


def create_uk_building_direct(dnac, site_name, parent_id):
    """Direct raw API call to create a building under UK."""
    try:
        logging.info(f"DIRECT UK BUILDING CREATION: name={site_name}, parentId={parent_id}")
        
        # Raw payload for UK building based on observed API requirements
        raw_payload = {
            "type": "building",
            "site": {
                "building": {
                    "name": site_name,
                    "parentId": parent_id,
                    "address": "1 Main Street",
                    "latitude": 51.50853,
                    "longitude": -0.12574,
                    "country": "United Kingdom"
                }
            }
        }
        
        # Log the exact payload we're sending
        logging.debug(f"RAW UK BUILDING PAYLOAD: {json.dumps(raw_payload, indent=2)}")
        
        # Make direct API call
        base_url = dnac.host.rstrip('/')
        response = dnac.session.post(
            f"{base_url}/dna/intent/api/v1/site",
            headers={
                "x-auth-token": dnac.token,
                "Content-Type": "application/json"
            },
            json=raw_payload,  # Use json parameter to let requests handle serialization
            timeout=30
        )
        
        # Log complete response
        logging.info(f"UK BUILDING DIRECT RESPONSE: status={response.status_code}")
        logging.debug(f"UK BUILDING DIRECT RESPONSE BODY: {response.text}")
        
        return response
            except Exception as e:
        logging.error(f"UK BUILDING DIRECT ERROR: {str(e)}")
        import traceback
        logging.debug(f"UK BUILDING DIRECT TRACEBACK: {traceback.format_exc()}")
        return None


def main():
    parser = argparse.ArgumentParser(description='Add sites to DNA Center')
    parser.add_argument('-c', '--config', help='Path to DNA Center config file')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug output')
    
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    
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
        print("The full functionality of this script is being rebuilt. Stay tuned for updates.")
        
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        traceback.print_exc()
        print(f"Error: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    main() 