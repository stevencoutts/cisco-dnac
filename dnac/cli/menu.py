#!/usr/bin/env python3
"""
Main menu handling for the CLI interface.
Author: Steven Coutts
"""
import curses
import sys
import subprocess
import os
from typing import List, Dict, Any

from dnac.core.config import load_config
from dnac.core.fabric import is_fabric_enabled
from dnac.cli.loading import show_loading_screen
from dnac.cli.output import show_scrollable_output
from dnac.cli.config_editor import edit_config
from dnac.ui.colors import ColorPair, get_color, initialize_colors
from dnac.ui.components import draw_status_indicator, draw_menu_item

class MenuItem:
    """Menu item with a label and associated action."""
    def __init__(self, label: str, action_fn, requires_fabric: bool = False):
        self.label = label
        self.action_fn = action_fn
        self.requires_fabric = requires_fabric

def run_script(window, script_path: str, title: str = None) -> None:
    """
    Run a Python script and display its output.
    
    Args:
        window: The curses window to draw on
        script_path: Path to the script to run
        title: Optional title for the output window
    """
    if title is None:
        title = f"Output from {os.path.basename(script_path)}"
    
    try:
        # Run the script and capture output
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Display the output
        show_scrollable_output(window, result.stdout, title)
        
    except subprocess.CalledProcessError as e:
        # Handle script error
        error_output = f"Error running {script_path}:\n\n{str(e)}\n\n{e.stderr}"
        show_scrollable_output(window, error_output, "Error")

def draw_menu(window, items: List[MenuItem], selected_idx: int, fabric_enabled: bool) -> None:
    """
    Draw the menu with the current selection.
    
    Args:
        window: The curses window to draw on
        items: List of menu items
        selected_idx: Index of the currently selected item
        fabric_enabled: Whether fabric is enabled on DNAC
    """
    window.clear()
    h, w = window.getmaxyx()
    
    # Define title
    title = "Cisco Catalyst Centre Tools"
    
    # Draw title
    try:
        window.attron(get_color(ColorPair.HEADER, bold=True))
        window.addstr(0, (w - len(title)) // 2, title)
        window.attroff(get_color(ColorPair.HEADER, bold=True))
    except curses.error:
        pass
    
    # Add fabric status indicator
    draw_status_indicator(
        window, 
        fabric_enabled, 
        text_enabled="● FABRIC ENABLED",
        text_disabled="○ FABRIC DISABLED"
    )
    
    # Calculate visible range
    visible_height = h - 4  # Leave space for title and instructions
    total_height = len(items)
    
    # Keep selected item in view
    if selected_idx < 0:
        selected_idx = 0
    elif selected_idx >= total_height:
        selected_idx = total_height - 1
    
    # Calculate start index to keep selected item centered when possible
    start_idx = max(0, min(selected_idx - visible_height // 2, total_height - visible_height))
    end_idx = min(total_height, start_idx + visible_height)
    
    # Draw menu items
    for idx, item in enumerate(items[start_idx:end_idx], start=start_idx):
        y = 2 + (idx - start_idx)  # Start at y=2 to leave space for title
        if y >= h - 2:  # Leave space for instructions
            break
            
        # Determine if item should be disabled
        disabled = item.requires_fabric and not fabric_enabled
        
        # Draw item with appropriate styling
        try:
            if disabled:
                # Draw as disabled
                window.attron(get_color(ColorPair.DISABLED))
                window.addstr(y, (w - len(item.label) - 10) // 2, f"{item.label} (disabled)")
                window.attroff(get_color(ColorPair.DISABLED))
            else:
                # Draw normally
                draw_menu_item(window, item.label, y, idx == selected_idx)
        except curses.error:
            continue
    
    # Draw scroll indicators if needed
    if start_idx > 0:
        try:
            window.addstr(1, 2, "↑")
        except curses.error:
            pass
    if end_idx < total_height:
        try:
            window.addstr(h-3, 2, "↓")
        except curses.error:
            pass
    
    # Draw instructions
    try:
        window.addstr(h-2, 2, "Use ↑↓ to navigate, Enter to select, q to quit")
    except curses.error:
        pass
    
    window.refresh()

def main_menu(stdscr) -> None:
    """
    Display the main menu and handle user interaction.
    
    Args:
        stdscr: The main curses window
    """
    # Hide cursor and initialize colors
    curses.curs_set(0)
    initialize_colors()
    
    config = load_config()
    
    # Check if fabric is enabled (with loading screen)
    fabric_enabled = show_loading_screen(
        stdscr,
        "Cisco Catalyst Centre Tools",
        "Connecting to DNAC...",
        lambda: is_fabric_enabled(config)
    )
    
    # Define menu items
    script_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "scripts")
    
    # Map of script labels to paths
    scripts = {
        "List Network Devices": os.path.join(script_dir, "devices.py"),
        "List SDA Segments": os.path.join(script_dir, "segment.py")
    }
    
    # Create menu items
    menu_items = [
        MenuItem(
            label=name,
            action_fn=lambda window, path=path: run_script(window, path, name),
            requires_fabric=name == "List SDA Segments"
        )
        for name, path in scripts.items()
    ]
    
    # Add configuration editor
    menu_items.append(MenuItem(
        label="Edit Configuration",
        action_fn=lambda window: edit_config(window)
    ))
    
    # Add exit option
    menu_items.append(MenuItem(
        label="Exit",
        action_fn=lambda window: None
    ))
    
    # Menu state
    current_idx = 0
    
    # Draw initial menu
    draw_menu(stdscr, menu_items, current_idx, fabric_enabled)
    
    # Main loop
    while True:
        key = stdscr.getch()
        
        if key == curses.KEY_UP:
            if current_idx > 0:
                current_idx -= 1
                draw_menu(stdscr, menu_items, current_idx, fabric_enabled)
        elif key == curses.KEY_DOWN:
            if current_idx < len(menu_items) - 1:
                current_idx += 1
                draw_menu(stdscr, menu_items, current_idx, fabric_enabled)
        elif key == ord('\n'):  # Enter key
            item = menu_items[current_idx]
            
            # Skip disabled items
            if item.requires_fabric and not fabric_enabled:
                continue
                
            # Exit item just breaks the loop
            if item.label == "Exit":
                break
                
            # Configuration requires special handling
            if item.label == "Edit Configuration":
                config = item.action_fn(stdscr)
                
                # Recheck fabric status after config change
                fabric_enabled = show_loading_screen(
                    stdscr,
                    "Cisco Catalyst Centre Tools",
                    "Reconnecting to DNAC...",
                    lambda: is_fabric_enabled(config),
                    duration=1.0
                )
            else:
                # Run the action
                item.action_fn(stdscr)
                
            # Redraw menu
            draw_menu(stdscr, menu_items, current_idx, fabric_enabled)
        elif key == ord('q'):
            break 