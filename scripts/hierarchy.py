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
import curses
from typing import Dict, Any, Optional, List

from dnac.core.api import Dnac
from dnac.ui.colors import get_color, ColorPair

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


def get_hierarchy_with_details(dnac, args, stdscr=None):
    """Fetch site hierarchy with additional details from DNAC."""
    try:
        # Get site topology
        if stdscr:
            stdscr.addstr(0, 2, "Fetching site hierarchy...")
            stdscr.refresh()
        
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
                    if stdscr:
                        stdscr.addstr(1, 2, f"Processing site {i+1}/{len(sites_data)}...")
                        stdscr.refresh()
                    
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
        error_msg = f"Error processing site data: {e}"
        if stdscr:
            stdscr.addstr(0, 2, error_msg)
            stdscr.refresh()
        return error_msg


def display_hierarchy(stdscr, hierarchy_output):
    """Display the hierarchy in a scrollable window."""
    # Get screen dimensions
    h, w = stdscr.getmaxyx()
    
    # Clear screen
    stdscr.clear()
    
    # Draw title
    title = "Site Hierarchy"
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
    
    # Split output into lines
    lines = hierarchy_output.split('\n')
    
    # Initialize scroll position
    scroll_pos = 0
    max_scroll = max(0, len(lines) - (h - 3))  # Leave room for header and footer
    
    while True:
        # Clear content area
        for y in range(1, h-1):
            stdscr.addstr(y, 0, " " * w)
        
        # Display visible lines
        for y, line in enumerate(lines[scroll_pos:scroll_pos + h - 3], 1):
            if y >= h - 1:
                break
            try:
                # Truncate line if too long
                if len(line) > w - 2:
                    line = line[:w-5] + "..."
                stdscr.addstr(y, 1, line)
            except:
                continue
        
        # Show navigation help
        help_text = "↑/↓: Scroll | PgUp/PgDn: Page | q: Quit"
        stdscr.addstr(h-1, 2, help_text)
        
        # Show scroll position
        if max_scroll > 0:
            scroll_percent = (scroll_pos / max_scroll) * 100
            scroll_info = f"Scroll: {scroll_percent:.1f}%"
            stdscr.addstr(h-1, w - len(scroll_info) - 2, scroll_info)
        
        stdscr.refresh()
        
        # Handle input
        key = stdscr.getch()
        
        if key == curses.KEY_UP and scroll_pos > 0:
            scroll_pos -= 1
        elif key == curses.KEY_DOWN and scroll_pos < max_scroll:
            scroll_pos += 1
        elif key == curses.KEY_PPAGE:  # Page Up
            scroll_pos = max(0, scroll_pos - (h - 3))
        elif key == curses.KEY_NPAGE:  # Page Down
            scroll_pos = min(max_scroll, scroll_pos + (h - 3))
        elif key == ord('q'):
            break


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="Display site hierarchy from Cisco Catalyst Centre")
    parser.add_argument("-c", "--config", help=f"Config file (default: {DEFAULT_CONFIG_FILE})")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("urllib3.connectionpool").setLevel(logging.DEBUG)

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
            print("Missing required configuration: hostname, username, or password")
            sys.exit(1)
        
        # Initialize DNAC client
        dnac = Dnac(hostname)
        
        # Set SSL verification
        dnac.verify = verify

        # Login and get token
        dnac.login(username, password)
        
        # Get hierarchy data
        hierarchy_output = get_hierarchy_with_details(dnac, args)
        
        # Check if we're running in a terminal that supports curses
        if os.isatty(sys.stdout.fileno()):
            # Display in curses interface
            curses.wrapper(lambda stdscr: display_hierarchy(stdscr, hierarchy_output))
        else:
            # Print output directly if not in a terminal
            print(hierarchy_output)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 
