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
    NORMAL = 6
    SELECTED = 7
    PROGRESS = 8
    DISABLED = 9
    WARNING = 10

def initialize_colors() -> None:
    """Initialize color pairs for use in the application."""
    # Start color support
    curses.start_color()
    curses.use_default_colors()  # Use terminal's default colors
    
    # Define base colors - using extended color pairs where available
    # Modern color scheme using more pleasing colors
    
    # Base colors
    BLACK = curses.COLOR_BLACK
    WHITE = curses.COLOR_WHITE
    
    # Modern blue shade for primary elements
    ROYAL_BLUE = curses.COLOR_BLUE
    
    # Darker blue for headers and background
    NAVY_BLUE = 18 if curses.COLORS >= 256 else curses.COLOR_BLUE
    DARK_NAVY = 17 if curses.COLORS >= 256 else curses.COLOR_BLACK
    
    # Success/positive action color
    TEAL = 30 if curses.COLORS >= 256 else curses.COLOR_GREEN
    
    # Warning/caution color
    AMBER = 208 if curses.COLORS >= 256 else curses.COLOR_YELLOW
    
    # Error/negative action color
    CRIMSON = 160 if curses.COLORS >= 256 else curses.COLOR_RED
    
    # Highlight/accent color
    PURPLE = 93 if curses.COLORS >= 256 else curses.COLOR_MAGENTA
    
    # Subtle colors for inactive/background elements
    DARK_GRAY = 236 if curses.COLORS >= 256 else curses.COLOR_BLACK
    LIGHT_GRAY = 250 if curses.COLORS >= 256 else curses.COLOR_WHITE
    
    # Use DARK_NAVY as the default background color for all pairs
    # Define color pairs
    curses.init_pair(ColorPair.HEADER.value, WHITE, NAVY_BLUE)
    curses.init_pair(ColorPair.SUCCESS.value, TEAL, DARK_NAVY)
    curses.init_pair(ColorPair.ERROR.value, CRIMSON, DARK_NAVY)
    curses.init_pair(ColorPair.HIGHLIGHT.value, PURPLE, DARK_NAVY)
    curses.init_pair(ColorPair.LOGO.value, ROYAL_BLUE, DARK_NAVY)
    curses.init_pair(ColorPair.NORMAL.value, LIGHT_GRAY, DARK_NAVY)
    curses.init_pair(ColorPair.SELECTED.value, WHITE, ROYAL_BLUE)
    curses.init_pair(ColorPair.PROGRESS.value, TEAL, DARK_NAVY)
    curses.init_pair(ColorPair.DISABLED.value, CRIMSON, DARK_NAVY)
    curses.init_pair(ColorPair.WARNING.value, AMBER, DARK_NAVY)

def get_color(color: ColorPair, bold: bool = False) -> int:
    """Get the attribute for a specific color, optionally with bold."""
    attr = curses.color_pair(color.value)
    if bold:
        attr |= curses.A_BOLD
    return attr 