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


def get_site_name(stdscr):
    """Get site name with direct input handling."""
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    title = "Enter Site Name"
    
    # Draw title bar
    try:
        stdscr.attron(get_color(ColorPair.HEADER, bold=True))
        for x in range(w):
            stdscr.addstr(0, x, " ")
        stdscr.addstr(0, (w - len(title)) // 2, title)
        stdscr.attroff(get_color(ColorPair.HEADER, bold=True))
    except:
        # Fallback if styling fails
        stdscr.addstr(0, (w - len(title)) // 2, title, curses.A_BOLD)
    
    prompt = "Site Name (required): "
    y_pos = h // 2 - 2
    x_pos = 2
    max_len = w - x_pos - 4
    
    while True:
        stdscr.addstr(y_pos, x_pos, prompt)
        # Clear input area
        for i in range(max_len):
            stdscr.addstr(y_pos, x_pos + len(prompt) + i, " ")
        
        # Save cursor state and make it visible for input
        curses.echo()
        curses.curs_set(1)
        
        try:
            stdscr.move(y_pos, x_pos + len(prompt))
            site_name = stdscr.getstr(max_len).decode('utf-8')
        except Exception as e:
            site_name = ""
            logging.error(f"Error getting site name: {e}")
        
        # Reset cursor state
        curses.noecho()
        curses.curs_set(0)
        
        # Validate
        if not site_name.strip():
            error_msg = "Site name cannot be empty. Press any key to try again."
            stdscr.addstr(y_pos + 2, x_pos, error_msg, get_color(ColorPair.ERROR))
            stdscr.refresh()
            stdscr.getch()  # Wait for key press
            # Clear error message
            stdscr.addstr(y_pos + 2, x_pos, " " * len(error_msg))
            continue
        
        return site_name


def add_site_ui(stdscr, args):
    """Main UI for adding a site."""
    # Initialize curses, but be cautious about the existing state
    try:
        curses.curs_set(0)  # Hide cursor
    except:
        pass  # Ignore if this fails
        
    # Initialize colors if not already done
    try:
        initialize_colors()
    except:
        pass  # Ignore if this fails
        
    # Apply the navy blue background to match the main application
    try:
        stdscr.bkgd(' ', get_color(ColorPair.NORMAL))
    except:
        pass  # Ignore if this fails
    
    stdscr.clear()
    stdscr.refresh()
    
    # Define initialization function
    def initialize_dnac():
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
            return {
                "success": False,
                "error": "Missing required configuration (hostname, username, or password)"
            }
        
        try:
            # Initialize DNAC client
            dnac = Dnac(hostname)
            
            # Set SSL verification
            dnac.verify = verify

            # Login and get token
            dnac.login(username, password)
            
            # Get parent sites for dropdown
            parent_sites = get_parent_sites(dnac)
            parent_site_names = [site["name"] for site in parent_sites]
            
            return {
                "success": True,
                "dnac": dnac,
                "config": config,
                "parent_sites": parent_sites,
                "parent_site_names": parent_site_names
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    # Show loading screen while connecting to DNAC
    result = show_loading_screen(
        stdscr,
        "Add Site to Catalyst Centre",
        "Connecting to Catalyst Centre...",
        initialize_dnac,
        duration=2.5,
        complete_msg="Connection established!"
    )
    
    # Check if initialization was successful
    if not result or not result.get("success", False):
        error = result.get("error", "Unknown initialization error") if result else "Unknown initialization error"
        stdscr.clear()
        
        # Draw title
        h, w = stdscr.getmaxyx()
        title = "Add Site to Catalyst Centre"
        try:
            # Draw title bar with background
            stdscr.attron(get_color(ColorPair.HEADER, bold=True))
            for x in range(w):
                stdscr.addstr(0, x, " ")
            stdscr.addstr(0, (w - len(title)) // 2, title)
            stdscr.attroff(get_color(ColorPair.HEADER, bold=True))
        except:
            # Fallback if styling fails
            stdscr.addstr(0, (w - len(title)) // 2, title, curses.A_BOLD)
        
        # Draw error message
        stdscr.attron(get_color(ColorPair.ERROR))
        stdscr.addstr(3, 2, f"Error: {error}")
        stdscr.attroff(get_color(ColorPair.ERROR))
        
        stdscr.addstr(5, 2, "Press any key to exit")
        stdscr.refresh()
        stdscr.getch()
        return
    
    # Extract the results from the initialization
    dnac = result["dnac"]
    config = result["config"]
    parent_sites = result["parent_sites"]
    parent_site_names = result["parent_site_names"]
    
    # Get screen dimensions
    h, w = stdscr.getmaxyx()
    
    # STEP 1: Get site type using direct selection (not form)
    site_type_options = ["Area", "Building", "Floor"]
    
    stdscr.clear()
    title = "Select Site Type"
    try:
        # Draw title bar with background
        stdscr.attron(get_color(ColorPair.HEADER, bold=True))
        for x in range(w):
            stdscr.addstr(0, x, " ")
        stdscr.addstr(0, (w - len(title)) // 2, title)
        stdscr.attroff(get_color(ColorPair.HEADER, bold=True))
    except:
        # Fallback if styling fails
        stdscr.addstr(0, (w - len(title)) // 2, title, curses.A_BOLD)
    
    # Show selection instructions
    stdscr.addstr(2, 2, "Use arrow keys to select site type:")
    stdscr.refresh()
    
    # Show site type options directly
    current_idx = 0
    
    # Selection loop
    while True:
        # Display options
        for i, option in enumerate(site_type_options):
            y_pos = 4 + i
            x_pos = 4
            
            if i == current_idx:
                stdscr.attron(get_color(ColorPair.SELECTED))
                stdscr.addstr(y_pos, x_pos, f"> {option}")
                stdscr.attroff(get_color(ColorPair.SELECTED))
            else:
                stdscr.addstr(y_pos, x_pos, f"  {option}")
        
        # Show navigation help
        stdscr.addstr(8, 2, "Press Enter to select, or Esc to cancel")
        stdscr.refresh()
        
        # Get input
        key = stdscr.getch()
        
        if key == curses.KEY_UP and current_idx > 0:
            current_idx -= 1
        elif key == curses.KEY_DOWN and current_idx < len(site_type_options) - 1:
            current_idx += 1
        elif key == 10 or key == 13:  # Enter key
            site_type_idx = current_idx
            break
        elif key == 27:  # Escape key
            return  # User canceled
    
    # STEP 2: Get site name using direct string input
    stdscr.clear()
    title = "Enter Site Name"
    
    try:
        # Draw title bar with background
        stdscr.attron(get_color(ColorPair.HEADER, bold=True))
        for x in range(w):
            stdscr.addstr(0, x, " ")
        stdscr.addstr(0, (w - len(title)) // 2, title)
        stdscr.attroff(get_color(ColorPair.HEADER, bold=True))
    except:
        # Fallback if styling fails
        stdscr.addstr(0, (w - len(title)) // 2, title, curses.A_BOLD)
    
    # Show prompt
    prompt = "Enter site name: "
    y_pos = 4
    x_pos = 4
    max_len = w - x_pos - len(prompt) - 4
    
    # Loop until valid input
    while True:
        stdscr.addstr(y_pos, x_pos, prompt)
        
        # Clear input area
        for i in range(max_len):
            stdscr.addstr(y_pos, x_pos + len(prompt) + i, " ")
        
        # Show cursor and enable echo
        curses.echo()
        curses.curs_set(1)
        
        # Get input
        stdscr.move(y_pos, x_pos + len(prompt))
        try:
            site_name = stdscr.getstr(max_len).decode('utf-8')
        except Exception as e:
            site_name = ""
            logging.error(f"Error getting site name: {e}")
        
        # Reset cursor and echo
        curses.noecho()
        curses.curs_set(0)
        
        # Validate input
        if not site_name.strip():
            error_msg = "Site name cannot be empty. Press any key to try again."
            stdscr.attron(get_color(ColorPair.ERROR))
            stdscr.addstr(y_pos + 2, x_pos, error_msg)
            stdscr.attroff(get_color(ColorPair.ERROR))
            stdscr.refresh()
            stdscr.getch()  # Wait for key press
            
            # Clear error message
            stdscr.addstr(y_pos + 2, x_pos, " " * len(error_msg))
            continue
        
        break
    
    # STEP 3: Get parent site using direct selection
    stdscr.clear()
    title = "Select Parent Site"
    
    try:
        # Draw title bar with background
        stdscr.attron(get_color(ColorPair.HEADER, bold=True))
        for x in range(w):
            stdscr.addstr(0, x, " ")
        stdscr.addstr(0, (w - len(title)) // 2, title)
        stdscr.attroff(get_color(ColorPair.HEADER, bold=True))
    except:
        # Fallback if styling fails
        stdscr.addstr(0, (w - len(title)) // 2, title, curses.A_BOLD)
    
    # Show selection instructions
    stdscr.addstr(2, 2, "Use arrow keys to select parent site:")
    
    # Calculate pagination
    items_per_page = min(10, h - 8)  # Leave room for header, instructions, footer
    total_pages = (len(parent_site_names) + items_per_page - 1) // items_per_page
    current_page = 0
    current_idx = 0
    
    # Selection loop
    while True:
        # Calculate page bounds
        start_idx = current_page * items_per_page
        end_idx = min(start_idx + items_per_page, len(parent_site_names))
        
        # Display page info if multiple pages
        if total_pages > 1:
            page_info = f"Page {current_page + 1}/{total_pages}"
            stdscr.addstr(3, w - len(page_info) - 4, page_info)
        
        # Clear options area
        for i in range(items_per_page + 2):
            stdscr.addstr(4 + i, 2, " " * (w - 4))
        
        # Display options for current page
        for i, option_idx in enumerate(range(start_idx, end_idx)):
            y_pos = 4 + i
            x_pos = 4
            option = parent_site_names[option_idx]
            
            # Truncate long options
            if len(option) > w - x_pos - 8:
                option = option[:w - x_pos - 11] + "..."
            
            if option_idx == current_idx:
                stdscr.attron(get_color(ColorPair.SELECTED))
                stdscr.addstr(y_pos, x_pos, f"> {option}")
                stdscr.attroff(get_color(ColorPair.SELECTED))
            else:
                stdscr.addstr(y_pos, x_pos, f"  {option}")
        
        # Show navigation help
        nav_help = "↑/↓: Navigate | Enter: Select | Esc: Cancel"
        if total_pages > 1:
            nav_help += " | PgUp/PgDn: Change Page"
        
        stdscr.addstr(h - 2, 2, nav_help)
        stdscr.refresh()
        
        # Get input
        key = stdscr.getch()
        
        if key == curses.KEY_UP:
            if current_idx > 0:
                current_idx -= 1
                # Update page if needed
                if current_idx < start_idx:
                    current_page = current_idx // items_per_page
        elif key == curses.KEY_DOWN:
            if current_idx < len(parent_site_names) - 1:
                current_idx += 1
                # Update page if needed
                if current_idx >= end_idx:
                    current_page = current_idx // items_per_page
        elif key == curses.KEY_NPAGE:  # Page Down
            if current_page < total_pages - 1:
                current_page += 1
                current_idx = min(current_page * items_per_page, len(parent_site_names) - 1)
        elif key == curses.KEY_PPAGE:  # Page Up
            if current_page > 0:
                current_page -= 1
                current_idx = current_page * items_per_page
        elif key == 10 or key == 13:  # Enter key
            parent_site_idx = current_idx
            break
        elif key == 27:  # Escape key
            return  # User canceled
    
    # Create basic form data
    basic_form_data = {
        "site_type": site_type_idx,
        "site_name": site_name,
        "parent_site": parent_site_idx
    }
    
    # Get additional attributes based on site type
    additional_attrs = {}
    
    # STEP 4: Get additional attributes if needed
    if site_type_idx == 1:  # Building - use simplified direct inputs
        stdscr.clear()
        title = "Building Additional Information (Optional)"
        
        try:
            # Draw title bar with background
            stdscr.attron(get_color(ColorPair.HEADER, bold=True))
            for x in range(w):
                stdscr.addstr(0, x, " ")
            stdscr.addstr(0, (w - len(title)) // 2, title)
            stdscr.attroff(get_color(ColorPair.HEADER, bold=True))
        except:
            # Fallback if styling fails
            stdscr.addstr(0, (w - len(title)) // 2, title, curses.A_BOLD)
        
        # Field definitions
        building_fields = [
            {"label": "Address", "key": "address"},
            {"label": "Latitude", "key": "latitude"},
            {"label": "Longitude", "key": "longitude"}
        ]
        
        # Get each field
        for i, field in enumerate(building_fields):
            y_pos = 3 + i*3
            x_pos = 4
            max_len = w - x_pos - len(field["label"]) - 6
            
            # Show prompt
            stdscr.addstr(y_pos, x_pos, f"{field['label']}: ")
            stdscr.addstr(y_pos + 1, x_pos, "(Press Enter to skip)")
            
            # Clear input area
            for j in range(max_len):
                stdscr.addstr(y_pos, x_pos + len(field["label"]) + 2 + j, " ")
            
            # Get input
            curses.echo()
            curses.curs_set(1)
            
            stdscr.move(y_pos, x_pos + len(field["label"]) + 2)
            try:
                value = stdscr.getstr(max_len).decode('utf-8')
                if value.strip():
                    additional_attrs[field["key"]] = value
            except Exception as e:
                logging.error(f"Error getting {field['key']}: {e}")
            
            curses.noecho()
            curses.curs_set(0)
    
    elif site_type_idx == 2:  # Floor - use simplified direct inputs
        stdscr.clear()
        title = "Floor Additional Information"
        
        try:
            # Draw title bar with background
            stdscr.attron(get_color(ColorPair.HEADER, bold=True))
            for x in range(w):
                stdscr.addstr(0, x, " ")
            stdscr.addstr(0, (w - len(title)) // 2, title)
            stdscr.attroff(get_color(ColorPair.HEADER, bold=True))
        except:
            # Fallback if styling fails
            stdscr.addstr(0, (w - len(title)) // 2, title, curses.A_BOLD)
        
        # Get floor number
        y_pos = 3
        x_pos = 4
        prompt = "Floor Number: "
        max_len = 5
        
        stdscr.addstr(y_pos, x_pos, prompt)
        
        # Get floor number
        while True:
            # Clear input area
            for i in range(max_len):
                stdscr.addstr(y_pos, x_pos + len(prompt) + i, " ")
            
            curses.echo()
            curses.curs_set(1)
            
            stdscr.move(y_pos, x_pos + len(prompt))
            try:
                floor_number = stdscr.getstr(max_len).decode('utf-8')
            except Exception as e:
                floor_number = ""
                logging.error(f"Error getting floor number: {e}")
            
            curses.noecho()
            curses.curs_set(0)
            
            # Validate (must be a number)
            if floor_number.strip():
                try:
                    int(floor_number)
                    additional_attrs["floor_number"] = floor_number
                    break
                except ValueError:
                    error_msg = "Floor number must be a number. Press any key to try again."
                    stdscr.attron(get_color(ColorPair.ERROR))
                    stdscr.addstr(y_pos + 2, x_pos, error_msg)
                    stdscr.attroff(get_color(ColorPair.ERROR))
                    stdscr.refresh()
                    stdscr.getch()  # Wait for key press
                    
                    # Clear error message
                    stdscr.addstr(y_pos + 2, x_pos, " " * len(error_msg))
                    continue
            else:
                # Default to 1 if not provided
                additional_attrs["floor_number"] = "1"
                break
        
        # Get RF model using direct selection
        rf_models = [
            "Indoor High Ceiling",
            "Outdoor Open Space",
            "Indoor Low Ceiling",
            "Cubes And Walled Offices"
        ]
        
        stdscr.addstr(y_pos + 3, x_pos, "RF Model:")
        stdscr.addstr(y_pos + 4, x_pos, "Use arrow keys to select:")
        
        # Selection loop
        current_rf_idx = 0
        
        while True:
            # Display options
            for i, option in enumerate(rf_models):
                option_y = y_pos + 5 + i
                option_x = x_pos + 2
                
                if i == current_rf_idx:
                    stdscr.attron(get_color(ColorPair.SELECTED))
                    stdscr.addstr(option_y, option_x, f"> {option}")
                    stdscr.attroff(get_color(ColorPair.SELECTED))
                else:
                    stdscr.addstr(option_y, option_x, f"  {option}")
            
            # Show navigation help
            stdscr.addstr(y_pos + 10, x_pos, "Press Enter to select")
            stdscr.refresh()
            
            # Get input
            key = stdscr.getch()
            
            if key == curses.KEY_UP and current_rf_idx > 0:
                current_rf_idx -= 1
            elif key == curses.KEY_DOWN and current_rf_idx < len(rf_models) - 1:
                current_rf_idx += 1
            elif key == 10 or key == 13:  # Enter key
                additional_attrs["rf_model_idx"] = current_rf_idx
                break
    
    # STEP 5: Display summary and confirmation
    stdscr.clear()
    title = "Confirm Site Creation"
    
    try:
        # Draw title bar with background
        stdscr.attron(get_color(ColorPair.HEADER, bold=True))
        for x in range(w):
            stdscr.addstr(0, x, " ")
        stdscr.addstr(0, (w - len(title)) // 2, title)
        stdscr.attroff(get_color(ColorPair.HEADER, bold=True))
    except:
        # Fallback if styling fails
        stdscr.addstr(0, (w - len(title)) // 2, title, curses.A_BOLD)
    
    # Display summary
    site_type_name = site_type_options[site_type_idx]
    parent_name = parent_site_names[parent_site_idx]
    
    stdscr.addstr(2, 2, f"Site Type: {site_type_name}")
    stdscr.addstr(3, 2, f"Site Name: {site_name}")
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
    stdscr.addstr(row + 2, 2, "Create this site? (Y/n): ")
    stdscr.refresh()
    
    # Get confirmation
    curses.echo()
    curses.curs_set(1)
    confirm = stdscr.getstr(row + 2, 23, 1).decode('utf-8').lower()
    curses.noecho()
    curses.curs_set(0)
    
    if confirm not in ('', 'y'):
        stdscr.addstr(row + 4, 2, "Site creation cancelled")
        stdscr.addstr(row + 6, 2, "Press any key to return")
        stdscr.refresh()
        stdscr.getch()
        return
    
    # STEP 6: Create the site
    stdscr.clear()
    title = "Creating Site"
    
    try:
        # Draw title bar with background
        stdscr.attron(get_color(ColorPair.HEADER, bold=True))
        for x in range(w):
            stdscr.addstr(0, x, " ")
        stdscr.addstr(0, (w - len(title)) // 2, title)
        stdscr.attroff(get_color(ColorPair.HEADER, bold=True))
    except:
        # Fallback if styling fails
        stdscr.addstr(0, (w - len(title)) // 2, title, curses.A_BOLD)
    
    stdscr.addstr(2, 2, "Sending request to Catalyst Centre...")
    stdscr.refresh()
    
    try:
        # Create site data from form inputs
        site_data = create_site_data(
            site_type_idx,
            site_name,
            parent_site_idx,
            parent_sites,
            additional_attrs
        )
        
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