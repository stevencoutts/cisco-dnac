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

def draw_menu_item(window, text: str, y: int, selected: bool = False) -> None:
    """Draw a menu item, highlighting it if selected."""
    h, w = window.getmaxyx()
    
    try:
        x = (w - len(text)) // 2
        if selected:
            window.attron(get_color(ColorPair.MENU_SELECTED, bold=True))
            window.addstr(y, x, text)
            window.attroff(get_color(ColorPair.MENU_SELECTED, bold=True))
        else:
            window.addstr(y, x, text)
    except curses.error:
        pass

def draw_status_indicator(window, enabled: bool, text_enabled: str = "● ENABLED", 
                         text_disabled: str = "○ DISABLED", y: int = 0) -> None:
    """Draw a status indicator showing enabled/disabled state."""
    h, w = window.getmaxyx()
    
    status_text = text_enabled if enabled else text_disabled
    color = ColorPair.SUCCESS if enabled else ColorPair.DISABLED
    
    try:
        window.attron(get_color(color, bold=True))
        window.addstr(y, w - len(status_text) - 2, status_text)
        window.attroff(get_color(color, bold=True))
    except curses.error:
        pass 