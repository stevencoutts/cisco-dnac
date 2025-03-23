#!/usr/bin/env python3
import curses
import sys
import subprocess
import os
from typing import List, Tuple

def run_script(script_name: str) -> None:
    """Run a Python script and handle its output."""
    try:
        # Run the script and capture output
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Create a new window for output with proper padding
        output_win = curses.newwin(curses.LINES-2, curses.COLS, 1, 0)
        output_win.box()
        
        # Calculate safe boundaries
        max_y = curses.LINES - 3  # Leave space for border and instructions
        max_x = curses.COLS - 4   # Leave space for borders
        
        # Split output into lines and display
        lines = result.stdout.split('\n')
        scroll_pos = 0
        max_scroll = max(0, len(lines) - (max_y - 2))  # Account for header and instructions
        
        while True:
            output_win.clear()
            output_win.box()
            
            # Add header
            try:
                output_win.addstr(1, 2, f"Output from {script_name}")
            except curses.error:
                pass
            
            # Display visible lines
            for i, line in enumerate(lines[scroll_pos:scroll_pos + (max_y - 2)], 2):
                if i >= max_y:
                    break
                try:
                    # Truncate line to fit window width
                    truncated_line = line[:max_x]
                    output_win.addstr(i, 2, truncated_line)
                except curses.error:
                    continue
            
            # Add instructions at the bottom
            try:
                output_win.addstr(max_y, 2, "Use ↑↓ to scroll, 'q' to return to menu")
            except curses.error:
                pass
            
            output_win.refresh()
            
            # Handle user input
            key = output_win.getch()
            if key == ord('q'):
                break
            elif key == curses.KEY_UP and scroll_pos > 0:
                scroll_pos = max(0, scroll_pos - 1)
            elif key == curses.KEY_DOWN and scroll_pos < max_scroll:
                scroll_pos = min(max_scroll, scroll_pos + 1)
                
    except subprocess.CalledProcessError as e:
        # Handle script errors
        error_win = curses.newwin(10, 50, curses.LINES//2-5, curses.COLS//2-25)
        error_win.box()
        try:
            error_win.addstr(1, 2, f"Error running {script_name}:")
            error_win.addstr(2, 2, str(e))
            error_win.addstr(3, 2, e.stderr)
            error_win.addstr(4, 2, "Press any key to continue")
        except curses.error:
            pass
        error_win.refresh()
        error_win.getch()

def draw_menu(stdscr, selected_idx: int, options: List[str]) -> None:
    """Draw the menu with the current selection."""
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    
    # Define title
    title = "Cisco Catalyst Centre Tools"
    
    # Draw title
    try:
        stdscr.addstr(0, (w - len(title)) // 2, title)
    except curses.error:
        pass
    
    # Draw options
    for idx, option in enumerate(options):
        x = w//2 - len(option)//2
        y = h//2 - len(options)//2 + idx
        if y >= h - 1:  # Skip if we're at the bottom of the screen
            break
        try:
            if idx == selected_idx:
                stdscr.attron(curses.A_REVERSE)
                stdscr.addstr(y, x, option)
                stdscr.attroff(curses.A_REVERSE)
            else:
                stdscr.addstr(y, x, option)
        except curses.error:
            continue
    
    # Draw instructions
    try:
        stdscr.addstr(h-2, 2, "Use ↑↓ to navigate, Enter to select, q to quit")
    except curses.error:
        pass
    stdscr.refresh()

def main(stdscr):
    # Initialize color support
    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
    
    # Menu options
    options = [
        "List Network Devices",
        "List SDA Segments",
        "Exit"
    ]
    
    current_idx = 0
    draw_menu(stdscr, current_idx, options)
    
    while True:
        key = stdscr.getch()
        
        if key == curses.KEY_UP and current_idx > 0:
            current_idx -= 1
        elif key == curses.KEY_DOWN and current_idx < len(options) - 1:
            current_idx += 1
        elif key == ord('\n'):  # Enter key
            if current_idx == 0:
                run_script("devices.py")
            elif current_idx == 1:
                run_script("segment.py")
            elif current_idx == 2:
                break
        elif key == ord('q'):
            break
            
        draw_menu(stdscr, current_idx, options)

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass 