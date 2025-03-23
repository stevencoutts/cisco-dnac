#!/usr/bin/env python3
"""
Color schemes and styling for the CLI interface.
Author: Steven Coutts
"""
import curses
from enum import Enum

class ColorPair(Enum):
    """Color pair identifiers for consistent use across the UI."""
    HEADER = 1
    SUCCESS = 2
    ERROR = 3
    HIGHLIGHT = 4
    LOGO = 5
    MENU_SELECTED = 6
    PROGRESS = 7
    DISABLED = 8

def initialize_colors() -> None:
    """Initialize color pairs for use in the application."""
    # Start color support
    curses.start_color()
    curses.use_default_colors()  # Use terminal's default colors
    
    # Define color pairs
    curses.init_pair(ColorPair.HEADER.value, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(ColorPair.SUCCESS.value, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(ColorPair.ERROR.value, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(ColorPair.HIGHLIGHT.value, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(ColorPair.LOGO.value, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(ColorPair.MENU_SELECTED.value, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(ColorPair.PROGRESS.value, curses.COLOR_BLUE, curses.COLOR_BLACK)
    curses.init_pair(ColorPair.DISABLED.value, curses.COLOR_RED, curses.COLOR_BLACK)

def get_color(color: ColorPair, bold: bool = False) -> int:
    """Get the attribute for a specific color, optionally with bold."""
    attr = curses.color_pair(color.value)
    if bold:
        attr |= curses.A_BOLD
    return attr 