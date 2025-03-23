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
from dnac.ui.components import draw_status_indicator, draw_menu_item, draw_standard_header_footer

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

def run_script(window, script_path: str, title: str = None, interactive: bool = False, suppress_prompts: bool = False) -> None:
    """
    Run a Python script and display its output.
    
    Args:
        window: The curses window to draw on
        script_path: Path to the script to run (can include arguments)
        title: Optional title for the output window
        interactive: Whether the script requires interactive input
        suppress_prompts: Whether to suppress "Running..." and "Press Enter" prompts
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
            
        # Check if this is a script that contains its own curses handling
        # Add specific scripts that have their own curses handling here
        script_base = os.path.basename(script_file)
        is_curses_script = 'curses' in script_file or script_base in ['hierarchy.py', 'devices.py']
        
        if interactive or is_curses_script:
            # Completely exit curses mode
            curses.endwin()
            
            # Show running message unless suppressed
            if not suppress_prompts:
                print(f"\n==== Running {os.path.basename(script_file)} ====\n")
            
            # Run the script allowing direct user interaction
            result = subprocess.run(
                [sys.executable, script_file] + script_args,
                env=env
            )
            
            # No pause, immediately return to menu
            
            # Restart curses safely without assuming any previous state
            os.environ.setdefault('ESCDELAY', '25')  # Reduce ESC key delay
            
            # Completely reinitialize curses
            stdscr = curses.initscr()
            curses.start_color()
            curses.noecho()
            curses.cbreak()
            stdscr.keypad(True)
            curses.curs_set(0)
            initialize_colors()
            
            # Restore navy blue background
            stdscr.bkgd(' ', get_color(ColorPair.NORMAL))
            
            # Force a full redraw
            stdscr.clear()
            stdscr.refresh()
            window.clear()
            window.bkgd(' ', get_color(ColorPair.NORMAL))
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
            if not suppress_prompts:
                print(f"Error running {script_path}:\n{str(e)}")
                if hasattr(e, 'stderr') and e.stderr:
                    print(f"Error output:\n{e.stderr}")
                    # No error pause
            
            # Restart curses safely
            os.environ.setdefault('ESCDELAY', '25')
            
            # Completely reinitialize curses
            stdscr = curses.initscr()
            curses.start_color()
            curses.noecho()
            curses.cbreak()
            stdscr.keypad(True)
            curses.curs_set(0)
            initialize_colors()
            
            # Restore navy blue background
            stdscr.bkgd(' ', get_color(ColorPair.NORMAL))
            
            # Force a full redraw
            stdscr.clear()
            stdscr.refresh()
            window.clear()
            window.bkgd(' ', get_color(ColorPair.NORMAL))
            window.refresh()
        else:
            # Handle script error in curses mode
            error_output = f"Error running {script_path}:\n\n{str(e)}"
            if hasattr(e, 'stderr') and e.stderr:
                error_output += f"\n\n{e.stderr}"
            show_scrollable_output(window, error_output, "Error")
    except KeyboardInterrupt:
        if interactive or is_curses_script:
            # Restore curses mode
            if not suppress_prompts:
                print("\nOperation cancelled by user")
                # No pause after cancellation
            
            # Restart curses safely
            os.environ.setdefault('ESCDELAY', '25')
            
            # Completely reinitialize curses
            stdscr = curses.initscr()
            curses.start_color()
            curses.noecho()
            curses.cbreak()
            stdscr.keypad(True)
            curses.curs_set(0)
            initialize_colors()
            
            # Restore navy blue background
            stdscr.bkgd(' ', get_color(ColorPair.NORMAL))
            
            # Force a full redraw
            stdscr.clear()
            stdscr.refresh()
            window.clear()
            window.bkgd(' ', get_color(ColorPair.NORMAL))
            window.refresh()
    except Exception as e:
        # Added more detailed error handling
        error_message = f"Unexpected error running {script_path}:\n\n{str(e)}\n\nType: {type(e)}"
        show_scrollable_output(window, error_message, "Error")

def draw_menu(window, items: List[MenuItem], selected_idx: int, fabric_enabled: bool, title_text: str = "Cisco Catalyst Centre Tools", breadcrumb: str = None, connected: bool = True) -> None:
    """
    Draw a menu with the provided items.
    
    Args:
        window: The curses window
        items: List of menu items
        selected_idx: Currently selected index
        fabric_enabled: Whether fabric is enabled
        title_text: Title text for the menu
        breadcrumb: Optional breadcrumb path
        connected: Whether connected to Catalyst Centre
    """
    # Set background and clear window
    window.bkgd(' ', get_color(ColorPair.NORMAL))
    window.clear()
    
    # Get window dimensions
    h, w = window.getmaxyx()
    
    # Use standard header/footer
    start_y = draw_standard_header_footer(
        window, 
        title=title_text,
        subtitle=breadcrumb,
        fabric_enabled=fabric_enabled,
        connected=connected
    )
    
    # Calculate available menu height
    menu_height = h - start_y - 2  # Leave room for status at bottom
    
    # Calculate visible range based on selected item
    visible_count = min(len(items), menu_height)
    
    # Simple centering around selected item
    half_visible = visible_count // 2
    start_idx = max(0, selected_idx - half_visible)
    
    # Adjust if we're near the end of the list
    if start_idx + visible_count > len(items):
        start_idx = max(0, len(items) - visible_count)
    
    # Draw menu items
    for i in range(min(visible_count, len(items))):
        idx = start_idx + i
        item = items[idx]
        y = start_y + i
        
        # Check if this item is disabled due to fabric requirement
        is_disabled = item.requires_fabric and not fabric_enabled
        
        if is_disabled:
            # Draw as disabled
            window.attron(get_color(ColorPair.DISABLED))
            disabled_label = f"{item.label} (Requires Fabric)"
            window.addstr(y, (w - len(disabled_label)) // 2, disabled_label)
            window.attroff(get_color(ColorPair.DISABLED))
        else:
            # Draw normally
            label = item.label
            if item.has_submenu:
                label = f"{label} ▶"
            draw_menu_item(window, label, y, idx == selected_idx)
    
    # Draw scrolling indicators if needed
    if len(items) > visible_count:
        if start_idx > 0:
            # Show up arrow to indicate more items above
            window.attron(get_color(ColorPair.NORMAL))
            window.addstr(start_y - 1, w // 2, "▲")
            window.attroff(get_color(ColorPair.NORMAL))
        
        if start_idx + visible_count < len(items):
            # Show down arrow to indicate more items below
            window.attron(get_color(ColorPair.NORMAL))
            window.addstr(start_y + visible_count, w // 2, "▼")
            window.attroff(get_color(ColorPair.NORMAL))
    
    # Refresh window
    window.refresh()

def display_submenu(window, parent_item: MenuItem, fabric_enabled: bool, breadcrumb_path: str, connected: bool = True) -> None:
    """
    Display a submenu for a menu item.
    
    Args:
        window: The curses window
        parent_item: The parent menu item containing submenu items
        fabric_enabled: Whether fabric is enabled
        breadcrumb_path: The current breadcrumb path
        connected: Whether connected to Catalyst Centre
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
              breadcrumb=new_breadcrumb,
              connected=connected)
    
    # Submenu loop
    while True:
        key = window.getch()
        
        if key == curses.KEY_UP:
            if current_idx > 0:
                current_idx -= 1
                draw_menu(window, submenu_items, current_idx, fabric_enabled, 
                          breadcrumb=new_breadcrumb,
                          connected=connected)
        elif key == curses.KEY_DOWN:
            if current_idx < len(submenu_items) - 1:
                current_idx += 1
                draw_menu(window, submenu_items, current_idx, fabric_enabled, 
                          breadcrumb=new_breadcrumb,
                          connected=connected)
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
                display_submenu(window, item, fabric_enabled, new_breadcrumb, connected)
                # Redraw this submenu after returning
                draw_menu(window, submenu_items, current_idx, fabric_enabled, 
                          breadcrumb=new_breadcrumb,
                          connected=connected)
            else:
                # Execute item action
                item.execute(window)
                # Redraw submenu after action
                draw_menu(window, submenu_items, current_idx, fabric_enabled, 
                          breadcrumb=new_breadcrumb,
                          connected=connected)
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
    try:
        # Hide cursor and initialize colors
        curses.curs_set(0)
        initialize_colors()
        
        # Set up navy blue background
        stdscr.bkgd(' ', get_color(ColorPair.NORMAL))
        stdscr.clear()
        stdscr.refresh()
        
        config = load_config()
        
        # Check if fabric is enabled (with loading screen)
        fabric_enabled = show_loading_screen(
            stdscr,
            "Cisco Catalyst Centre Tools",
            "Connecting to DNAC...",
            lambda: is_fabric_enabled(config)
        )
        
        # Set connection status based on successful connection to DNAC
        connected = fabric_enabled is not None  # If fabric_enabled is not None, we are connected
        
        # Define menu items
        script_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "scripts")
        
        # Map of script labels to paths
        scripts = {
            "List Network Devices": os.path.join(script_dir, "devices.py")
        }
        
        # Site Hierarchy submenu items
        site_hierarchy_items = [
            MenuItem(
                label="List Hierarchy",
                action_fn=lambda window: run_script(window, os.path.join(script_dir, "hierarchy.py"), "Site Hierarchy", False, True)
            ),
            MenuItem(
                label="Add Site",
                action_fn=lambda window: run_script(window, os.path.join(script_dir, "add_site_curses.py") + " --from-menu", "Add Site", False, True)
            )
        ]
        
        # Create main menu items for scripts
        device_menu_items = [
            MenuItem(
                label=name,
                action_fn=lambda window, path=path: run_script(window, path, name, False, True)
            )
            for name, path in scripts.items()
        ]
        
        # Fabric Configuration submenu items
        fabric_menu_items = [
            MenuItem(
                label="List SDA Segments",
                action_fn=lambda window: run_script(window, os.path.join(script_dir, "segment.py"), "List SDA Segments", False, True),
                requires_fabric=True
            )
        ]
        
        # Main menu items
        menu_items = [
            # Site Hierarchy menu with submenu (moved to top)
            MenuItem(
                label="Site Hierarchy",
                submenu=site_hierarchy_items
            ),
            # Fabric Configuration menu with submenu
            MenuItem(
                label="Fabric Configuration",
                submenu=fabric_menu_items,
                requires_fabric=True
            )
        ] + device_menu_items + [
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
        draw_menu(stdscr, menu_items, current_idx, fabric_enabled, connected=connected)
        
        # Main loop
        while True:
            key = stdscr.getch()
            
            if key == curses.KEY_UP:
                if current_idx > 0:
                    current_idx -= 1
                    draw_menu(stdscr, menu_items, current_idx, fabric_enabled, connected=connected)
            elif key == curses.KEY_DOWN:
                if current_idx < len(menu_items) - 1:
                    current_idx += 1
                    draw_menu(stdscr, menu_items, current_idx, fabric_enabled, connected=connected)
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
                    display_submenu(stdscr, item, fabric_enabled, "Main", connected)
                    # Redraw main menu after submenu closes
                    draw_menu(stdscr, menu_items, current_idx, fabric_enabled, connected=connected)
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
                    # Update connection status after reconnection attempt
                    connected = fabric_enabled is not None
                    # Redraw menu
                    draw_menu(stdscr, menu_items, current_idx, fabric_enabled, connected=connected)
                else:
                    # Run the action
                    item.execute(stdscr)
                    # Redraw menu
                    draw_menu(stdscr, menu_items, current_idx, fabric_enabled, connected=connected)
            elif key == ord('q'):
                break
    except Exception as e:
        # Cleanly exit curses mode
        curses.endwin()
        print(f"Error in main menu: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        # Wait for user acknowledgment
        input("\nPress Enter to exit...") 