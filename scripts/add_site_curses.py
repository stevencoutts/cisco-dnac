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
from dnac.ui.colors import initialize_colors, ColorPair, get_color
from dnac.cli.loading import show_loading_screen
from dnac.ui.components import draw_title, draw_cisco_logo, draw_progress_bar, draw_spinner

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


def create_site_data(site_type, site_name, parent_site=None):
    """Create site data payload based on type and name."""
    site_data = {
        "type": site_type,
        "site": {
            "area": None,
            "building": None,
            "floor": None
        }
    }
    
    # Set the appropriate site type data
    if site_type == "area":
        site_data["site"]["area"] = {
            "name": site_name,
            "parentName": parent_site if parent_site else "Global"
        }
    elif site_type == "building":
        site_data["site"]["building"] = {
            "name": site_name,
            "parentName": parent_site if parent_site else "Global",
            "address": ""  # Optional address field
        }
    elif site_type == "floor":
        site_data["site"]["floor"] = {
            "name": site_name,
            "parentName": parent_site if parent_site else "Global",
            "rfModel": "Cubes And Walled Offices"  # Default RF model
        }
    
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
    
    # Draw title
    try:
        title = "Enter Site Name"
        stdscr.addstr(0, 2, title)
    except curses.error:
        pass
    
    # Draw prompt
    prompt = "Site Name: "
    try:
        stdscr.addstr(2, 4, prompt)
        
        # Draw note
        note = "(Press Enter when done)"
        stdscr.addstr(3, 4, note)
    except curses.error:
        pass
    
    stdscr.refresh()
    
    # Calculate input field size
    max_len = min(50, w - len(prompt) - 6)
    
    # Get input
    try:
        # Position cursor
        stdscr.move(2, 4 + len(prompt))
        
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


def add_site_ui(stdscr, args):
    """Main UI function for adding a site."""
    # Initialize curses
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_GREEN)
    curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_RED)
    
    # Get screen dimensions
    h, w = stdscr.getmaxyx()
    
    try:
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
            raise ValueError("Missing required configuration: hostname, username, or password")
        
        # Initialize DNAC client
        dnac = Dnac(hostname)
        dnac.verify = verify
        
        # Show loading screen
        stdscr.clear()
        try:
            stdscr.addstr(0, 2, "Connecting to DNAC...")
            stdscr.refresh()
        except curses.error:
            pass
        
        # Login and get token
        dnac.login(username, password)
        
        # Step 1: Select site type
        site_types = [
            {"name": "Area", "value": "area"},
            {"name": "Building", "value": "building"},
            {"name": "Floor", "value": "floor"}
        ]
        
        stdscr.clear()
        try:
            stdscr.addstr(0, 2, "Select site type:")
            stdscr.refresh()
        except curses.error:
            pass
        
        selected_type = show_dropdown_menu(stdscr, [t["name"] for t in site_types], 1, 2)
        if selected_type is None:
            return
        
        site_type = site_types[selected_type]["value"]
        
        # Step 2: Get site name
        site_name = get_site_name(stdscr)
        if not site_name:
            stdscr.clear()
            try:
                stdscr.addstr(0, 2, "Site name is required. Press any key to return.")
                stdscr.refresh()
                stdscr.getch()
            except curses.error:
                pass
            return
        
        # Step 3: Select parent site
        stdscr.clear()
        try:
            stdscr.addstr(0, 2, "Fetching available parent sites...")
            stdscr.refresh()
        except curses.error:
            pass
        
        parent_sites = get_parent_sites(dnac)
        if parent_sites:
            stdscr.clear()
            try:
                stdscr.addstr(0, 2, "Select parent site (optional):")
                stdscr.refresh()
            except curses.error:
                pass
            
            # Create list of site names for display
            site_names = ["None (Global)"]
            for site in parent_sites:
                site_names.append(site.get("name", "Unknown"))
            
            selected_parent = show_dropdown_menu(stdscr, site_names, 1, 2)
            if selected_parent is None:
                return
            # If "None (Global)" is selected (index 0), use None as parent
            parent_site = None if selected_parent == 0 else parent_sites[selected_parent - 1]["name"]
        else:
            parent_site = None
        
        # Create site data
        site_data = create_site_data(site_type, site_name, parent_site)
        
        # Show confirmation
        stdscr.clear()
        try:
            stdscr.addstr(0, 2, "Confirm site creation:")
            stdscr.addstr(1, 4, f"Type: {site_type.title()}")
            stdscr.addstr(2, 4, f"Name: {site_name}")
            stdscr.addstr(3, 4, f"Parent: {parent_site if parent_site else 'Global'}")
            stdscr.addstr(5, 2, "Press 'y' to confirm, any other key to cancel:")
            stdscr.refresh()
        except curses.error:
            pass
        
        if stdscr.getch() != ord('y'):
            return
        
        # Create site
        stdscr.clear()
        try:
            stdscr.addstr(0, 2, "Creating site...")
            stdscr.refresh()
        except curses.error:
            pass
        
        try:
            response = dnac.post("site", data=site_data, ver="v1")
            
            # Handle different response formats
            if isinstance(response, int):
                # If response is just a status code
                status_code = response
                response_text = "Site created successfully"
            elif hasattr(response, 'response'):
                # If response has a response attribute
                status_code = response.response.status_code
                response_text = response.response.text if hasattr(response.response, 'text') else str(response.response)
            else:
                # Default case
                status_code = getattr(response, 'status_code', 500)
                response_text = str(response)
            
            stdscr.clear()
            if status_code in (200, 201, 202, 204):
                try:
                    stdscr.addstr(0, 2, "Site created successfully!")
                    stdscr.addstr(1, 2, "Press any key to continue...")
                    stdscr.refresh()
                except curses.error:
                    pass
                stdscr.getch()
            else:
                try:
                    # Limit response text length to prevent drawing errors
                    error_msg = f"Failed to create site (Status {status_code})"
                    stdscr.addstr(0, 2, error_msg)
                    # Split response text into multiple lines if needed
                    if response_text:
                        text_lines = str(response_text).split('\n')
                        for i, line in enumerate(text_lines[:3]):  # Show at most 3 lines
                            if len(line) > w - 4:
                                line = line[:w - 7] + "..."
                            stdscr.addstr(i + 1, 2, line)
                    stdscr.addstr(5, 2, "Press any key to continue...")
                    stdscr.refresh()
                except curses.error:
                    pass
                stdscr.getch()
        except Exception as e:
            stdscr.clear()
            try:
                error_msg = f"Error creating site: {str(e)[:w-4]}"
                stdscr.addstr(0, 2, error_msg)
                stdscr.addstr(1, 2, "Press any key to continue...")
                stdscr.refresh()
            except curses.error:
                pass
            stdscr.getch()
    
    except Exception as e:
        stdscr.clear()
        try:
            error_msg = f"Error: {str(e)[:w-4]}"
            stdscr.addstr(0, 2, error_msg)
            stdscr.addstr(1, 2, "Press any key to continue...")
            stdscr.refresh()
        except curses.error:
            pass
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