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

def draw_status_indicator(window, enabled: bool, text_enabled: str = "● ENABLED", 
                         text_disabled: str = "○ DISABLED", y: int = 0, x: Optional[int] = None) -> None:
    """Draw a status indicator showing enabled/disabled state."""
    h, w = window.getmaxyx()
    
    status_text = text_enabled if enabled else text_disabled
    color = ColorPair.SUCCESS if enabled else ColorPair.DISABLED
    
    # Set default x position if not specified
    if x is None:
        x = w - len(status_text) - 2
    
    # Ensure we don't exceed window boundaries
    if y < 0 or y >= h or x < 0:
        return
    
    try:
        window.attron(get_color(color, bold=True))
        window.addstr(y, x, status_text)
        window.attroff(get_color(color, bold=True))
    except curses.error:
        pass 