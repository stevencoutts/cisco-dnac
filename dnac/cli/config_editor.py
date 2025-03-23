#!/usr/bin/env python3
"""
Configuration editing interface for the CLI.
Author: Steven Coutts
"""
import curses
from typing import Dict, Any, List, Tuple

from dnac.core.config import load_config, save_config
from dnac.ui.colors import ColorPair, get_color

def edit_config(window) -> Dict[str, Any]:
    """
    Interactive configuration editor.
    
    Args:
        window: The curses window to draw on
        
    Returns:
        The updated configuration dictionary
    """
    config = load_config()
    
    # Setup variables
    current_section = 0
    current_field = 0
    editing = False
    edit_buffer = ""
    
    # Define sections and fields
    sections = ['server', 'auth']
    fields = {
        'server': ['host', 'port', 'verify_ssl', 'timeout'],
        'auth': ['username', 'password']
    }
    
    # Flag to track if we need to redraw
    redraw = True
    
    while True:
        if redraw:
            window.clear()
            h, w = window.getmaxyx()
            
            # Draw title
            title = "DNAC Configuration Editor"
            try:
                window.attron(get_color(ColorPair.HEADER, bold=True))
                window.addstr(0, (w - len(title)) // 2, title)
                window.attroff(get_color(ColorPair.HEADER, bold=True))
            except curses.error:
                pass
            
            # Draw sections and fields
            y = 2
            for section_idx, section in enumerate(sections):
                # Draw section header
                try:
                    window.attron(curses.A_BOLD)
                    window.addstr(y, 2, f"{section.upper()} Settings:")
                    window.attroff(curses.A_BOLD)
                except curses.error:
                    pass
                y += 1
                
                # Draw fields
                for field_idx, field in enumerate(fields[section]):
                    value = str(config[section][field])
                    
                    # Show selected item differently
                    if section_idx == current_section and field_idx == current_field:
                        prefix = "> "
                        color = ColorPair.HIGHLIGHT
                    else:
                        prefix = "  "
                        color = None
                    
                    # Mask password
                    display_value = "*" * len(value) if field == "password" else value
                    
                    # Line to display
                    line = f"{prefix}{field}: {display_value}"
                    
                    try:
                        if color:
                            window.attron(get_color(color, bold=True))
                            window.addstr(y, 4, line)
                            window.attroff(get_color(color, bold=True))
                        else:
                            window.addstr(y, 4, line)
                    except curses.error:
                        pass
                    y += 1
                y += 1
            
            # Draw instructions
            instructions = [
                "Use ↑↓ to navigate, Enter to edit, 's' to save, 'q' to quit",
                f"Current value: {edit_buffer}" if editing else ""
            ]
            for i, instr in enumerate(instructions):
                try:
                    window.addstr(h-2+i, 2, instr)
                except curses.error:
                    pass
            
            window.refresh()
            redraw = False
        
        # Handle input
        key = window.getch()
        
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
                redraw = True
            elif key == 27:  # ESC
                editing = False
                edit_buffer = ""
                redraw = True
            elif key == curses.KEY_BACKSPACE or key == 127:
                edit_buffer = edit_buffer[:-1]
                redraw = True
            else:
                if 32 <= key <= 126:  # Printable ASCII only
                    edit_buffer += chr(key)
                    redraw = True
        else:
            if key == ord('q'):
                break
            elif key == ord('s'):
                save_config(config)
                # Show save confirmation
                try:
                    window.attron(get_color(ColorPair.SUCCESS, bold=True))
                    msg = "Configuration saved! Press any key to continue..."
                    window.addstr(h-1, 2, msg)
                    window.attroff(get_color(ColorPair.SUCCESS, bold=True))
                    window.refresh()
                except curses.error:
                    pass
                window.getch()
                redraw = True
            elif key == ord('\n'):
                editing = True
                section = sections[current_section]
                field = fields[section][current_field]
                edit_buffer = str(config[section][field])
                redraw = True
            elif key == curses.KEY_UP:
                if current_field > 0:
                    current_field -= 1
                elif current_section > 0:
                    current_section -= 1
                    current_field = len(fields[sections[current_section]]) - 1
                redraw = True
            elif key == curses.KEY_DOWN:
                if current_field < len(fields[sections[current_section]]) - 1:
                    current_field += 1
                elif current_section < len(sections) - 1:
                    current_section += 1
                    current_field = 0
                redraw = True
    
    return config 