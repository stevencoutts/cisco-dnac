#!/usr/bin/env python3
import curses
import sys
import subprocess
import os
import yaml
from typing import List, Tuple, Dict, Any

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
        output_win.box()
        
        # Calculate safe boundaries
        max_y = curses.LINES - 3  # Leave space for border and instructions
        max_x = curses.COLS - 4   # Leave space for borders
        
        # Split output into lines and display
        lines = result.stdout.split('\n')
        scroll_pos = 0
        max_scroll = max(0, len(lines) - (max_y - 2))  # Account for header and instructions
        
        while True:
            output_win.clear()
            output_win.box()
            
            # Add header
            try:
                output_win.addstr(1, 2, f"Output from {script_name}")
            except curses.error:
                pass
            
            # Display visible lines
            for i, line in enumerate(lines[scroll_pos:scroll_pos + (max_y - 2)], 2):
                if i >= max_y:
                    break
                try:
                    # Truncate line to fit window width
                    truncated_line = line[:max_x]
                    output_win.addstr(i, 2, truncated_line)
                except curses.error:
                    continue
            
            # Add instructions at the bottom
            try:
                output_win.addstr(max_y, 2, "Use ↑↓ to scroll, 'q' to return to menu")
            except curses.error:
                pass
            
            output_win.refresh()
            
            # Handle user input
            key = output_win.getch()
            if key == ord('q'):
                break
            elif key == curses.KEY_UP and scroll_pos > 0:
                scroll_pos = max(0, scroll_pos - 1)
            elif key == curses.KEY_DOWN and scroll_pos < max_scroll:
                scroll_pos = min(max_scroll, scroll_pos + 1)
                
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

def draw_menu(stdscr, selected_idx: int, options: List[str]) -> None:
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
    
    # Draw options
    for idx, option in enumerate(options):
        x = w//2 - len(option)//2
        y = h//2 - len(options)//2 + idx
        if y >= h - 1:  # Skip if we're at the bottom of the screen
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
    
    # Draw instructions
    try:
        stdscr.addstr(h-2, 2, "Use ↑↓ to navigate, Enter to select, q to quit")
    except curses.error:
        pass
    stdscr.refresh()

def main(stdscr):
    # Initialize color support
    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
    
    # Menu options
    options = [
        "List Network Devices",
        "List SDA Segments",
        "Edit Configuration",
        "Exit"
    ]
    
    current_idx = 0
    draw_menu(stdscr, current_idx, options)
    
    while True:
        key = stdscr.getch()
        
        if key == curses.KEY_UP and current_idx > 0:
            current_idx -= 1
        elif key == curses.KEY_DOWN and current_idx < len(options) - 1:
            current_idx += 1
        elif key == ord('\n'):  # Enter key
            if current_idx == 0:
                run_script("devices.py")
            elif current_idx == 1:
                run_script("segment.py")
            elif current_idx == 2:
                edit_config(stdscr)
            elif current_idx == 3:
                break
        elif key == ord('q'):
            break
            
        draw_menu(stdscr, current_idx, options)

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass 