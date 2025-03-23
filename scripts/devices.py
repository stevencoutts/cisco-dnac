#!/usr/bin/env python
"""List network devices from Cisco Catalyst Centre."""

import json
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


def get_devices(dnac) -> List[Dict[str, Any]]:
    """Get network devices from Cisco DNA Center."""
    response = dnac.get("dna/intent/api/v1/network-device")
    
    if not response:
        return []
    
    try:
        if hasattr(response, 'json') and callable(response.json):
            devices_data = response.json()
            
            # Check if response is a dict/list
            if isinstance(devices_data, (dict, list)):
                # If it's a dict, it might have a 'response' key with the actual data
                if isinstance(devices_data, dict) and 'response' in devices_data:
                    devices_data = devices_data['response']
                
                return devices_data
    except Exception as e:
        logging.error(f"Error processing devices: {e}")
    
    return []


def display_devices(stdscr, devices):
    """Display devices in a scrollable window."""
    try:
        # Set environment variable to reduce delay for ESC key
        os.environ.setdefault('ESCDELAY', '25')
        
        # Initialize colors
        initialize_colors()
        
        # Hide cursor
        curses.curs_set(0)
        
        # Get window dimensions
        h, w = stdscr.getmaxyx()
        
        # Current scroll position
        scroll_pos = 0
        
        # Set shorter timeout for getch() to make the UI more responsive
        stdscr.timeout(100)
        
        # Format device info
        lines = []
        
        # Add header
        lines.append("Network Devices:")
        lines.append("---------------")
        
        # Format column headers
        fmt = "{:20} {:16} {:20} {:16} {:12} {:10}"
        lines.append(fmt.format("Hostname", "Management IP", "Platform", "Serial", "SW Version", "Status"))
        lines.append("-" * min(w-2, 100))
        
        # Format device rows
        for device in devices:
            try:
                device_line = fmt.format(
                    str(device.get('hostname', 'N/A'))[:20],
                    str(device.get('managementIpAddress', 'N/A'))[:16],
                    str(device.get('platformId', 'N/A'))[:20], 
                    str(device.get('serialNumber', 'N/A'))[:16],
                    str(device.get('softwareVersion', 'N/A'))[:12],
                    str(device.get('reachabilityStatus', 'N/A'))[:10]
                )
                lines.append(device_line)
            except Exception as e:
                lines.append(f"Error formatting device: {str(e)}")
        
        # Add footer
        lines.append("-" * min(w-2, 100))
        lines.append(f"Total devices: {len(devices)}")
        
        # Calculate max scroll position
        max_scroll = max(0, len(lines) - (h - 4))
        
        while True:
            # Clear screen
            stdscr.clear()
            
            # Draw standard header/footer
            content_start = draw_standard_header_footer(
                stdscr, 
                title="Cisco Catalyst Centre",
                subtitle="Network Devices",
                footer_text="↑/↓: Scroll | PgUp/PgDn: Page | q: Quit"
            )
            
            # Available display height
            display_height = h - content_start - 2
            
            # Display visible lines
            for y, line in enumerate(lines[scroll_pos:scroll_pos + display_height], 0):
                if content_start + y >= h - 1:
                    break
                try:
                    # Highlight headers
                    if y < 4 and scroll_pos == 0:
                        stdscr.attron(get_color(ColorPair.HIGHLIGHT))
                        stdscr.addstr(content_start + y, 1, line[:w-2])
                        stdscr.attroff(get_color(ColorPair.HIGHLIGHT))
                    else:
                        # Color status based on value
                        if y > 3 and "Reachable" in line[-10:]:
                            parts = line.rsplit(' ', 1)
                            if len(parts) == 2:
                                stdscr.addstr(content_start + y, 1, parts[0])
                                stdscr.attron(get_color(ColorPair.SUCCESS))
                                stdscr.addstr(content_start + y, 1 + len(parts[0]), parts[1])
                                stdscr.attroff(get_color(ColorPair.SUCCESS))
                        elif y > 3 and "Unreachable" in line[-10:]:
                            parts = line.rsplit(' ', 1)
                            if len(parts) == 2:
                                stdscr.addstr(content_start + y, 1, parts[0])
                                stdscr.attron(get_color(ColorPair.ERROR))
                                stdscr.addstr(content_start + y, 1 + len(parts[0]), parts[1])
                                stdscr.attroff(get_color(ColorPair.ERROR))
                        else:
                            stdscr.addstr(content_start + y, 1, line[:w-2])
                except:
                    continue
            
            # Show scroll indicators if needed
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
            
            # Show scroll position
            if max_scroll > 0:
                scroll_percent = (scroll_pos / max_scroll) * 100
                scroll_info = f"Scroll: {scroll_percent:.1f}%"
                try:
                    stdscr.addstr(h-2, w - len(scroll_info) - 2, scroll_info)
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
        logging.error(f"Error in display_devices: {str(e)}")
        raise


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="List network devices from Cisco Catalyst Centre")
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
        
        # Get network devices
        print("Fetching network devices...")
        devices = get_devices(dnac)
        
        # Handle displaying devices with proper curses cleanup
        if devices:
            curses.wrapper(display_devices, devices)
        else:
            print("No devices found or error occurred")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 