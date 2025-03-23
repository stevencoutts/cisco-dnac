#!/usr/bin/env python3
"""
Main menu handling for the CLI interface.
Author: Steven Coutts
"""
import curses
import sys
import subprocess
import os
from typing import List, Dict, Any, Optional, Callable

from dnac.core.config import load_config
from dnac.core.fabric import is_fabric_enabled
from dnac.cli.loading import show_loading_screen
from dnac.cli.output import show_scrollable_output
from dnac.cli.config_editor import edit_config
from dnac.ui.colors import ColorPair, get_color, initialize_colors
from dnac.ui.components import draw_status_indicator, draw_menu_item

class MenuItem:
    """Menu item with a label and associated action."""
    def __init__(self, label: str, action_fn=None, requires_fabric: bool = False, submenu: List['MenuItem'] = None):
        self.label = label
        self.action_fn = action_fn
        self.requires_fabric = requires_fabric
        self.submenu = submenu or []
        self.has_submenu = bool(submenu)
        
    def execute(self, window):
        """Execute the menu item's action or display submenu."""
        if self.action_fn:
            return self.action_fn(window)
        return None

def run_script(window, script_path: str, title: str = None, interactive: bool = False) -> None:
    """
    Run a Python script and display its output.
    
    Args:
        window: The curses window to draw on
        script_path: Path to the script to run (can include arguments)
        title: Optional title for the output window
        interactive: Whether the script requires interactive input
    """
    if title is None:
        # Extract base script name without arguments
        base_script_path = script_path.split()[0]
        title = f"Output from {os.path.basename(base_script_path)}"
    
    try:
        # Split script path and arguments
        script_parts = script_path.split()
        script_file = script_parts[0]
        script_args = script_parts[1:] if len(script_parts) > 1 else []
        
        # Set up environment with correct PYTHONPATH
        env = os.environ.copy()
        
        # Add project root directory to PYTHONPATH
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        if 'PYTHONPATH' in env:
            env['PYTHONPATH'] = f"{project_root}:{env['PYTHONPATH']}"
        else:
            env['PYTHONPATH'] = project_root
            
        # Save current terminal state
        curses_state = {
            'was_keypad': window.getyx()  # Just a placeholder to store something
        }
        
        # For both interactive scripts and scripts containing 'curses' in the name,
        # we need to completely exit curses mode
        is_curses_script = 'curses' in script_file
        if interactive or is_curses_script:
            # Completely exit curses mode
            curses.endwin()
            print(f"\n==== Running {os.path.basename(script_file)} ====\n")
            
            # Run the script allowing direct user interaction
            result = subprocess.run(
                [sys.executable, script_file] + script_args,
                env=env
            )
            
            # Pause to let user see the results
            input("\nPress Enter to return to the menu...")
            
            # Completely reinitialize curses
            stdscr = curses.initscr()
            curses.start_color()
            curses.noecho()
            curses.cbreak()
            stdscr.keypad(True)
            curses.curs_set(0)
            initialize_colors()
            
            # Force a full redraw
            stdscr.clear()
            stdscr.refresh()
            window.clear()
            window.refresh()
        else:
            # For non-interactive scripts, capture output
            result = subprocess.run(
                [sys.executable, script_file] + script_args,
                capture_output=True,
                text=True,
                check=True,
                env=env
            )
            
            # Display the output
            show_scrollable_output(window, result.stdout, title)
        
    except subprocess.CalledProcessError as e:
        if interactive or is_curses_script:
            # Already in terminal mode
            print(f"Error running {script_path}:\n{str(e)}\n{e.stderr}")
            input("\nPress Enter to return to the menu...")
            
            # Completely reinitialize curses
            stdscr = curses.initscr()
            curses.start_color()
            curses.noecho()
            curses.cbreak()
            stdscr.keypad(True)
            curses.curs_set(0)
            initialize_colors()
            
            # Force a full redraw
            stdscr.clear()
            stdscr.refresh()
            window.clear()
            window.refresh()
        else:
            # Handle script error in curses mode
            error_output = f"Error running {script_path}:\n\n{str(e)}\n\n{e.stderr}"
            show_scrollable_output(window, error_output, "Error")
    except KeyboardInterrupt:
        if interactive or is_curses_script:
            # Restore curses mode
            print("\nOperation cancelled by user")
            input("\nPress Enter to return to the menu...")
            
            # Completely reinitialize curses
            stdscr = curses.initscr()
            curses.start_color()
            curses.noecho()
            curses.cbreak()
            stdscr.keypad(True)
            curses.curs_set(0)
            initialize_colors()
            
            # Force a full redraw
            stdscr.clear()
            stdscr.refresh()
            window.clear()
            window.refresh()

def draw_menu(window, items: List[MenuItem], selected_idx: int, fabric_enabled: bool, title_text: str = "Cisco Catalyst Centre Tools", breadcrumb: str = None) -> None:
    """
    Draw the menu with the current selection.
    
    Args:
        window: The curses window to draw on
        items: List of menu items
        selected_idx: Index of the currently selected item
        fabric_enabled: Whether fabric is enabled on DNAC
        title_text: Title to display at the top
        breadcrumb: Navigation breadcrumb path
    """
    window.clear()
    h, w = window.getmaxyx()
    
    # Draw title
    try:
        window.attron(get_color(ColorPair.HEADER, bold=True))
        window.addstr(0, (w - len(title_text)) // 2, title_text)
        window.attroff(get_color(ColorPair.HEADER, bold=True))
    except curses.error:
        pass
    
    # Draw breadcrumb if available
    if breadcrumb:
        try:
            window.addstr(1, 2, breadcrumb)
        except curses.error:
            pass
    
    # Add fabric status indicator
    draw_status_indicator(
        window, 
        fabric_enabled, 
        text_enabled="● FABRIC ENABLED",
        text_disabled="○ FABRIC DISABLED",
        y=1,
        x=w-20 if w > 20 else 0
    )
    
    # Calculate visible range
    visible_height = h - 5  # Leave space for title, breadcrumb and instructions
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
        y = 3 + (idx - start_idx)  # Start at y=3 to leave space for title and breadcrumb
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
                label = item.label
                if item.has_submenu:
                    label = f"{label} ▶"
                draw_menu_item(window, label, y, idx == selected_idx)
        except curses.error:
            continue
    
    # Draw scroll indicators if needed
    if start_idx > 0:
        try:
            window.addstr(2, 2, "↑")
        except curses.error:
            pass
    if end_idx < total_height:
        try:
            window.addstr(h-3, 2, "↓")
        except curses.error:
            pass
    
    # Draw instructions
    try:
        window.addstr(h-2, 2, "Use ↑↓ to navigate, Enter to select, Backspace/Esc to go back, q to quit")
    except curses.error:
        pass
    
    window.refresh()

def display_submenu(window, parent_item: MenuItem, fabric_enabled: bool, breadcrumb_path: str) -> None:
    """
    Display a submenu for a menu item.
    
    Args:
        window: The curses window
        parent_item: The parent menu item containing submenu items
        fabric_enabled: Whether fabric is enabled
        breadcrumb_path: The current breadcrumb path
    """
    if not parent_item.submenu:
        return
    
    current_idx = 0
    submenu_items = parent_item.submenu.copy()
    
    # Add a blank separator item and a "Back" item at the end
    separator_item = MenuItem("", action_fn=lambda window: None)  # Empty separator
    back_item = MenuItem("← Back")
    submenu_items.append(separator_item)
    submenu_items.append(back_item)
    
    # Create new breadcrumb
    new_breadcrumb = f"{breadcrumb_path} > {parent_item.label}"
    
    # Draw initial submenu
    draw_menu(window, submenu_items, current_idx, fabric_enabled, 
              title_text="Cisco Catalyst Centre Tools", 
              breadcrumb=new_breadcrumb)
    
    # Submenu loop
    while True:
        key = window.getch()
        
        if key == curses.KEY_UP:
            if current_idx > 0:
                current_idx -= 1
                draw_menu(window, submenu_items, current_idx, fabric_enabled, 
                          breadcrumb=new_breadcrumb)
        elif key == curses.KEY_DOWN:
            if current_idx < len(submenu_items) - 1:
                current_idx += 1
                draw_menu(window, submenu_items, current_idx, fabric_enabled, 
                          breadcrumb=new_breadcrumb)
        elif key == ord('\n'):  # Enter key
            item = submenu_items[current_idx]
            
            # Skip disabled items
            if item.requires_fabric and not fabric_enabled:
                continue
            
            # Skip separator item
            if item.label == "":
                continue
                
            # Back item returns to parent menu
            if item == back_item:  # Back item
                return
                
            # Handle submenu
            if item.has_submenu:
                display_submenu(window, item, fabric_enabled, new_breadcrumb)
                # Redraw this submenu after returning
                draw_menu(window, submenu_items, current_idx, fabric_enabled, 
                          breadcrumb=new_breadcrumb)
            else:
                # Execute item action
                item.execute(window)
                # Redraw submenu after action
                draw_menu(window, submenu_items, current_idx, fabric_enabled, 
                          breadcrumb=new_breadcrumb)
        elif key in (curses.KEY_BACKSPACE, 27, ord('\b'), 8):  # Backspace, Escape
            return
        elif key == ord('q'):
            sys.exit(0)

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
    
    # Create main menu items for scripts
    device_menu_items = [
        MenuItem(
            label=name,
            action_fn=lambda window, path=path: run_script(window, path, name, False),
            requires_fabric=name == "List SDA Segments"
        )
        for name, path in scripts.items()
    ]
    
    # Site Hierarchy submenu items
    site_hierarchy_items = [
        MenuItem(
            label="List Hierarchy",
            action_fn=lambda window: run_script(window, os.path.join(script_dir, "hierarchy.py"), "Site Hierarchy", False)
        ),
        MenuItem(
            label="Add Site",
            action_fn=lambda window: run_script(window, os.path.join(script_dir, "add_site_curses.py") + " --from-menu", "Add Site", False)
        )
    ]
    
    # Main menu items
    menu_items = device_menu_items + [
        # Site Hierarchy menu with submenu
        MenuItem(
            label="Site Hierarchy",
            submenu=site_hierarchy_items
        ),
        # Add configuration editor
        MenuItem(
            label="Edit Configuration",
            action_fn=lambda window: edit_config(window)
        ),
        # Add separator
        MenuItem(
            label=""
        ),
        # Add exit option
        MenuItem(
            label="Exit",
            action_fn=lambda window: None
        )
    ]
    
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
                
            # Handle submenu
            if item.has_submenu:
                display_submenu(stdscr, item, fabric_enabled, "Main")
                # Redraw main menu after submenu closes
                draw_menu(stdscr, menu_items, current_idx, fabric_enabled)
            # Configuration requires special handling
            elif item.label == "Edit Configuration":
                config = item.execute(stdscr)
                
                # Recheck fabric status after config change
                fabric_enabled = show_loading_screen(
                    stdscr,
                    "Cisco Catalyst Centre Tools",
                    "Reconnecting to DNAC...",
                    lambda: is_fabric_enabled(config),
                    duration=1.0
                )
                # Redraw menu
                draw_menu(stdscr, menu_items, current_idx, fabric_enabled)
            else:
                # Run the action
                item.execute(stdscr)
                # Redraw menu
                draw_menu(stdscr, menu_items, current_idx, fabric_enabled)
        elif key == ord('q'):
            break 