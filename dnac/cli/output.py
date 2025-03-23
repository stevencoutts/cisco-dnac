#!/usr/bin/env python3
"""
Output display and scrolling functionality for the CLI interface.
Author: Steven Coutts
"""
import curses
import time
from typing import List, Optional

from dnac.ui.colors import ColorPair, get_color

def show_scrollable_output(window, content: str, title: str = "Output") -> None:
    """
    Display scrollable text output with navigation controls.
    
    Args:
        window: The curses window to draw on
        content: The text content to display
        title: Title to show at the top of the output window
    """
    # Split content into lines and initialize variables
    lines = content.split('\n')
    scroll_pos = 0
    
    # Enable keypad for special keys like Page Up/Down
    window.keypad(True)
    
    # Calculate safe boundaries
    h, w = window.getmaxyx()
    max_y = h - 4  # Leave space for border, header, and footer
    max_x = w - 4  # Leave space for borders
    
    # Calculate max scroll position
    total_lines = len(lines)
    max_scroll = max(0, total_lines - max_y)
    
    # Flag to track if we need to redraw
    redraw = True
    
    while True:
        if redraw:
            window.clear()
            window.box()
            
            # Add header with scroll position information
            header = f"{title} (line {scroll_pos+1}/{total_lines})"
            try:
                window.attron(get_color(ColorPair.HEADER, bold=True))
                window.addstr(1, 2, header[:max_x])
                window.attroff(get_color(ColorPair.HEADER, bold=True))
            except curses.error:
                pass
            
            # Display visible lines
            display_lines = min(max_y, total_lines - scroll_pos)
            for i in range(display_lines):
                y_pos = i + 2  # Start at line 2 (after header)
                line_idx = scroll_pos + i
                
                if line_idx < total_lines and y_pos < h - 2:
                    try:
                        # Truncate line to fit window width
                        line = lines[line_idx][:max_x]
                        window.addstr(y_pos, 2, line)
                    except curses.error:
                        continue
            
            # Add scroll indicators
            if scroll_pos > 0:
                try:
                    window.addstr(1, max_x + 1, "↑")
                except curses.error:
                    pass
            
            if scroll_pos < max_scroll:
                try:
                    window.addstr(max_y + 1, max_x + 1, "↓")
                except curses.error:
                    pass
            
            # Add instructions at the bottom
            try:
                window.addstr(h-2, 2, 
                             "↑/↓: scroll 1 line, PgUp/PgDn: scroll page, Home/End: start/end, q: quit")
            except curses.error:
                pass
            
            window.refresh()
            redraw = False
        
        # Handle user input
        key = window.getch()
        
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