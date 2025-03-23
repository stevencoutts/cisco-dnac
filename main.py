#!/usr/bin/env python3
"""
Entry point for the Cisco Catalyst Centre CLI Tools.
Author: Steven Coutts
"""
import sys
import curses
from dnac.cli.menu import main_menu

def main():
    """Main entry point for the application."""
    try:
        # Explicitly call the main_menu with a stdscr object
        curses.wrapper(main_menu)
        return 0
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 