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


def get_hierarchy(dnac) -> str:
    """Get site hierarchy from Cisco DNA Center."""
    response = dnac.get("dna/intent/api/v1/site")
    
    if not response:
        return "Error: No response from DNA Center"
    
    try:
        # Ensure we have a valid JSON response
        if hasattr(response, 'json') and callable(response.json):
            data = response.json()
            
            if isinstance(data, dict) and 'response' in data:
                sites = data['response']
                
                # Format hierarchy
                output = []
                output.append("Site Hierarchy:")
                output.append("---------------")
                
                # Process global site first
                output.append("Global")
                
                # Helper function to find child sites
                def find_children(parent_id, level=1):
                    children = []
                    for site in sites:
                        # Parse site hierarchy to check parent
                        hierarchy = site.get('siteHierarchy', '')
                        if hierarchy.startswith(parent_id + '/') and hierarchy.count('/') == level:
                            children.append(site)
                    return children
                
                # Find top-level sites (direct children of Global)
                for site in sites:
                    if site.get('name') == 'Global':
                        global_id = site.get('id')
                        
                        # Process children recursively
                        def process_site(site_id, level=0):
                            children = find_children(site_id, level+1)
                            for child in sorted(children, key=lambda x: x.get('name', '')):
                                # Determine site type
                                site_type = "Unknown"
                                if "area" in str(child.get('additionalInfo', {})):
                                    site_type = "Area"
                                elif "building" in str(child.get('additionalInfo', {})):
                                    site_type = "Building"
                                elif "floor" in str(child.get('additionalInfo', {})):
                                    site_type = "Floor"
                                
                                # Add indentation based on level
                                indent = "  " * level
                                output.append(f"{indent}├─ {child.get('name')} ({site_type})")
                                
                                # Process child's children
                                process_site(child.get('id'), level+1)
                        
                        process_site(global_id)
                
                return "\n".join(output)
            else:
                return f"Error: Unexpected response format - {data}"
        else:
            return "Error: Invalid response format"
    except Exception as e:
        return f"Error parsing response: {str(e)}"


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
    
    # Initialize DNAC client with updated class
    dnac = Dnac(hostname)
    
    # Set SSL verification
    dnac.verify = verify

    try:
        # Login and get token
        dnac.login(username, password)
        print("Successfully authenticated")
        
        # Get hierarchy
        print("Fetching site hierarchy...")
        hierarchy_output = get_hierarchy(dnac)
        
        # Use only curses.wrapper, which handles initialization and cleanup properly
        curses.wrapper(display_hierarchy, hierarchy_output)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 
