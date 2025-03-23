#!/usr/bin/env python3
"""
Form input components for the CLI interface.
Author: Steven Coutts
"""
import curses
from typing import List, Dict, Any, Optional, Callable, Tuple

from dnac.ui.colors import ColorPair, get_color

def get_text_input(window, prompt: str, y: int, x: int, max_length: int = 30, 
                  initial_value: str = "") -> str:
    """
    Display a text input field and get user input.
    
    Args:
        window: The curses window
        prompt: The prompt text to display
        y: Y position for the prompt
        x: X position for the prompt
        max_length: Maximum length of input
        initial_value: Initial value for the input field
        
    Returns:
        The text entered by the user
    """
    # Enable cursor and echo for text input
    curses.curs_set(1)
    curses.echo()
    
    # Display prompt
    window.addstr(y, x, prompt)
    
    # Create input area
    input_x = x + len(prompt) + 1
    input_y = y
    
    # Display initial value if any
    current_value = initial_value
    window.addstr(input_y, input_x, current_value + " " * (max_length - len(current_value)))
    
    # Move cursor to end of initial value
    window.move(input_y, input_x + len(current_value))
    window.refresh()
    
    # Get user input
    try:
        text = window.getstr(input_y, input_x, max_length)
        value = text.decode('utf-8')
    except:
        value = current_value
    
    # Reset cursor and echo
    curses.noecho()
    curses.curs_set(0)
    
    return value

def show_dropdown_menu(window, title: str, options: List[str], 
                      y: int, x: int, width: int = 40) -> int:
    """
    Show a dropdown menu with options and return the selected index.
    
    Args:
        window: The curses window
        title: Title text for the dropdown
        options: List of option strings
        y: Y position for the dropdown
        x: X position for the dropdown
        width: Width of the dropdown box
        
    Returns:
        Index of the selected option or -1 if cancelled
    """
    # Save current cursor state and hide cursor
    curses.curs_set(0)
    
    if not options:
        return -1
    
    # Create a new window for the dropdown
    height = min(len(options) + 2, 10)  # +2 for border
    dropdown = curses.newwin(height, width, y, x)
    dropdown.keypad(True)
    
    # Calculate if we need scrolling
    max_display = height - 2  # Subtract border
    can_scroll = len(options) > max_display
    
    # Initialize state
    current_idx = 0
    offset = 0
    
    while True:
        # Draw border and title
        dropdown.clear()
        dropdown.box()
        try:
            dropdown.addstr(0, 2, f" {title} ")
        except curses.error:
            pass
        
        # Calculate visible range
        if can_scroll:
            # Keep selected item in view
            if current_idx < offset:
                offset = current_idx
            elif current_idx >= offset + max_display:
                offset = current_idx - max_display + 1
                
            # Draw up/down indicators if scrollable
            if offset > 0:
                dropdown.addstr(1, width-3, "↑")
            if offset + max_display < len(options):
                dropdown.addstr(height-2, width-3, "↓")
        
        # Draw options
        visible_options = options[offset:offset+max_display]
        for i, option in enumerate(visible_options):
            # Truncate option text if needed
            display_text = option
            if len(display_text) > width - 6:
                display_text = display_text[:width-9] + "..."
                
            # Highlight current selection
            y_pos = i + 1
            x_pos = 2
            
            is_selected = i + offset == current_idx
            if is_selected:
                dropdown.attron(get_color(ColorPair.SELECTED))
                dropdown.addstr(y_pos, x_pos, " " + display_text + " " * (width - len(display_text) - 4))
                dropdown.attroff(get_color(ColorPair.SELECTED))
            else:
                dropdown.addstr(y_pos, x_pos, " " + display_text)
        
        dropdown.refresh()
        
        # Handle key presses
        key = dropdown.getch()
        
        if key == curses.KEY_UP:
            if current_idx > 0:
                current_idx -= 1
        elif key == curses.KEY_DOWN:
            if current_idx < len(options) - 1:
                current_idx += 1
        elif key == ord('\n'):  # Enter key
            return current_idx
        elif key in (curses.KEY_BACKSPACE, 27, ord('\b'), 8):  # Backspace, Escape
            return -1
    
    return -1

def show_form(window, title: str, fields: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Show a form with multiple input fields.
    
    Args:
        window: The curses window
        title: Form title
        fields: List of field definitions with:
               - name: Field name
               - label: Display label
               - type: "text", "dropdown", "number" etc.
               - options: List of options for dropdowns
               - required: Whether field is required
               - default: Default value
               
    Returns:
        Dictionary with field values
    """
    h, w = window.getmaxyx()
    
    # Initialize form state
    form_values = {}
    current_field = 0
    
    # Save a copy of the window for restoring later
    window_copy = window.getmaxyx()
    
    # Initialize default values
    for field in fields:
        form_values[field["name"]] = field.get("default", "")
    
    while True:
        window.clear()
        
        # Draw title
        window.attron(get_color(ColorPair.HEADER, bold=True))
        window.addstr(0, (w - len(title)) // 2, title)
        window.attroff(get_color(ColorPair.HEADER, bold=True))
        
        # Draw form fields
        for i, field in enumerate(fields):
            y_pos = i * 2 + 2  # Space fields out vertically
            
            # Field label
            label = field["label"]
            if field.get("required", False):
                label += " *"
            
            # Highlight current field
            if i == current_field:
                window.attron(get_color(ColorPair.HIGHLIGHT))
                window.addstr(y_pos, 2, label)
                window.attroff(get_color(ColorPair.HIGHLIGHT))
            else:
                window.addstr(y_pos, 2, label)
            
            # Draw field value
            value = form_values[field["name"]]
            if field["type"] == "dropdown" and isinstance(value, int) and value >= 0:
                # For dropdown, show the selected option text
                if value < len(field["options"]):
                    display_value = field["options"][value]
                else:
                    display_value = "Invalid selection"
            else:
                display_value = str(value)
                
            window.addstr(y_pos + 1, 4, display_value)
        
        # Draw navigation help
        help_text = "↑↓: Navigate fields | Enter: Edit field | Esc: Cancel | F10: Save form"
        try:
            window.addstr(h-2, (w - len(help_text)) // 2, help_text)
        except curses.error:
            pass
        
        window.refresh()
        
        # Handle input
        key = window.getch()
        
        if key == curses.KEY_UP:
            if current_field > 0:
                current_field -= 1
        elif key == curses.KEY_DOWN:
            if current_field < len(fields) - 1:
                current_field += 1
        elif key == ord('\n'):  # Enter - edit current field
            field = fields[current_field]
            
            if field["type"] == "text":
                # Handle text input
                value = get_text_input(
                    window, 
                    field["label"] + ": ", 
                    current_field * 2 + 2, 
                    2,
                    initial_value=str(form_values[field["name"]])
                )
                form_values[field["name"]] = value
                
            elif field["type"] == "dropdown":
                # Handle dropdown selection
                selected = show_dropdown_menu(
                    window,
                    field["label"],
                    field["options"],
                    current_field * 2 + 3,  # Position below the field
                    4,
                    40
                )
                if selected >= 0:  # -1 means cancelled
                    form_values[field["name"]] = selected
                    
            elif field["type"] == "number":
                # Handle numeric input
                try:
                    value = get_text_input(
                        window, 
                        field["label"] + ": ", 
                        current_field * 2 + 2, 
                        2,
                        initial_value=str(form_values[field["name"]])
                    )
                    # Convert to number if possible
                    try:
                        if "." in value:
                            form_values[field["name"]] = float(value)
                        else:
                            form_values[field["name"]] = int(value)
                    except ValueError:
                        form_values[field["name"]] = value
                except:
                    pass
                    
        elif key == 27:  # Escape - cancel form
            return None
            
        elif key == curses.KEY_F10:  # F10 - save form
            # Validate required fields
            valid = True
            for field in fields:
                if field.get("required", False):
                    value = form_values[field["name"]]
                    if not value and value != 0:  # Allow 0 as a valid value
                        valid = False
                        current_field = fields.index(field)
                        break
                        
            if valid:
                return form_values
    
    return None 