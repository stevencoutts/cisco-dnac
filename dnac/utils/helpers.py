#!/usr/bin/env python3
"""
General utility functions.
Author: Steven Coutts
"""
import os
import sys
import subprocess
from typing import List, Dict, Any, Optional, Tuple

def find_script_path(script_name: str, search_paths: Optional[List[str]] = None) -> Optional[str]:
    """
    Find the absolute path to a script.
    
    Args:
        script_name: Name of the script to find (with or without .py extension)
        search_paths: List of paths to search in addition to the default locations
        
    Returns:
        The absolute path to the script if found, None otherwise
    """
    if not script_name.endswith('.py'):
        script_name += '.py'
        
    # Add default search paths
    if search_paths is None:
        search_paths = []
        
    # Add the scripts directory relative to the current module
    module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scripts_dir = os.path.join(module_dir, 'scripts')
    search_paths.append(scripts_dir)
    
    # Add the current directory
    search_paths.append(os.getcwd())
    
    # Search for the script
    for path in search_paths:
        full_path = os.path.join(path, script_name)
        if os.path.isfile(full_path):
            return full_path
            
    return None

def run_command(cmd: List[str], capture_output: bool = True) -> Tuple[int, str, str]:
    """
    Run a shell command and return the result.
    
    Args:
        cmd: List of command arguments
        capture_output: Whether to capture and return stdout/stderr
        
    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            check=False
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)

def suppress_output() -> Tuple[Any, Any]:
    """
    Temporarily suppress stdout and stderr.
    
    Returns:
        Tuple of (old_stdout, old_stderr) to be restored later
    """
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')
    return old_stdout, old_stderr

def restore_output(old_stdout: Any, old_stderr: Any) -> None:
    """
    Restore stdout and stderr after suppression.
    
    Args:
        old_stdout: Original stdout to restore
        old_stderr: Original stderr to restore
    """
    sys.stdout.close()
    sys.stderr.close()
    sys.stdout = old_stdout
    sys.stderr = old_stderr 