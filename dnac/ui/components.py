#!/usr/bin/env python3
"""
Reusable UI components for the CLI interface.
Author: Steven Coutts
"""
import curses
from typing import List, Tuple, Optional
from dnac.ui.colors import ColorPair, get_color

def draw_title(window, title: str, y: int = 0) -> None:
    """Draw a centered title with the header color scheme."""
    h, w = window.getmaxyx()
    try:
        window.attron(get_color(ColorPair.HEADER, bold=True))
        window.addstr(y, (w - len(title)) // 2, title)
        window.attroff(get_color(ColorPair.HEADER, bold=True))
    except curses.error:
        pass

def draw_cisco_logo(window, y_offset: int = 2) -> None:
    """Draw the Cisco ASCII logo."""
    h, w = window.getmaxyx()
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
            window.attron(get_color(ColorPair.LOGO))
            window.addstr(y_offset + i, (w - len(line)) // 2, line)
            window.attroff(get_color(ColorPair.LOGO))
    except curses.error:
        pass

def draw_progress_bar(window, progress: int, width: int = 40, y: int = 0, x: Optional[int] = None, 
                      show_percentage: bool = True) -> None:
    """Draw a progress bar with optional percentage text."""
    h, w = window.getmaxyx()
    
    # If x is not specified, center the progress bar
    if x is None:
        x = (w - width) // 2
    
    # Calculate filled width
    filled_width = int(width * min(100, max(0, progress)) / 100)
    
    try:
        # Draw the progress bar
        bar = f"[{'■' * filled_width}{' ' * (width - filled_width)}]"
        window.addstr(y, x, bar)
        
        # Draw the percentage text
        if show_percentage:
            progress_text = f"{progress}%"
            window.addstr(y + 1, (w - len(progress_text)) // 2, progress_text)
    except curses.error:
        pass

def draw_spinner(window, frame_index: int, text: str, y: int, frames: Optional[List[str]] = None) -> None:
    """Draw an animated spinner with text."""
    h, w = window.getmaxyx()
    
    if frames is None:
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    
    try:
        spinner = frames[frame_index % len(frames)]
        window.attron(get_color(ColorPair.SUCCESS, bold=True))
        window.addstr(y, (w - len(text) - 2) // 2, f"{spinner} {text}")
        window.attroff(get_color(ColorPair.SUCCESS, bold=True))
    except curses.error:
        pass

def draw_menu_item(window, label: str, y: int, is_selected: bool, x: int = None) -> None:
    """
    Draw a menu item with the appropriate styling.
    
    Args:
        window: The curses window to draw on
        label: The menu item label
        y: The y position to draw at
        is_selected: Whether the item is currently selected
        x: Optional x position (centered if None)
    """
    h, w = window.getmaxyx()
    
    if x is None:
        # Center the item unless it's a separator (empty label)
        if label == "":
            x = 0
        else:
            x = (w - len(label)) // 2
    
    # Don't draw anything for separator items (empty labels)
    if label == "":
        return
        
    # Select appropriate color
    if is_selected:
        # Use selected style
        window.attron(get_color(ColorPair.SELECTED, bold=True))
        window.addstr(y, x, label)
        window.attroff(get_color(ColorPair.SELECTED, bold=True))
    else:
        # Use normal style
        window.attron(get_color(ColorPair.NORMAL))
        window.addstr(y, x, label)
        window.attroff(get_color(ColorPair.NORMAL))

def draw_status_indicator(window, is_enabled: bool, text_enabled: str = "ENABLED", text_disabled: str = "DISABLED", y: int = None, x: int = 0) -> None:
    """
    Draw a status indicator with appropriate styling.
    
    Args:
        window: The curses window to draw on
        is_enabled: Whether the status is enabled
        text_enabled: Text to display when enabled
        text_disabled: Text to display when disabled
        y: The y position to draw at (centered if None)
        x: The x position to draw at
    """
    h, w = window.getmaxyx()
    
    # Use bottom if y is not specified
    if y is None:
        y = h - 1
    
    # Select appropriate color
    color = ColorPair.SUCCESS if is_enabled else ColorPair.ERROR
    text = text_enabled if is_enabled else text_disabled
    
    # Draw the indicator
    window.attron(get_color(color))
    window.addstr(y, x, text)
    window.attroff(get_color(color))

def draw_standard_header_footer(window, title: str = "Cisco Catalyst Centre", subtitle: str = None,
                              footer_text: str = None, fabric_enabled: bool = None, connected: bool = True) -> int:
    """
    Draw a standard header and footer for all screens to maintain consistent appearance.
    
    Args:
        window: The curses window to draw on
        title: The title to display in the header
        subtitle: Optional subtitle to display below the header
        footer_text: Optional footer text (defaults to navigation help)
        fabric_enabled: Whether fabric is enabled (if None, status indicator is not shown)
        connected: Whether connected to Catalyst Centre
        
    Returns:
        int: The y-coordinate where content should start
    """
    # Get window dimensions
    h, w = window.getmaxyx()
    
    # Draw title bar with background
    window.attron(get_color(ColorPair.HEADER, bold=True))
    for x in range(w):
        window.addstr(0, x, " ")
    window.addstr(0, (w - len(title)) // 2, title)
    window.attroff(get_color(ColorPair.HEADER, bold=True))
    
    # Start position for content
    content_start_y = 1
    
    # Draw subtitle if provided
    if subtitle:
        # Add a subtle separator line
        window.attron(get_color(ColorPair.NORMAL))
        for x in range(w):
            window.addstr(1, x, "─")
        window.attroff(get_color(ColorPair.NORMAL))
        
        # Display subtitle with styling
        window.attron(get_color(ColorPair.HIGHLIGHT))
        window.addstr(2, 2, subtitle)
        window.attroff(get_color(ColorPair.HIGHLIGHT))
        
        # Content starts below subtitle
        content_start_y = 4
    
    # Draw footer
    if footer_text is None:
        footer_text = "↑↓: Navigate  Enter: Select  Esc/q: Quit"
    
    window.attron(get_color(ColorPair.HIGHLIGHT))
    window.addstr(h-1, (w - len(footer_text)) // 2, footer_text)
    window.attroff(get_color(ColorPair.HIGHLIGHT))
    
    # Draw connection status indicator
    draw_status_indicator(window, connected, 
                        text_enabled="● CONNECTED", 
                        text_disabled="● DISCONNECTED",
                        y=h-2, x=2)
    
    # Draw fabric status indicator if provided
    if fabric_enabled is not None:
        # Position the fabric status to the right of the connection status
        fabric_x = 16  # Adjust this value based on the width of connection status
        draw_status_indicator(window, fabric_enabled, 
                            text_enabled="● FABRIC ENABLED", 
                            text_disabled="● FABRIC DISABLED",
                            y=h-2, x=fabric_x)
    
    # Return where content should start
    return content_start_y 