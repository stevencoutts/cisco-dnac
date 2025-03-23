#!/usr/bin/env python3
import curses
import sys
import subprocess
import os
import yaml
import json
import requests
import time
import urllib3
import warnings
from typing import List, Tuple, Dict, Any

# Suppress warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=ResourceWarning)

def load_config() -> Dict[str, Any]:
    """Load configuration from config.yaml file."""
    try:
        with open('config.yaml', 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {
            'server': {
                'host': 'https://sandboxdnac.cisco.com',
                'port': 443,
                'verify_ssl': False,
                'timeout': 30
            },
            'auth': {
                'username': 'devnetuser',
                'password': 'Cisco123!'
            }
        }

def check_fabric_enabled() -> bool:
    """Check if Fabric/SDA is enabled on the Catalyst Centre."""
    try:
        config = load_config()
        
        # Build the URL
        host = config['server']['host']
        if not host.startswith('http'):
            host = f"https://{host}"
        if host.endswith('/'):
            host = host[:-1]
            
        port = config['server'].get('port', 443)
        base_url = f"{host}:{port}"
        
        # Authentication
        auth_url = f"{base_url}/dna/system/api/v1/auth/token"
        username = config['auth']['username']
        password = config['auth']['password']
        
        verify_ssl = config['server'].get('verify_ssl', True)
        
        # Get auth token - with proper warning suppression
        try:
            auth_response = requests.post(
                auth_url,
                auth=(username, password),
                verify=verify_ssl,
                timeout=5  # Add timeout to prevent hanging
            )
            auth_response.raise_for_status()
            token = auth_response.json().get('Token')
            
            if not token:
                return False
                
            # Check for virtual networks (which indicates SDA/Fabric is enabled)
            vn_url = f"{base_url}/dna/intent/api/v2/virtual-network"
            headers = {
                'x-auth-token': token,
                'Content-Type': 'application/json'
            }
            
            vn_response = requests.get(
                vn_url,
                headers=headers,
                verify=verify_ssl,
                timeout=5  # Add timeout to prevent hanging
            )
            
            # If we get a successful response with data, SDA is enabled
            if vn_response.status_code == 200:
                data = vn_response.json()
                # Check if response contains any virtual networks
                return bool(data and isinstance(data, list) and len(data) > 0)
            
            return False
        except requests.exceptions.SSLError:
            # Suppress SSL errors, just return False
            return False
        except requests.exceptions.ConnectionError:
            # Suppress connection errors, just return False
            return False
        except requests.exceptions.Timeout:
            # Handle timeout errors
            return False
        except requests.exceptions.RequestException:
            # Handle all other request errors
            return False
        except json.JSONDecodeError:
            # Handle JSON parsing errors
            return False
    except Exception:
        # In case of any error, assume SDA is not enabled
        return False

def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to config.yaml file."""
    with open('config.yaml', 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

def edit_config(stdscr) -> None:
    """Edit configuration settings in a curses window."""
    config = load_config()
    current_section = 0
    current_field = 0
    editing = False
    edit_buffer = ""
    
    sections = ['server', 'auth']
    fields = {
        'server': ['host', 'port', 'verify_ssl', 'timeout'],
        'auth': ['username', 'password']
    }
    
    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        
        # Draw title
        title = "DNAC Configuration Editor"
        stdscr.addstr(0, (w - len(title)) // 2, title)
        
        # Draw sections and fields
        y = 2
        for section_idx, section in enumerate(sections):
            # Draw section header
            stdscr.attron(curses.A_BOLD)
            stdscr.addstr(y, 2, f"{section.upper()} Settings:")
            stdscr.attroff(curses.A_BOLD)
            y += 1
            
            # Draw fields
            for field_idx, field in enumerate(fields[section]):
                value = str(config[section][field])
                prefix = "> " if section_idx == current_section and field_idx == current_field else "  "
                display_value = "*" * len(value) if field == "password" else value
                line = f"{prefix}{field}: {display_value}"
                stdscr.addstr(y, 4, line)
                y += 1
            y += 1
        
        # Draw instructions
        instructions = [
            "Use ↑↓ to navigate, Enter to edit, 's' to save, 'q' to quit",
            "Current value: " + (edit_buffer if editing else "")
        ]
        for i, instr in enumerate(instructions):
            stdscr.addstr(h-2+i, 2, instr)
        
        stdscr.refresh()
        
        # Handle input
        key = stdscr.getch()
        
        if editing:
            if key == ord('\n'):  # Enter
                # Save the edited value
                section = sections[current_section]
                field = fields[section][current_field]
                try:
                    if field in ['port', 'timeout']:
                        config[section][field] = int(edit_buffer)
                    elif field == 'verify_ssl':
                        config[section][field] = edit_buffer.lower() == 'true'
                    else:
                        config[section][field] = edit_buffer
                except ValueError:
                    pass  # Keep old value if conversion fails
                editing = False
                edit_buffer = ""
            elif key == 27:  # ESC
                editing = False
                edit_buffer = ""
            elif key == curses.KEY_BACKSPACE or key == 127:
                edit_buffer = edit_buffer[:-1]
            else:
                edit_buffer += chr(key)
        else:
            if key == ord('q'):
                break
            elif key == ord('s'):
                save_config(config)
                stdscr.addstr(h-1, 2, "Configuration saved! Press any key to continue...")
                stdscr.refresh()
                stdscr.getch()
            elif key == ord('\n'):
                editing = True
                section = sections[current_section]
                field = fields[section][current_field]
                edit_buffer = str(config[section][field])
            elif key == curses.KEY_UP:
                if current_field > 0:
                    current_field -= 1
                elif current_section > 0:
                    current_section -= 1
                    current_field = len(fields[sections[current_section]]) - 1
            elif key == curses.KEY_DOWN:
                if current_field < len(fields[sections[current_section]]) - 1:
                    current_field += 1
                elif current_section < len(sections) - 1:
                    current_section += 1
                    current_field = 0

def run_script(script_name: str) -> None:
    """Run a Python script and handle its output."""
    try:
        # Run the script and capture output
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Create a new window for output with proper padding
        output_win = curses.newwin(curses.LINES-2, curses.COLS, 1, 0)
        output_win.keypad(True)  # Enable keypad for arrow keys
        
        # Calculate safe boundaries
        max_y = curses.LINES - 4  # Leave space for border, header and instructions
        max_x = curses.COLS - 4   # Leave space for borders
        
        # Split output into lines and display
        lines = result.stdout.split('\n')
        total_lines = len(lines)
        scroll_pos = 0
        
        # Calculate max scroll position
        max_scroll = max(0, total_lines - max_y)
        
        # Flag to track if we need to redraw
        redraw = True
        
        while True:
            if redraw:
                output_win.clear()
                output_win.box()
                
                # Add header with scroll position information for debugging
                header = f"Output from {script_name} (line {scroll_pos+1}/{total_lines})"
                try:
                    output_win.addstr(1, 2, header[:max_x])
                except curses.error:
                    pass
                
                # Display visible lines
                display_lines = min(max_y, total_lines - scroll_pos)
                for i in range(display_lines):
                    y_pos = i + 2  # Start at line 2 (after header)
                    line_idx = scroll_pos + i
                    
                    if line_idx < total_lines and y_pos < curses.LINES - 2:
                        try:
                            # Truncate line to fit window width
                            line = lines[line_idx][:max_x]
                            output_win.addstr(y_pos, 2, line)
                        except curses.error:
                            continue
                
                # Add scroll indicators
                if scroll_pos > 0:
                    try:
                        output_win.addstr(1, max_x + 1, "↑")
                    except curses.error:
                        pass
                
                if scroll_pos < max_scroll:
                    try:
                        output_win.addstr(max_y + 1, max_x + 1, "↓")
                    except curses.error:
                        pass
                
                # Add instructions at the bottom
                try:
                    output_win.addstr(curses.LINES-3, 2, 
                                     "↑/↓: scroll 1 line, PgUp/PgDn: scroll page, Home/End: start/end, q: quit")
                except curses.error:
                    pass
                
                output_win.refresh()
                redraw = False
            
            # Handle user input
            key = output_win.getch()
            
            if key == ord('q'):
                break
            elif key == curses.KEY_UP:
                if scroll_pos > 0:
                    scroll_pos -= 1
                    redraw = True
            elif key == curses.KEY_DOWN:
                if scroll_pos < max_scroll:
                    scroll_pos += 1
                    redraw = True
            elif key == curses.KEY_PPAGE:  # Page Up
                scroll_pos = max(0, scroll_pos - max_y)
                redraw = True
            elif key == curses.KEY_NPAGE:  # Page Down
                scroll_pos = min(max_scroll, scroll_pos + max_y)
                redraw = True
            elif key == curses.KEY_HOME:  # Home
                scroll_pos = 0
                redraw = True
            elif key == curses.KEY_END:  # End
                scroll_pos = max_scroll
                redraw = True
                
    except subprocess.CalledProcessError as e:
        # Handle script errors
        error_win = curses.newwin(10, 50, curses.LINES//2-5, curses.COLS//2-25)
        error_win.box()
        try:
            error_win.addstr(1, 2, f"Error running {script_name}:")
            error_win.addstr(2, 2, str(e))
            error_win.addstr(3, 2, e.stderr)
            error_win.addstr(4, 2, "Press any key to continue")
        except curses.error:
            pass
        error_win.refresh()
        error_win.getch()

def draw_menu(stdscr, selected_idx: int, options: List[str], fabric_enabled: bool = False) -> None:
    """Draw the menu with the current selection."""
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    
    # Define title
    title = "Cisco Catalyst Centre Tools"
    
    # Draw title
    try:
        stdscr.addstr(0, (w - len(title)) // 2, title)
    except curses.error:
        pass
    
    # Add fabric status indicator
    if fabric_enabled:
        fabric_status = "● FABRIC ENABLED"
        try:
            # Use color to highlight fabric status
            stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
            stdscr.addstr(0, w - len(fabric_status) - 2, fabric_status)
            stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
        except curses.error:
            pass
    else:
        fabric_status = "○ FABRIC DISABLED"
        try:
            # Use color to show disabled status
            stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(0, w - len(fabric_status) - 2, fabric_status)
            stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
        except curses.error:
            pass
    
    # Calculate visible range
    visible_height = h - 4  # Leave space for title and instructions
    total_height = len(options)
    
    # Calculate scroll position to keep selected item visible
    if selected_idx < 0:
        selected_idx = 0
    elif selected_idx >= total_height:
        selected_idx = total_height - 1
    
    # Calculate start index to keep selected item centered when possible
    start_idx = max(0, min(selected_idx - visible_height // 2, total_height - visible_height))
    end_idx = min(total_height, start_idx + visible_height)
    
    # Draw options
    for idx, option in enumerate(options[start_idx:end_idx], start=start_idx):
        x = w//2 - len(option)//2
        y = 2 + (idx - start_idx)  # Start at y=2 to leave space for title
        if y >= h - 2:  # Leave space for instructions
            break
        try:
            if idx == selected_idx:
                stdscr.attron(curses.A_REVERSE)
                stdscr.addstr(y, x, option)
                stdscr.attroff(curses.A_REVERSE)
            else:
                stdscr.addstr(y, x, option)
        except curses.error:
            continue
    
    # Draw scroll indicators if needed
    if start_idx > 0:
        try:
            stdscr.addstr(1, 2, "↑")
        except curses.error:
            pass
    if end_idx < total_height:
        try:
            stdscr.addstr(h-3, 2, "↓")
        except curses.error:
            pass
    
    # Draw instructions
    try:
        stdscr.addstr(h-2, 2, "Use ↑↓ to navigate, Enter to select, q to quit")
    except curses.error:
        pass
    stdscr.refresh()

def main(stdscr):
    # Initialize color support
    curses.start_color()
    curses.use_default_colors()  # Use terminal's default colors
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)
    
    # Setup the screen
    curses.curs_set(0)  # Hide the cursor
    stdscr.clear()
    
    # Create loading animation
    h, w = stdscr.getmaxyx()
    loading_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    frame_index = 0
    
    # Draw initial loading screen
    title = "Cisco Catalyst Centre Tools"
    loading_msg = "Starting up..."
    
    # Background check for fabric status
    fabric_enabled = False
    check_complete = False
    
    # Capture stdout/stderr to hide warning messages
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')
    
    try:
        # Animation loop
        start_time = time.time()
        while not check_complete:
            stdscr.clear()
            
            # Draw title
            try:
                stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
                stdscr.addstr(h//2 - 3, (w - len(title))//2, title)
                stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
            except curses.error:
                pass
                
            # Draw Cisco logo
            logo = [
                "     ██████╗██╗███████╗ ██████╗ ██████╗     ",
                "    ██╔════╝██║██╔════╝██╔════╝██╔═══██╗    ",
                "    ██║     ██║███████╗██║     ██║   ██║    ",
                "    ██║     ██║╚════██║██║     ██║   ██║    ",
                "    ╚██████╗██║███████║╚██████╗██████╔╝     ",
                "     ╚═════╝╚═╝╚══════╝ ╚═════╝╚═════╝      "
            ]
            
            try:
                for i, line in enumerate(logo):
                    stdscr.attron(curses.color_pair(4))
                    stdscr.addstr(h//2 - 10 + i, (w - len(line))//2, line)
                    stdscr.attroff(curses.color_pair(4))
            except curses.error:
                pass
                
            # Draw spinner animation
            try:
                spinner = loading_frames[frame_index % len(loading_frames)]
                stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
                stdscr.addstr(h//2, (w - len(loading_msg) - 4)//2, f"{spinner} {loading_msg}")
                stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
            except curses.error:
                pass
                
            # Draw progress bar
            progress_width = 40
            elapsed_time = time.time() - start_time
            # Progress linearly from 0-99% based on time elapsed (0-2 seconds)
            progress = min(int((elapsed_time / 2.0) * 100), 99)  # Scale to reach ~99% at 2 seconds
            filled_width = int(progress_width * progress / 100)
            
            try:
                progress_bar = f"[{'■' * filled_width}{' ' * (progress_width - filled_width)}]"
                stdscr.addstr(h//2 + 2, (w - progress_width - 2)//2, progress_bar)
                progress_text = f"{progress}%"
                stdscr.addstr(h//2 + 3, (w - len(progress_text))//2, progress_text)
            except curses.error:
                pass
                
            # Update frame and refresh
            frame_index += 1
            stdscr.refresh()
            curses.napms(100)  # Update every 100ms
            
            # Check if we need to perform the actual fabric check
            if not check_complete and elapsed_time > 2.0:  # After 2 seconds of animation
                try:
                    # Actually check the fabric status (this might take time)
                    fabric_enabled = check_fabric_enabled()
                except Exception:
                    # If any error occurs during check, just assume it's disabled
                    fabric_enabled = False
                
                check_complete = True
                
                # Show completed animation for a moment
                stdscr.clear()
                try:
                    # Draw title
                    stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
                    stdscr.addstr(h//2 - 3, (w - len(title))//2, title)
                    stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
                    
                    # Draw logo
                    for i, line in enumerate(logo):
                        stdscr.attron(curses.color_pair(4))
                        stdscr.addstr(h//2 - 10 + i, (w - len(line))//2, line)
                        stdscr.attroff(curses.color_pair(4))
                    
                    # Draw complete message
                    complete_msg = "Initialisation complete!"
                    stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
                    stdscr.addstr(h//2, (w - len(complete_msg))//2, complete_msg)
                    stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
                    
                    # Draw complete progress bar
                    progress_bar = f"[{'■' * progress_width}]"
                    stdscr.addstr(h//2 + 2, (w - progress_width - 2)//2, progress_bar)
                    progress_text = "100%"
                    stdscr.addstr(h//2 + 3, (w - len(progress_text))//2, progress_text)
                    
                    stdscr.refresh()
                    curses.napms(1000)  # Show completion for 1 second
                except curses.error:
                    pass
    finally:
        # Restore stdout/stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    
    # Menu options
    options = [
        "List Network Devices",
        "List SDA Segments",
        "Edit Configuration",
        "Exit"
    ]
    
    current_idx = 0
    draw_menu(stdscr, current_idx, options, fabric_enabled)
    
    while True:
        key = stdscr.getch()
        
        if key == curses.KEY_UP:
            if current_idx > 0:
                current_idx -= 1
                draw_menu(stdscr, current_idx, options, fabric_enabled)
        elif key == curses.KEY_DOWN:
            if current_idx < len(options) - 1:
                current_idx += 1
                draw_menu(stdscr, current_idx, options, fabric_enabled)
        elif key == ord('\n'):  # Enter key
            if current_idx == 0:
                run_script("devices.py")
            elif current_idx == 1:
                run_script("segment.py")
            elif current_idx == 2:
                # Before editing config, save old config state
                old_config = load_config()
                
                # Show editing interface
                edit_config(stdscr)
                
                # Check if config was changed
                new_config = load_config()
                if (old_config.get('server') != new_config.get('server') or 
                    old_config.get('auth') != new_config.get('auth')):
                    
                    # Config changed, show loading screen again
                    stdscr.clear()
                    loading_msg = "Reconnecting..."
                    check_complete = False
                    frame_index = 0
                    start_time = time.time()
                    
                    # Capture stdout/stderr to hide warning messages
                    old_stdout = sys.stdout
                    old_stderr = sys.stderr
                    sys.stdout = open(os.devnull, 'w')
                    sys.stderr = open(os.devnull, 'w')
                    
                    try:
                        # Re-run the animation loop for reconnection
                        while not check_complete:
                            stdscr.clear()
                            
                            # Draw title and spinner
                            try:
                                stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
                                stdscr.addstr(h//2 - 3, (w - len(title))//2, title)
                                stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
                                
                                spinner = loading_frames[frame_index % len(loading_frames)]
                                stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
                                stdscr.addstr(h//2, (w - len(loading_msg) - 4)//2, f"{spinner} {loading_msg}")
                                stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
                                
                                # Shorter animation for reconnecting
                                elapsed_time = time.time() - start_time
                                # Scale to reach ~99% at 1 second
                                progress = min(int((elapsed_time / 1.0) * 100), 99)
                                filled_width = int(progress_width * progress / 100)
                                progress_bar = f"[{'■' * filled_width}{' ' * (progress_width - filled_width)}]"
                                stdscr.addstr(h//2 + 2, (w - progress_width - 2)//2, progress_bar)
                                
                                # Add progress text
                                progress_text = f"{progress}%"
                                stdscr.addstr(h//2 + 3, (w - len(progress_text))//2, progress_text)
                            except curses.error:
                                pass
                                
                            # Update frame and refresh
                            frame_index += 1
                            stdscr.refresh()
                            curses.napms(100)
                            
                            elapsed_time = time.time() - start_time
                            if elapsed_time > 1.0:  # Only 1 second for reconnection
                                try:
                                    fabric_enabled = check_fabric_enabled()
                                except Exception:
                                    # If any error occurs during check, just assume it's disabled
                                    fabric_enabled = False
                                check_complete = True
                                
                                # Show completion briefly
                                stdscr.clear()
                                try:
                                    # Draw complete message
                                    complete_msg = "Reconnection complete!"
                                    stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
                                    stdscr.addstr(h//2, (w - len(complete_msg))//2, complete_msg)
                                    stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
                                    
                                    # Draw complete progress bar
                                    progress_bar = f"[{'■' * progress_width}]"
                                    stdscr.addstr(h//2 + 2, (w - progress_width - 2)//2, progress_bar)
                                    progress_text = "100%"
                                    stdscr.addstr(h//2 + 3, (w - len(progress_text))//2, progress_text)
                                    
                                    stdscr.refresh()
                                    curses.napms(800)  # Show briefly
                                except curses.error:
                                    pass
                    finally:
                        # Restore stdout/stderr
                        sys.stdout = old_stdout
                        sys.stderr = old_stderr
            elif current_idx == 3:
                break
            draw_menu(stdscr, current_idx, options, fabric_enabled)  # Redraw menu after script execution
        elif key == ord('q'):
            break

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass 