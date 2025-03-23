#!/usr/bin/env python
"""View site hierarchy from Cisco Catalyst Centre."""

import os
import sys
import argparse
import logging
import yaml
import curses
import atexit
from typing import Dict, Any, Optional, List

# Add parent directory to path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from dnac.core.api import Dnac
from dnac.ui.colors import ColorPair, get_color, initialize_colors
from dnac.ui.components import draw_standard_header_footer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s"
)

DEFAULT_CONFIG_FILE = "config.yaml"

# Register cleanup function to ensure curses is properly shut down
def cleanup_curses():
    """Clean up curses on exit."""
    try:
        curses.endwin()
    except:
        pass

atexit.register(cleanup_curses)


def load_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from file."""
    if config_file is None:
        config_file = DEFAULT_CONFIG_FILE

    if not os.path.exists(config_file):
        print(f"Config file {config_file} not found")
        sys.exit(1)

    with open(config_file) as f:
        return yaml.safe_load(f)


def get_site_type(site_data):
    """
    Determine the site type from site data.
    Returns one of: "Area", "Building", "Floor", or "Unknown"
    """
    # First, let's log the actual data for debugging
    site_name = site_data.get('name', 'Unnamed')
    logging.debug(f"Determining type for site: {site_name}")
    logging.debug(f"Site data keys: {list(site_data.keys())}")
    
    # Check if site has a parent/group type that would indicate an area
    group_name_hierarchy = site_data.get('groupNameHierarchy', '').lower()
    if group_name_hierarchy:
        logging.debug(f"groupNameHierarchy: {group_name_hierarchy}")
    
    # Most direct: Check the site type directly
    site_type_field = site_data.get('siteType')
    if site_type_field:
        logging.debug(f"siteType: {site_type_field}")
        if isinstance(site_type_field, str):
            site_type_field = site_type_field.upper()
            if any(area_term in site_type_field for area_term in ['AREA', 'REGION', 'COUNTRY']):
                return "Area"
            elif 'BUILDING' in site_type_field:
                return "Building" 
            elif 'FLOOR' in site_type_field:
                return "Floor"
    
    # Check the additionalInfo field
    additional_info = site_data.get('additionalInfo')
    if additional_info:
        logging.debug(f"additionalInfo type: {type(additional_info)}")
        logging.debug(f"additionalInfo: {additional_info}")
        
        if isinstance(additional_info, str):
            additional_info_lower = additional_info.lower()
            if any(area_term in additional_info_lower for area_term in ['area', 'region', 'country']):
                return "Area"
            elif "building" in additional_info_lower:
                return "Building"
            elif "floor" in additional_info_lower:
                return "Floor"
        elif isinstance(additional_info, dict):
            # Try to extract type from additionalInfo dict
            type_value = additional_info.get('type')
            if type_value:
                type_value_lower = type_value.lower()
                if any(area_term in type_value_lower for area_term in ['area', 'region', 'country']):
                    return "Area"
                elif "building" in type_value_lower:
                    return "Building"
                elif "floor" in type_value_lower:
                    return "Floor"
                
            # Check for any key that might indicate type
            for key, value in additional_info.items():
                if isinstance(value, str) and 'type' in key.lower():
                    value_lower = value.lower()
                    if any(area_term in value_lower for area_term in ['area', 'region', 'country']):
                        return "Area"
                    elif "building" in value_lower:
                        return "Building"
                    elif "floor" in value_lower:
                        return "Floor"
    
    # Check for type indicators in the hierarchy path
    site_hierarchy = site_data.get('siteHierarchy', '')
    if site_hierarchy:
        logging.debug(f"siteHierarchy: {site_hierarchy}")
        site_hierarchy_lower = site_hierarchy.lower()
        if any(area_term in site_hierarchy_lower for area_term in ['/area/', '/region/', '/country/']):
            return "Area"
        elif '/building/' in site_hierarchy_lower:
            return "Building"
        elif '/floor/' in site_hierarchy_lower:
            return "Floor"
    
    # Check if this is a direct child of Global (likely an area)
    if site_hierarchy and site_hierarchy.count('/') == 1:
        # Only one slash means it's directly under Global
        parent_parts = site_hierarchy.split('/')
        if len(parent_parts) >= 2 and parent_parts[0]:
            # Find the parent site name
            parent_id = parent_parts[0]
            if parent_id and parent_id != site_data.get('id'):
                if site_name not in ["Global", "global"]:
                    # Direct children of Global are typically areas
                    return "Area"
    
    # Last attempt: try to guess from name conventions or position
    name = site_name.lower()
    if any(area_term in name for area_term in ['area', 'region', 'country', 'province', 'state', 'county']):
        return "Area"
    elif any(building_term in name for building_term in ['bldg', 'building', 'campus', 'office', 'hq', 'headquarters']):
        return "Building"
    elif any(floor_term in name for floor_term in ['floor', 'level', 'story', 'storey']):
        return "Floor"
    
    # If we got this far but can tell it's not a building or floor, default to Area for top-level sites
    if not any(term in name for term in ['building', 'bldg', 'floor', 'level']):
        site_hierarchy = site_data.get('siteHierarchy', '')
        # Count slashes to determine depth (fewer slashes = higher in hierarchy)
        slash_count = site_hierarchy.count('/')
        if slash_count <= 2:  # Global/Area or Global/Area/Something
            return "Area"
    
    # Couldn't determine type
    return "Unknown"


def get_hierarchy(dnac) -> str:
    """Get site hierarchy from Cisco DNA Center."""
    logging.info("Fetching site hierarchy from DNAC...")
    response = dnac.get("dna/intent/api/v1/site")
    
    if not response:
        logging.error("No response received from DNA Center")
        return "Error: No response from DNA Center"
    
    try:
        # Ensure we have a valid JSON response
        if hasattr(response, 'json') and callable(response.json):
            data = response.json()
            
            if isinstance(data, dict) and 'response' in data:
                sites = data['response']
                logging.info(f"Received {len(sites)} sites from DNAC")
                
                # Format hierarchy
                output = []
                output.append("Site Hierarchy:")
                output.append("---------------")
                
                # Build a map of site IDs to sites for easy lookup
                site_map = {}
                global_site = None
                
                for site in sites:
                    site_id = site.get('id')
                    if site_id:
                        site_map[site_id] = site
                        # Find the Global site
                        if site.get('name') == 'Global':
                            global_site = site
                            logging.info(f"Found Global site with ID: {site_id}")
                
                if not global_site:
                    logging.error("Global site not found in hierarchy")
                    # Show all site names to help debug
                    site_names = [site.get('name', 'Unknown') for site in sites]
                    logging.debug(f"Available sites: {', '.join(site_names)}")
                    return "Error: Global site not found in hierarchy"
                
                # Add Global to output
                output.append("Global")
                
                # Group sites by their parent ID for more efficient lookup
                children_map = {}
                unprocessed_sites = []
                
                for site in sites:
                    # Skip the Global site as it has no parent
                    if site.get('name') == 'Global':
                        continue
                    
                    # Extract parent ID from siteHierarchy
                    hierarchy = site.get('siteHierarchy', '')
                    if hierarchy:
                        # The parent is the second-to-last ID in the hierarchy path
                        hierarchy_parts = hierarchy.split('/')
                        if len(hierarchy_parts) >= 2:
                            parent_id = hierarchy_parts[-2]  # Second-to-last part is the direct parent
                            if parent_id not in children_map:
                                children_map[parent_id] = []
                            children_map[parent_id].append(site)
                            logging.debug(f"Added site {site.get('name')} as child of parent ID {parent_id}")
                        else:
                            unprocessed_sites.append(site)
                            logging.warning(f"Site {site.get('name')} has invalid hierarchy format: {hierarchy}")
                    else:
                        unprocessed_sites.append(site)
                        logging.warning(f"Site {site.get('name')} has no siteHierarchy attribute")
                
                if unprocessed_sites:
                    logging.warning(f"Could not determine parent for {len(unprocessed_sites)} sites")
                
                # Process the hierarchy recursively starting from Global
                def process_site(site, level=0):
                    site_id = site.get('id')
                    children = children_map.get(site_id, [])
                    
                    if not children and level == 0:
                        logging.warning(f"No children found for Global site (ID: {site_id})")
                        logging.debug(f"Children map keys: {list(children_map.keys())}")
                    
                    # Sort children by name
                    sorted_children = sorted(children, key=lambda x: x.get('name', ''))
                    logging.debug(f"Processing {len(sorted_children)} children for site {site.get('name')}")
                    
                    for child in sorted_children:
                        child_name = child.get('name', 'Unnamed')
                        
                        # Determine site type using the utility function
                        site_type = get_site_type(child)
                        if site_type != "Unknown":
                            logging.debug(f"Determined site type for {child_name}: {site_type}")
                        else:
                            logging.warning(f"Could not determine site type for {child_name}")
                        
                        # Add indentation based on level
                        indent = "  " * level
                        output.append(f"{indent}├─ {child_name} ({site_type})")
                        logging.debug(f"Added {child_name} to output at level {level}")
                        
                        # Process child's children
                        process_site(child, level+1)
                
                # Start processing from the Global site
                process_site(global_site)
                
                logging.info(f"Generated hierarchy with {len(output)} lines")
                return "\n".join(output)
            else:
                logging.error(f"Unexpected response format: {data}")
                return f"Error: Unexpected response format - {data}"
        else:
            logging.error("Invalid response format, cannot convert to JSON")
            return "Error: Invalid response format"
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logging.error(f"Error parsing response: {e}\n{error_trace}")
        return f"Error parsing response: {str(e)}\n{error_trace}"


def display_hierarchy(stdscr, hierarchy_output):
    """Display the hierarchy in a scrollable window."""
    try:
        # Set environment variable to reduce delay for ESC key
        os.environ.setdefault('ESCDELAY', '25')
        
        # Initialize colors
        initialize_colors()
        
        # Hide cursor
        curses.curs_set(0)
        
        # Get window dimensions
        h, w = stdscr.getmaxyx()
        
        # Split hierarchy into lines
        lines = hierarchy_output.split('\n')
        
        # Calculate max scroll position
        max_scroll = max(0, len(lines) - (h - 3))
        
        # Current scroll position
        scroll_pos = 0
        
        # Set shorter timeout for getch() to make the UI more responsive 
        stdscr.timeout(100)
        
        while True:
            # Clear screen
            stdscr.clear()
            
            # Draw standard header/footer
            content_start = draw_standard_header_footer(
                stdscr, 
                title="Cisco Catalyst Centre",
                subtitle="Site Hierarchy",
                footer_text="↑/↓: Scroll | PgUp/PgDn: Page | q: Quit"
            )
            
            # Available display height
            display_height = h - content_start - 2
            
            # Display visible lines
            for y, line in enumerate(lines[scroll_pos:scroll_pos + display_height], 0):
                if content_start + y >= h - 1:
                    break
                try:
                    # Truncate line if too long
                    if len(line) > w - 2:
                        line = line[:w-5] + "..."
                    stdscr.addstr(content_start + y, 1, line)
                except:
                    continue
            
            # Show scroll position if needed
            if max_scroll > 0:
                scroll_percent = (scroll_pos / max_scroll) * 100
                scroll_info = f"Scroll: {scroll_percent:.1f}%"
                try:
                    stdscr.addstr(h-2, w - len(scroll_info) - 2, scroll_info)
                except:
                    pass
                
                # Show scroll indicators
                if scroll_pos > 0:
                    try:
                        stdscr.addstr(content_start, w // 2, "▲")
                    except:
                        pass
                if scroll_pos < max_scroll:
                    try:
                        stdscr.addstr(h-2, w // 2, "▼")
                    except:
                        pass
            
            stdscr.refresh()
            
            # Handle input
            key = stdscr.getch()
            
            # Exit on 'q' immediately
            if key == ord('q'):
                return
            # Also exit on ESC key
            elif key == 27:  # ESC key
                return
            elif key == curses.KEY_UP and scroll_pos > 0:
                scroll_pos -= 1
            elif key == curses.KEY_DOWN and scroll_pos < max_scroll:
                scroll_pos += 1
            elif key == curses.KEY_PPAGE:  # Page Up
                scroll_pos = max(0, scroll_pos - (display_height - 1))
            elif key == curses.KEY_NPAGE:  # Page Down
                scroll_pos = min(max_scroll, scroll_pos + (display_height - 1))
    except Exception as e:
        # Log any exceptions in the display function
        logging.error(f"Error in display_hierarchy: {str(e)}")
        raise


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="View site hierarchy from Cisco Catalyst Centre")
    parser.add_argument("-c", "--config", help=f"Config file (default: {DEFAULT_CONFIG_FILE})")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug output (even more verbose)")
    args = parser.parse_args()

    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
        logging.info("Debug mode enabled")
    elif args.verbose:
        logging.getLogger().setLevel(logging.INFO)
        logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
        logging.info("Verbose mode enabled")
    else:
        # Keep third-party logger quiet
        logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)

    # Load configuration
    try:
        config = load_config(args.config)
        logging.info("Configuration loaded successfully")
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
        print(f"Error loading configuration: {e}")
        sys.exit(1)
    
    # Extract nested configuration values
    server_config = config.get("server", {})
    hostname = server_config.get("host")
    verify = server_config.get("verify_ssl", False)
    
    auth_config = config.get("auth", {})
    username = auth_config.get("username")
    password = auth_config.get("password")
    
    if not all([hostname, username, password]):
        missing = []
        if not hostname: missing.append("hostname")
        if not username: missing.append("username")
        if not password: missing.append("password")
        err_msg = f"Missing required configuration: {', '.join(missing)}"
        logging.error(err_msg)
        print(err_msg)
        sys.exit(1)
    
    # Initialize DNAC client with updated class
    dnac = Dnac(hostname)
    logging.info(f"Connecting to DNAC at {hostname}")
    
    # Set SSL verification
    dnac.verify = verify
    if not verify:
        logging.info("SSL verification disabled")

    try:
        # Login and get token
        dnac.login(username, password)
        logging.info("Successfully authenticated")
        print("Successfully authenticated")
        
        # Get hierarchy
        print("Fetching site hierarchy...")
        hierarchy_output = get_hierarchy(dnac)
        
        # Check if the output looks like an error message
        if hierarchy_output.strip().startswith("Error:"):
            # If running in terminal mode and not from the menu, print the error
            if "curses" not in sys.modules or not curses.has_colors():
                print(hierarchy_output)
                sys.exit(1)
        
        # Display in curses UI
        try:
            curses.wrapper(display_hierarchy, hierarchy_output)
        except Exception as e:
            logging.error(f"Error in curses interface: {e}")
            print(f"Error displaying hierarchy: {e}")
            # If there was an error and we had received error output, print it
            if hierarchy_output.strip().startswith("Error:"):
                print(hierarchy_output)
            sys.exit(1)
        
    except Exception as e:
        logging.error(f"Unhandled error: {e}", exc_info=True)
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 
