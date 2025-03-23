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
    # Save the cursor state
    try:
        old_cursor = curses.curs_set(1)
    except:
        old_cursor = 0
    
    # Turn on echo for text input
    curses.echo()
    
    # Get window dimensions
    h, w = window.getmaxyx()
    
    # Create the entire input field including prompt
    field_width = min(max_length + len(prompt) + 5, w - x - 2)
    input_y = y
    input_x = x
    
    # Display prompt
    window.attron(get_color(ColorPair.HIGHLIGHT))
    window.addstr(input_y, input_x, prompt)
    window.attroff(get_color(ColorPair.HIGHLIGHT))
    
    # Calculate position for input text
    text_x = input_x + len(prompt)
    
    # Start with initial value
    input_value = initial_value if initial_value is not None else ""
    
    # Clear input area
    window.addstr(input_y, text_x, " " * (field_width - len(prompt)))
    
    # Display initial value
    window.addstr(input_y, text_x, input_value)
    
    # Move cursor to end of initial value
    window.move(input_y, text_x + len(input_value))
    window.refresh()
    
    # Get user input
    try:
        new_value = window.getstr(input_y, text_x, max_length).decode('utf-8')
        
        # If empty and we had an initial value, use initial value
        if not new_value.strip() and initial_value:
            result = initial_value
        else:
            result = new_value
    except:
        # On exception, keep initial value
        result = initial_value
    
    # Reset cursor visibility and echo
    curses.noecho()
    try:
        curses.curs_set(old_cursor)
    except:
        pass
    
    return result

def show_dropdown_menu(window, options, y, x, max_height=10):
    """Display a dropdown menu with options and return the selected index."""
    # Save original cursor state
    try:
        curses.curs_set(0)
    except:
        pass
    
    # Get window dimensions
    h, w = window.getmaxyx()
    
    # Convert all options to strings to prevent len() errors
    string_options = [str(option) for option in options]
    
    # Find the longest option to determine dropdown width
    longest_option = max(string_options, key=len) if string_options else ""
    dropdown_width = min(len(longest_option) + 4, w - x - 2)  # Add padding, respect window width
    
    # Calculate visible options based on max_height and window height
    visible_options = min(max_height, len(string_options), h - y - 2)
    
    # Initialize selection
    current_idx = 0
    first_visible_idx = 0
    
    # Create dropdown panel
    dropdown_box = window.derwin(visible_options + 2, dropdown_width, y, x)
    
    # Main loop
    while True:
        # Draw dropdown box
        dropdown_box.box()
        
        # Calculate last visible index
        last_visible_idx = first_visible_idx + visible_options
        
        # Display visible options
        for i in range(first_visible_idx, min(last_visible_idx, len(string_options))):
            option_idx = i - first_visible_idx  # Relative position in the visible list
            option_text = string_options[i]
            
            # Truncate if too long
            if len(option_text) > dropdown_width - 4:
                option_text = option_text[:dropdown_width - 7] + "..."
            
            # Highlight if selected
            if i == current_idx:
                attr = curses.A_REVERSE
            else:
                attr = curses.A_NORMAL
            
            # Clear line
            try:
                dropdown_box.addstr(option_idx + 1, 1, " " * (dropdown_width - 2))
                # Draw option
                dropdown_box.addstr(option_idx + 1, 2, option_text, attr)
            except curses.error:
                pass  # Ignore errors if we can't draw
        
        # Show scroll indicators if needed - using ASCII instead of Unicode
        try:
            if first_visible_idx > 0:
                dropdown_box.addstr(0, dropdown_width // 2, "^")
            if last_visible_idx < len(string_options):
                dropdown_box.addstr(visible_options + 1, dropdown_width // 2, "v")
        except curses.error:
            pass  # Ignore errors for indicators
        
        # Refresh display
        dropdown_box.refresh()
        
        # Get input
        key = window.getch()
        
        if key == curses.KEY_UP:
            # Move selection up
            if current_idx > 0:
                current_idx -= 1
                # Scroll if needed
                if current_idx < first_visible_idx:
                    first_visible_idx = current_idx
        elif key == curses.KEY_DOWN:
            # Move selection down
            if current_idx < len(string_options) - 1:
                current_idx += 1
                # Scroll if needed
                if current_idx >= last_visible_idx:
                    first_visible_idx = current_idx - visible_options + 1
        elif key == curses.KEY_PPAGE:  # Page Up
            # Move page up
            current_idx = max(0, current_idx - visible_options)
            first_visible_idx = max(0, first_visible_idx - visible_options)
        elif key == curses.KEY_NPAGE:  # Page Down
            # Move page down
            current_idx = min(len(string_options) - 1, current_idx + visible_options)
            first_visible_idx = min(len(string_options) - visible_options, first_visible_idx + visible_options)
            if first_visible_idx < 0:
                first_visible_idx = 0
        elif key == 10 or key == 13:  # Enter key
            # Return selected index
            return current_idx
        elif key == 27 or key == ord('q'):  # Escape or q
            # Cancel selection
            return None
    
    # Clean up
    del dropdown_box

def show_form(window, title: str, fields: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Show a form with multiple input fields.
    
    Args:
        window: The curses window
        title: Form title
        fields: List of field definitions:
               [{
                 'name': 'field_name',      # Internal field name
                 'label': 'Display Label',  # User-facing label
                 'type': 'text',            # Field type (text, dropdown, number)
                 'required': True,          # Whether field is required
                 'options': [...],          # List of options for dropdown type
                 'initial': 'value'         # Initial value
               }]
               
    Returns:
        Dictionary of field values
    """
    # Save the current window state
    h, w = window.getmaxyx()
    
    # Apply the navy blue background to match the main application
    window.bkgd(' ', get_color(ColorPair.NORMAL))
    window.clear()
    
    # Create form
    form_h = min(h - 4, len(fields) * 3 + 6)  # Height based on number of fields
    form_w = min(w - 4, 70)  # Width constrained to available space or 70 chars
    
    # Center the form
    start_y = (h - form_h) // 2
    start_x = (w - form_w) // 2
    
    # Create a form window
    form_win = curses.newwin(form_h, form_w, start_y, start_x)
    form_win.bkgd(' ', get_color(ColorPair.NORMAL))
    form_win.keypad(True)
    
    # Draw form border
    form_win.box()
    
    # Draw title
    form_win.attron(get_color(ColorPair.HEADER, bold=True))
    for x in range(1, form_w-1):
        form_win.addstr(0, x, " ")
    form_win.addstr(0, (form_w - len(title)) // 2, title)
    form_win.attroff(get_color(ColorPair.HEADER, bold=True))
    
    # Initialize form data with any initial values
    form_values = {}
    for field in fields:
        field_name = field['name']
        initial = field.get('initial', field.get('default', ''))
        form_values[field_name] = initial
    
    # Initialize form state
    current_field = 0
    
    # Save a copy of the window for restoring later
    window_copy = window.getmaxyx()
    
    while True:
        form_win.clear()
        form_win.box()  # Redraw the border
        
        # Draw title
        form_win.attron(get_color(ColorPair.HEADER, bold=True))
        for x in range(1, form_w-1):
            form_win.addstr(0, x, " ")
        form_win.addstr(0, (form_w - len(title)) // 2, title)
        form_win.attroff(get_color(ColorPair.HEADER, bold=True))
        
        # Draw form fields
        for i, field in enumerate(fields):
            y_pos = i * 2 + 2  # Space fields out vertically
            
            # Field label
            label = field["label"]
            if field.get("required", False):
                label += " *"
            
            # Highlight current field
            if i == current_field:
                form_win.attron(get_color(ColorPair.HIGHLIGHT))
                form_win.addstr(y_pos, 2, label)
                form_win.attroff(get_color(ColorPair.HIGHLIGHT))
            else:
                form_win.addstr(y_pos, 2, label)
            
            # Draw field value
            value = form_values.get(field["name"], "")
            if field["type"] == "dropdown" and isinstance(value, int) and value >= 0:
                # For dropdown, show the selected option text
                if "options" in field and value < len(field["options"]):
                    display_value = field["options"][value]
                else:
                    display_value = "Invalid selection"
            else:
                display_value = str(value) if value is not None else ""
                
            form_win.addstr(y_pos + 1, 4, display_value)
        
        # Draw navigation help
        help_text = "↑↓: Navigate fields | Enter: Edit field | Esc: Cancel | F10: Save form"
        try:
            form_win.addstr(form_h-2, (form_w - len(help_text)) // 2, help_text)
        except curses.error:
            pass
        
        form_win.refresh()
        
        # Handle input
        key = form_win.getch()
        
        if key == curses.KEY_UP:
            if current_field > 0:
                current_field -= 1
        elif key == curses.KEY_DOWN:
            if current_field < len(fields) - 1:
                current_field += 1
        elif key == ord('\n'):  # Enter - edit current field
            field = fields[current_field]
            current_value = form_values.get(field["name"], "")
            
            if field["type"] == "text":
                # Handle text input
                new_value = get_text_input(
                    form_win, 
                    field["label"] + ": ", 
                    current_field * 2 + 2, 
                    2,
                    max_length=50,
                    initial_value=str(current_value) if current_value is not None else ""
                )
                form_values[field["name"]] = new_value
                
            elif field["type"] == "dropdown":
                # Handle dropdown selection
                if "options" in field and field["options"]:
                    selected = show_dropdown_menu(
                        form_win,
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
                    new_value = get_text_input(
                        form_win, 
                        field["label"] + ": ", 
                        current_field * 2 + 2, 
                        2,
                        max_length=20,
                        initial_value=str(current_value) if current_value is not None else ""
                    )
                    
                    # If the user entered something, try to convert to number
                    if new_value:
                        try:
                            if "." in new_value:
                                form_values[field["name"]] = float(new_value)
                            else:
                                form_values[field["name"]] = int(new_value)
                        except ValueError:
                            # If conversion fails, store as string
                            form_values[field["name"]] = new_value
                    else:
                        # Empty input, store as empty string
                        form_values[field["name"]] = ""
                except Exception as e:
                    # On exception, keep the current value
                    pass
                    
        elif key == 27:  # Escape - cancel form
            return None
            
        elif key == curses.KEY_F10:  # F10 - save form
            # Validate required fields
            valid = True
            for field in fields:
                if field.get("required", False):
                    value = form_values.get(field["name"], "")
                    if (value is None) or (value == "" and value != 0):  # Allow 0 as a valid value
                        valid = False
                        current_field = fields.index(field)
                        
                        # Show error message
                        error_msg = f"Required field: {field['label']}"
                        form_win.attron(get_color(ColorPair.ERROR))
                        try:
                            form_win.addstr(form_h-3, (form_w - len(error_msg)) // 2, error_msg)
                        except curses.error:
                            pass
                        form_win.attroff(get_color(ColorPair.ERROR))
                        form_win.refresh()
                        curses.napms(1500)  # Show error for 1.5 seconds
                        break
                        
            if valid:
                return form_values
    
    return None 