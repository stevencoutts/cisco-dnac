#!/usr/bin/env python3
"""
Loading screens and animations for the CLI interface.
Author: Steven Coutts
"""
import curses
import time
import sys
import os
from typing import Callable, Any, Optional

from dnac.ui.colors import ColorPair, get_color
from dnac.ui.components import draw_title, draw_cisco_logo, draw_progress_bar, draw_spinner

def show_loading_screen(window, title: str, loading_text: str, operation: Callable[[], Any], 
                       duration: float = 2.0, complete_msg: str = "Initialization complete!") -> Any:
    """
    Show a loading screen while performing an operation.
    
    Args:
        window: The curses window to draw on
        title: The title to display
        loading_text: Text to show during loading
        operation: Function to call after the animation duration
        duration: Minimum duration of the loading animation in seconds
        complete_msg: Message to show when complete
        
    Returns:
        The result of the operation function
    """
    # Capture stdout/stderr to hide messages
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')
    
    result = None
    frame_index = 0
    start_time = time.time()
    operation_complete = False
    
    try:
        # Animation loop
        while time.time() - start_time < duration or not operation_complete:
            window.clear()
            h, w = window.getmaxyx()
            
            # Draw title
            draw_title(window, title)
            
            # Draw logo
            draw_cisco_logo(window, y_offset=2)
            
            # Calculate progress percentage (0-99%)
            elapsed = time.time() - start_time
            progress = min(int((elapsed / duration) * 100), 99)
            
            # Draw spinner and progress
            draw_spinner(window, frame_index, loading_text, h//2)
            draw_progress_bar(window, progress, width=40, y=h//2 + 2)
            
            # Update frame and refresh
            frame_index += 1
            window.refresh()
            curses.napms(100)  # Update every 100ms
            
            # Run the operation once we're at least 50% through the animation
            if not operation_complete and elapsed >= duration * 0.5:
                result = operation()
                operation_complete = True
        
        # Show completion screen
        window.clear()
        
        # Draw title and logo
        draw_title(window, title)
        draw_cisco_logo(window, y_offset=2)
        
        # Draw complete message
        window.attron(get_color(ColorPair.SUCCESS, bold=True))
        window.addstr(h//2, (w - len(complete_msg))//2, complete_msg)
        window.attroff(get_color(ColorPair.SUCCESS, bold=True))
        
        # Draw 100% progress bar
        draw_progress_bar(window, 100, width=40, y=h//2 + 2)
        
        window.refresh()
        curses.napms(1000)  # Show completion for 1 second
        
    finally:
        # Restore stdout/stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    
    return result 