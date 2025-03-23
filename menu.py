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
        
        if key == curses.KEY_UP:
            if current_idx > 0:
                current_idx -= 1
                draw_menu(stdscr, current_idx, options)
        elif key == curses.KEY_DOWN:
            if current_idx < len(options) - 1:
                current_idx += 1
                draw_menu(stdscr, current_idx, options)
        elif key == ord('\n'):  # Enter key
            if current_idx == 0:
                run_script("devices.py")
            elif current_idx == 1:
                run_script("segment.py")
            elif current_idx == 2:
                edit_config(stdscr)
            elif current_idx == 3:
                break
            draw_menu(stdscr, current_idx, options)  # Redraw menu after script execution
        elif key == ord('q'):
            break

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass 