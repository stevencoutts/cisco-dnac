#!/usr/bin/env python3
"""
Main entry point for the DNAC CLI application.
Author: Steven Coutts
"""
import os
import sys
import curses
import argparse
from typing import List, Dict, Any

from dnac.cli.menu import main_menu

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Cisco Catalyst Centre CLI Tools")
    parser.add_argument("-c", "--config", help="Path to config file", default="config.yaml")
    parser.add_argument("-v", "--verbose", help="Enable verbose output", action="store_true")
    return parser.parse_args()

def main() -> int:
    """Main entry point for the application."""
    # Parse command line arguments
    args = parse_args()
    
    # Set config path as environment variable for other modules to use
    os.environ["DNAC_CONFIG_PATH"] = args.config
    
    # Enable verbose output if requested
    if args.verbose:
        os.environ["DNAC_VERBOSE"] = "1"
    
    # Start the curses application
    try:
        curses.wrapper(main_menu)
        return 0
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        return 0
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 