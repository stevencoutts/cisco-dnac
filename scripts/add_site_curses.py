#!/usr/bin/env python3
"""
Script to add a new site to Cisco Catalyst Centre using a curses-based UI.
Author: Steven Coutts
"""

import os
import sys
import argparse
import logging
import yaml
import json
import curses
import itertools
import time
from typing import Dict, Any, Optional, List

from dnac.core.api import Dnac
from dnac.ui.forms import show_form, show_dropdown_menu
from dnac.ui.colors import initialize_colors, ColorPair, get_color
from dnac.cli.loading import show_loading_screen
from dnac.ui.components import draw_title, draw_cisco_logo, draw_progress_bar, draw_spinner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
    handlers=[
        logging.FileHandler("dnac_add_site.log"),
        logging.StreamHandler()
    ]
)

DEFAULT_CONFIG_FILE = "config.yaml"


def load_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from file."""
    if config_file is None:
        config_file = DEFAULT_CONFIG_FILE

    if not os.path.exists(config_file):
        print(f"Config file {config_file} not found")
        sys.exit(1)

    with open(config_file) as f:
        return yaml.safe_load(f)


def get_parent_sites(dnac):
    """Get available parent sites from DNAC."""
    try:
        parent_sites = []
        response = dnac.get("site", ver="v1")
        
        logging.debug("Fetching available parent sites...")
        
        if hasattr(response, 'response') and hasattr(response.response, 'json'):
            sites_data = response.response.json()
            logging.debug(f"Raw sites response: {json.dumps(sites_data, indent=2)}")
            
            # Handle response format
            if isinstance(sites_data, dict) and 'response' in sites_data:
                sites_data = sites_data['response']
                
            # Build list of available sites
            available_sites = []
            
            # Add Global as first option
            available_sites.append({"name": "Global", "id": "global", "parentId": None})
            
            if isinstance(sites_data, list):
                for site in sites_data:
                    if 'name' in site and 'id' in site:
                        # Log UK sites specifically for debugging
                        if 'UK' in site.get('name', ''):
                            logging.debug(f"Found UK site: {site.get('name')} with ID: {site.get('id')}")
                            
                        available_sites.append({
                            "name": site['name'],
                            "id": site['id'],
                            "parentId": site.get('parentId'),
                            # Include additional attributes for debugging
                            "siteNameHierarchy": site.get('siteNameHierarchy', '')
                        })
            
            # Log full list of available sites
            logging.debug(f"Available parent sites: {json.dumps(available_sites, indent=2)}")
            
            # Convert to simple name and ID for use in UI
            for site in available_sites:
                parent_sites.append({
                    "name": site["name"],
                    "id": site["id"],
                    "parentId": site.get("parentId"),
                    "siteNameHierarchy": site.get("siteNameHierarchy", "")
                })
                
            return parent_sites
            
    except Exception as e:
        logging.error(f"Error fetching sites: {e}")
        return []


def create_site_data(site_type, site_name, parent_site=None, parent_id=None):
    """Create site data payload based on type and name."""
    # Create the payload in the format expected by the API
    if site_type == "area":
        site_data = {
            "type": site_type,
            "site": {
                "area": {
                    "name": site_name,
                    "parentName": parent_site if parent_site else "Global"
                }
            }
        }
        # Add parentId if available (more reliable than parentName)
        if parent_id and parent_id != "global":
            site_data["site"]["area"]["parentId"] = parent_id
            
    elif site_type == "building":
        site_data = {
            "type": site_type,
            "site": {
                "building": {
                    "name": site_name,
                    "parentName": parent_site if parent_site else "Global",
                    "address": "123 Example Street",
                    "latitude": 37.409,
                    "longitude": -121.965,
                    "country": "United Kingdom",  # Changed to UK
                    "state": "",  # Not needed for UK
                    "city": "London",  # Default UK city
                    "zipCode": ""  # Called postcode in UK
                }
            }
        }
        # Add parentId if available (more reliable than parentName)
        if parent_id and parent_id != "global":
            site_data["site"]["building"]["parentId"] = parent_id
            
    elif site_type == "floor":
        site_data = {
            "type": site_type,
            "site": {
                "floor": {
                    "name": site_name,
                    "parentName": parent_site if parent_site else "Global",
                    "rfModel": "Cubes And Walled Offices"  # Default RF model
                }
            }
        }
        # Add parentId if available (more reliable than parentName)
        if parent_id and parent_id != "global":
            site_data["site"]["floor"]["parentId"] = parent_id
    else:
        site_data = {}
    
    return site_data


def get_site_name(stdscr):
    """Get site name input directly from the user."""
    # Save cursor state
    try:
        old_cursor = curses.curs_set(1)
    except:
        old_cursor = 0
        
    # Turn on echo for text input
    curses.echo()
    
    # Get window dimensions
    h, w = stdscr.getmaxyx()
    
    # Clear screen
    stdscr.clear()
    
    # Draw title
    try:
        title = "Enter Site Name"
        stdscr.addstr(0, 2, title)
    except curses.error:
        pass
    
    # Draw prompt
    prompt = "Site Name: "
    try:
        stdscr.addstr(2, 4, prompt)
        
        # Draw note
        note = "(Press Enter when done)"
        stdscr.addstr(3, 4, note)
    except curses.error:
        pass
    
    stdscr.refresh()
    
    # Calculate input field size
    max_len = min(50, w - len(prompt) - 6)
    
    # Get input
    try:
        # Position cursor
        stdscr.move(2, 4 + len(prompt))
        
        # Get user input
        site_name = stdscr.getstr(max_len).decode('utf-8').strip()
    except Exception as e:
        site_name = ""
    
    # Reset terminal state
    curses.noecho()
    try:
        curses.curs_set(old_cursor)
    except:
        pass
    
    return site_name


def create_site_screen(stdscr, site_type, dnac, config, logger):
    """Screen for creating a new site."""
    # Get parent sites
    parent_sites = get_parent_sites(dnac)
    if not parent_sites:
        logger.error("Failed to fetch parent sites.")
        show_message(stdscr, "Failed to fetch parent sites.", curses.A_REVERSE)
        return False
    
    # Add a "Global" option for top-level sites
    parent_sites_dropdown = ["Global"] + [site.get("name") for site in parent_sites]
    parent_site_ids = {"Global": "global"}
    for site in parent_sites:
        parent_site_ids[site.get("name")] = site.get("id")
    
    # Set up variables
    site_name = ""
    parent_site = "Global"  # Default value
    parent_id = "global"    # Default global ID
    form_fields = ["site_name", "parent_site"]
    current_field = 0
    saved = False
    
    # Setup spinner for loading indicators
    spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
    
    while True:
        # Clear screen
        stdscr.clear()
        
        # Set up header
        title = f"Create New {site_type.capitalize()}"
        startx = max(0, (curses.COLS - len(title)) // 2)
        stdscr.addstr(1, startx, title, curses.A_BOLD)
        
        # Draw input fields
        stdscr.addstr(3, 2, "Site Name:", curses.A_BOLD)
        stdscr.addstr(3, 15, site_name)
        
        stdscr.addstr(5, 2, "Parent Site:", curses.A_BOLD)
        stdscr.addstr(5, 15, parent_site)
        
        # Draw field cursor
        cursor_y = 3 if current_field == 0 else 5
        stdscr.addstr(cursor_y, 1, ">")
        
        # Draw footer with instructions
        footer = "UP/DOWN: Navigate | ENTER: Edit field | S: Save | Q: Cancel"
        startx = max(0, (curses.COLS - len(footer)) // 2)
        stdscr.addstr(curses.LINES - 2, startx, footer, curses.A_REVERSE)
        
        # Refresh screen
        stdscr.refresh()
        
        # Get key press
        key = stdscr.getch()
        
        # Handle navigation
        if key == curses.KEY_UP and current_field > 0:
            current_field -= 1
        elif key == curses.KEY_DOWN and current_field < len(form_fields) - 1:
            current_field += 1
        elif key == ord('\n'):  # Enter key
            if current_field == 0:  # Site name field
                site_name = edit_field(stdscr, 3, 15, site_name)
            elif current_field == 1:  # Parent site field
                choice = show_dropdown(stdscr, 6, 15, parent_sites_dropdown, parent_sites_dropdown.index(parent_site))
                if choice >= 0:
                    parent_site = parent_sites_dropdown[choice]
                    parent_id = parent_site_ids.get(parent_site, "global")
                    logger.debug(f"Selected parent site: {parent_site}, ID: {parent_id}")
        elif key == ord('s') or key == ord('S'):  # Save
            # Validate form
            if not site_name:
                show_message(stdscr, "Site name cannot be empty.", curses.A_REVERSE)
                continue
                
            # Confirmation screen
            if show_confirm(stdscr, f"Create {site_type} '{site_name}' under '{parent_site}'?"):
                # Log the attempt
                logger.info(f"Attempting to create {site_type}: {site_name} under parent: {parent_site} (ID: {parent_id})")
                
                # Show spinner while processing
                status_msg = f"Creating {site_type}..."
                startx = max(0, (curses.COLS - len(status_msg) - 2) // 2)
                
                # Create site data
                site_data = create_site_data(site_type, site_name, parent_site, parent_id)
                
                # Show confirmation
                stdscr.clear()
                try:
                    stdscr.addstr(0, 2, "Creating site...")
                    stdscr.refresh()
                    
                    # Show a spinner while creating site
                    spinner_chars = ['|', '/', '-', '\\']
                    spinner_idx = 0
                    
                    def update_spinner():
                        nonlocal spinner_idx
                        try:
                            # Clear previous spinner
                            stdscr.addstr(1, 2, " " * 20)
                            # Show updated spinner with status
                            stdscr.addstr(1, 2, f"Please wait {spinner_chars[spinner_idx]} ")
                            spinner_idx = (spinner_idx + 1) % len(spinner_chars)
                            stdscr.refresh()
                        except curses.error:
                            pass
                    
                    # Setup a timer to update the spinner periodically
                    last_update = 0
                    update_interval = 0.2  # seconds
                except curses.error:
                    pass
                
                try:
                    # Log for debugging
                    logging.debug(f"Creating site of type: {site_type}")
                    logging.debug(f"Site name: {site_name}")
                    logging.debug(f"Parent site: {parent_site}")
                    logging.debug(f"Sending site data: {json.dumps(site_data, indent=2)}")
                    
                    # Create the site using direct API call to avoid path construction issues
                    direct_url = "dna/intent/api/v1/site"
                    
                    # Ensure hostname doesn't have trailing slash and doesn't duplicate protocol
                    base_url = dnac.host.rstrip('/')
                    full_url = f"{base_url}/{direct_url}"
                    
                    headers = {
                        "x-auth-token": dnac.token,
                        "Content-Type": "application/json"
                    }
                    
                    # Convert site_data to JSON string
                    json_data = json.dumps(site_data)
                    logging.debug(f"Full URL: {full_url}")
                    logging.debug(f"Headers: {headers}")
                    logging.debug(f"JSON data: {json_data}")
                    
                    # Make direct request
                    response = dnac.session.post(
                        full_url,
                        headers=headers,
                        data=json_data
                    )
                    logging.debug(f"Direct response status: {response.status_code}")
                    logging.debug(f"Direct response text: {response.text}")
                    
                    # Parse response
                    response_data = response.json()
                    logging.debug(f"Response data: {json.dumps(response_data, indent=2)}")
                    
                    # Check for task ID or execution ID
                    success = False
                    
                    if response.status_code in (200, 201, 202):
                        # For 202 Accepted, we need to monitor for completion
                        if response.status_code == 202:
                            logging.info("Got 202 Accepted response, monitoring for completion...")
                            # Proceed with verification rather than treating as success
                            
                            # Simple wait and verify approach - attempt to find the site
                            max_verification_attempts = 30
                            verification_delay = 3  # seconds
                            for attempt in range(max_verification_attempts):
                                # Update spinner
                                current_time = time.time()
                                if current_time - last_update > update_interval:
                                    update_spinner()
                                    last_update = current_time
                                    
                                logging.info(f"Verification attempt {attempt+1}/{max_verification_attempts}...")
                                
                                # Try to verify the site exists
                                verify_url = f"{base_url}/dna/intent/api/v1/site"
                                verify_response = dnac.session.get(
                                    verify_url, 
                                    headers={"x-auth-token": dnac.token},
                                    timeout=10
                                )
                                
                                site_found = False
                                if verify_response.status_code == 200:
                                    verify_data = verify_response.json()
                                    if 'response' in verify_data and isinstance(verify_data['response'], list):
                                        for site in verify_data['response']:
                                            if site.get('name') == site_name:
                                                logging.info(f"Site '{site_name}' found after {attempt+1} verification attempts!")
                                                site_found = True
                                                success = True
                                                break
                                
                                if site_found:
                                    break
                                    
                                # If not found and not the last attempt, wait and try again
                                if attempt < max_verification_attempts - 1:
                                    logging.info(f"Site not found yet, waiting {verification_delay} seconds...")
                                    time.sleep(verification_delay)
                                    
                            if not success:
                                logging.error(f"Failed to verify site creation after {max_verification_attempts} attempts")
                                raise Exception("Site creation could not be verified within the timeout period")
                            
                        # Only proceed with task/execution monitoring for other success codes
                        elif "response" in response_data and response_data["response"].get("taskId"):
                            task_id = response_data["response"].get("taskId")
                            logging.debug(f"Got task ID: {task_id}")
                            
                            # Monitor task
                            try:
                                task_url = f"{base_url}/dna/intent/api/v1/task/{task_id}"
                                logging.debug(f"Task URL: {task_url}")
                                
                                # Poll for task completion
                                max_retries = 60  # Increase from 30 to 60
                                retry_count = 0
                                start_time = time.time()
                                max_wait_time = 180  # Increase from 60 to 180 seconds (3 minutes)
                                
                                while retry_count < max_retries and (time.time() - start_time) < max_wait_time:
                                    # Update spinner
                                    current_time = time.time()
                                    if current_time - last_update > update_interval:
                                        update_spinner()
                                        last_update = current_time
                                        
                                    try:
                                        task_response = dnac.session.get(
                                            task_url,
                                            headers={"x-auth-token": dnac.token},
                                            timeout=5  # 5 second timeout for each request
                                        )
                                        logging.debug(f"Task poll response status: {task_response.status_code}")
                                        task_data = task_response.json()
                                        logging.debug(f"Task poll data: {json.dumps(task_data, indent=2)}")
                                        
                                        if "response" in task_data:
                                            task_result = task_data["response"]
                                            if task_result.get("isError", False):
                                                error_msg = task_result.get("failureReason", "Unknown task error")
                                                logging.error(f"Task failed: {error_msg}")
                                                raise Exception(f"Task failed: {error_msg}")
                                                
                                            if task_result.get("endTime", None):
                                                logging.debug("Task completed successfully!")
                                                success = True
                                                break
                                        
                                        logging.debug(f"Task still in progress. Retry {retry_count+1}/{max_retries}")
                                        retry_count += 1
                                        time.sleep(2)  # Wait 2 seconds before polling again
                                    except Exception as e:
                                        logging.error(f"Error polling task: {str(e)}")
                                        
                                if not success:
                                    logging.error(f"Task monitoring timed out after {max_retries} attempts")
                                    
                                    # Even if we time out, check if the site was created anyway
                                    try:
                                        logging.debug("Checking if site was created despite timeout...")
                                        verify_url = f"{base_url}/dna/intent/api/v1/site"
                                        verify_response = dnac.session.get(
                                            verify_url, 
                                            headers={"x-auth-token": dnac.token},
                                            timeout=10
                                        )
                                        
                                        if verify_response.status_code == 200:
                                            verify_data = verify_response.json()
                                            if 'response' in verify_data and isinstance(verify_data['response'], list):
                                                for site in verify_data['response']:
                                                    if site.get('name') == site_name:
                                                        logging.info(f"Site {site_name} appears to have been created despite timeout!")
                                                        success = True
                                                        break
                                    except Exception as ve:
                                        logging.error(f"Error during verification after timeout: {str(ve)}")
                                    
                                    if not success:
                                        raise Exception("Task timed out")
                            except Exception as task_error:
                                logging.error(f"Error monitoring task: {str(task_error)}")
                                raise
                        
                        # Handle execution status URL format
                        elif "executionId" in response_data and "executionStatusUrl" in response_data:
                            execution_id = response_data["executionId"]
                            status_path = response_data["executionStatusUrl"]
                            
                            # Create the full URL
                            if status_path.startswith('/'):
                                status_path = status_path[1:]
                            execution_url = f"{base_url}/{status_path}"
                            
                            logging.debug(f"Monitoring execution: {execution_id}")
                            logging.debug(f"Execution status URL: {execution_url}")
                            
                            # Poll for execution completion
                            max_retries = 60  # Increase from 30 to 60
                            retry_count = 0
                            start_time = time.time()
                            max_wait_time = 180  # Increase from 60 to 180 seconds (3 minutes)
                            
                            while retry_count < max_retries and (time.time() - start_time) < max_wait_time:
                                # Update spinner
                                current_time = time.time()
                                if current_time - last_update > update_interval:
                                    update_spinner()
                                    last_update = current_time
                                    
                                try:
                                    exec_response = dnac.session.get(
                                        execution_url,
                                        headers={"x-auth-token": dnac.token},
                                        timeout=5  # 5 second timeout for each request
                                    )
                                    
                                    try:
                                        exec_data = exec_response.json()
                                        logging.debug(f"Execution status (attempt {retry_count+1}): {json.dumps(exec_data, indent=2)}")
                                        
                                        # Check status
                                        status = exec_data.get("status", "").lower()
                                        if status == "failed":
                                            error_msg = exec_data.get("bapiError", "Unknown execution error")
                                            logging.error(f"Execution failed: {error_msg}")
                                            raise Exception(f"Execution failed: {error_msg}")
                                            
                                        if status == "success":
                                            logging.debug("Execution completed successfully!")
                                            success = True
                                            break
                                        
                                        # Still in progress
                                        if status in ["running", "pending"]:
                                            logging.debug(f"Execution still in progress: {status}")
                                    except Exception as e:
                                        logging.error(f"Error parsing execution status: {str(e)}")
                                    
                                    # Wait before polling again
                                    retry_count += 1
                                    time.sleep(2)
                                except Exception as e:
                                    logging.error(f"Error polling execution status: {str(e)}")
                                
                            if not success:
                                logging.error(f"Execution monitoring timed out after {max_retries} attempts")
                                
                                # Even if we time out, check if the site was created anyway
                                try:
                                    logging.debug("Checking if site was created despite timeout...")
                                    verify_url = f"{base_url}/dna/intent/api/v1/site"
                                    verify_response = dnac.session.get(
                                        verify_url, 
                                        headers={"x-auth-token": dnac.token},
                                        timeout=10
                                    )
                                    
                                    if verify_response.status_code == 200:
                                        verify_data = verify_response.json()
                                        if 'response' in verify_data and isinstance(verify_data['response'], list):
                                            for site in verify_data['response']:
                                                if site.get('name') == site_name:
                                                    logging.info(f"Site {site_name} appears to have been created despite timeout!")
                                                    success = True
                                                    break
                                except Exception as ve:
                                    logging.error(f"Error during verification after timeout: {str(ve)}")
                                
                                if not success:
                                    raise Exception("Execution timed out")
                        
                        else:
                            # If no known structure, consider it success anyway
                            logging.debug("No task ID or execution URL found, assuming success")
                            success = True
                     
                    # Final verification - always check if the site exists
                    try:
                        logging.debug("Performing final verification to confirm site creation...")
                        verify_url = f"{base_url}/dna/intent/api/v1/site"
                        verify_response = dnac.session.get(
                            verify_url, 
                            headers={"x-auth-token": dnac.token},
                            timeout=10
                        )
                        
                        site_exists = False
                        if verify_response.status_code == 200:
                            verify_data = verify_response.json()
                            if 'response' in verify_data and isinstance(verify_data['response'], list):
                                for site in verify_data['response']:
                                    if site.get('name') == site_name:
                                        logging.info(f"Final verification: Site {site_name} exists!")
                                        site_exists = True
                                        break
                        
                        if not site_exists:
                            logging.warning(f"Final verification: Site {site_name} NOT found. This indicates a potential failure.")
                            # We've already spent time waiting in the verification loop, so this is likely a real issue
                            success = False
                            raise Exception(f"Site {site_name} was not found in the final verification. Creation appears to have failed.")
                    except Exception as ve:
                        logging.error(f"Error during final verification: {str(ve)}")
                        if "was not found in the final verification" in str(ve):
                            raise  # Re-raise this specific exception
                        # Don't fail the operation due to other verification errors
                    
                    # Display result to user
                    if success:
                        show_message(stdscr, f"{site_type.capitalize()} '{site_name}' created successfully!", curses.A_NORMAL)
                        saved = True
                        break
                    else:
                        show_message(stdscr, f"Failed to create {site_type}. See logs for details.", curses.A_REVERSE)
                except Exception as e:
                    logging.error(f"Error creating site: {str(e)}")
                    show_message(stdscr, f"Error: {str(e)}", curses.A_REVERSE)
            else:
                # User cancelled the confirmation
                pass
        elif key == ord('q') or key == ord('Q'):  # Cancel
            if not saved and site_name:
                if show_confirm(stdscr, "Discard changes?"):
                    return False
            else:
                return False
    
    return saved


def add_site_ui(stdscr, args):
    """Main UI function for adding a site."""
    # Get screen dimensions
    h, w = stdscr.getmaxyx()
    
    try:
        # Load configuration
        config = load_config(args.config)
        
        # Extract nested configuration values
        server_config = config.get("server", {})
        hostname = server_config.get("host")
        verify = server_config.get("verify_ssl", False)
        
        auth_config = config.get("auth", {})
        username = auth_config.get("username")
        password = auth_config.get("password")
        
        if not all([hostname, username, password]):
            raise ValueError("Missing required configuration: hostname, username, or password")
        
        # Initialize DNAC client
        dnac = Dnac(hostname)
        dnac.verify = verify
        
        # Show loading screen
        stdscr.clear()
        try:
            stdscr.addstr(0, 2, "Connecting to DNAC...")
            stdscr.refresh()
        except curses.error:
            pass
        
        # Login and get token
        dnac.login(username, password)
        
        # Step 1: Select site type
        site_types = [
            {"name": "Area", "value": "area"},
            {"name": "Building", "value": "building"},
            {"name": "Floor", "value": "floor"}
        ]
        
        stdscr.clear()
        try:
            stdscr.addstr(0, 2, "Select site type:")
            stdscr.refresh()
        except curses.error:
            pass
        
        selected_type = show_dropdown_menu(stdscr, [t["name"] for t in site_types], 1, 2)
        if selected_type is None:
            return
        
        site_type = site_types[selected_type]["value"]
        
        # Step 2: Get site name
        site_name = get_site_name(stdscr)
        if not site_name:
            stdscr.clear()
            try:
                stdscr.addstr(0, 2, "Site name is required. Press any key to return.")
                stdscr.refresh()
                stdscr.getch()
            except curses.error:
                pass
            return
        
        # Step 3: Select parent site
        stdscr.clear()
        try:
            stdscr.addstr(0, 2, "Fetching available parent sites...")
            stdscr.refresh()
        except curses.error:
            pass
        
        parent_sites = get_parent_sites(dnac)
        if parent_sites:
            stdscr.clear()
            try:
                stdscr.addstr(0, 2, "Select parent site (optional):")
                stdscr.refresh()
            except curses.error:
                pass
            
            # Create list of site names for display
            site_names = ["None (Global)"]
            for site in parent_sites:
                site_names.append(site.get("name", "Unknown"))
            
            selected_parent = show_dropdown_menu(stdscr, site_names, 1, 2)
            if selected_parent is None:
                return
            # If "None (Global)" is selected (index 0), use None as parent
            parent_site = None if selected_parent == 0 else parent_sites[selected_parent - 1]["name"]
            parent_id = None if selected_parent == 0 else parent_sites[selected_parent - 1]["id"]
            
            # Log the selected parent site details
            if parent_site:
                logging.debug(f"Selected parent site: {parent_site} (ID: {parent_id})")
            else:
                logging.debug("No parent site selected, using Global")
        else:
            parent_site = None
            parent_id = None
        
        # Create site data
        site_data = create_site_data(site_type, site_name, parent_site, parent_id)
        
        # Show confirmation
        stdscr.clear()
        try:
            stdscr.addstr(0, 2, "Confirm site creation:")
            stdscr.addstr(1, 4, f"Type: {site_type.title()}")
            stdscr.addstr(2, 4, f"Name: {site_name}")
            stdscr.addstr(3, 4, f"Parent: {parent_site if parent_site else 'Global'}")
            stdscr.addstr(5, 2, "Press 'y' to confirm, any other key to cancel:")
            stdscr.refresh()
        except curses.error:
            pass
        
        if stdscr.getch() != ord('y'):
            return
        
        # Create site
        stdscr.clear()
        try:
            stdscr.addstr(0, 2, "Creating site...")
            stdscr.refresh()
            
            # Show a spinner while creating site
            spinner_chars = ['|', '/', '-', '\\']
            spinner_idx = 0
            
            def update_spinner():
                nonlocal spinner_idx
                try:
                    # Clear previous spinner
                    stdscr.addstr(1, 2, " " * 20)
                    # Show updated spinner with status
                    stdscr.addstr(1, 2, f"Please wait {spinner_chars[spinner_idx]} ")
                    spinner_idx = (spinner_idx + 1) % len(spinner_chars)
                    stdscr.refresh()
                except curses.error:
                    pass
            
            # Setup a timer to update the spinner periodically
            last_update = 0
            update_interval = 0.2  # seconds
        except curses.error:
            pass
        
        try:
            # Log for debugging
            logging.debug(f"Creating site of type: {site_type}")
            logging.debug(f"Site name: {site_name}")
            logging.debug(f"Parent site: {parent_site}")
            logging.debug(f"Sending site data: {json.dumps(site_data, indent=2)}")
            
            # Create the site using direct API call to avoid path construction issues
            direct_url = "dna/intent/api/v1/site"
            
            # Ensure hostname doesn't have trailing slash and doesn't duplicate protocol
            base_url = dnac.host.rstrip('/')
            full_url = f"{base_url}/{direct_url}"
            
            headers = {
                "x-auth-token": dnac.token,
                "Content-Type": "application/json"
            }
            
            # Convert site_data to JSON string
            json_data = json.dumps(site_data)
            logging.debug(f"Full URL: {full_url}")
            logging.debug(f"Headers: {headers}")
            logging.debug(f"JSON data: {json_data}")
            
            # Make direct request
            response = dnac.session.post(
                full_url,
                headers=headers,
                data=json_data
            )
            logging.debug(f"Direct response status: {response.status_code}")
            logging.debug(f"Direct response text: {response.text}")
            
            # Parse response
            response_data = response.json()
            logging.debug(f"Response data: {json.dumps(response_data, indent=2)}")
            
            # Check for task ID or execution ID
            success = False
            
            if response.status_code in (200, 201, 202):
                # For 202 Accepted, we need to monitor for completion
                if response.status_code == 202:
                    logging.info("Got 202 Accepted response, monitoring for completion...")
                    # Proceed with verification rather than treating as success
                    
                    # Simple wait and verify approach - attempt to find the site
                    max_verification_attempts = 30
                    verification_delay = 3  # seconds
                    for attempt in range(max_verification_attempts):
                        # Update spinner
                        current_time = time.time()
                        if current_time - last_update > update_interval:
                            update_spinner()
                            last_update = current_time
                            
                        logging.info(f"Verification attempt {attempt+1}/{max_verification_attempts}...")
                        
                        # Try to verify the site exists
                        verify_url = f"{base_url}/dna/intent/api/v1/site"
                        verify_response = dnac.session.get(
                            verify_url, 
                            headers={"x-auth-token": dnac.token},
                            timeout=10
                        )
                        
                        site_found = False
                        if verify_response.status_code == 200:
                            verify_data = verify_response.json()
                            if 'response' in verify_data and isinstance(verify_data['response'], list):
                                for site in verify_data['response']:
                                    if site.get('name') == site_name:
                                        logging.info(f"Site '{site_name}' found after {attempt+1} verification attempts!")
                                        site_found = True
                                        success = True
                                        break
                        
                        if site_found:
                            break
                            
                        # If not found and not the last attempt, wait and try again
                        if attempt < max_verification_attempts - 1:
                            logging.info(f"Site not found yet, waiting {verification_delay} seconds...")
                            time.sleep(verification_delay)
                            
                    if not success:
                        logging.error(f"Failed to verify site creation after {max_verification_attempts} attempts")
                        raise Exception("Site creation could not be verified within the timeout period")
                        
                # Only proceed with task/execution monitoring for other success codes
                elif "response" in response_data and response_data["response"].get("taskId"):
                    task_id = response_data["response"].get("taskId")
                    logging.debug(f"Got task ID: {task_id}")
                    
                    # Monitor task
                    try:
                        task_url = f"{base_url}/dna/intent/api/v1/task/{task_id}"
                        logging.debug(f"Task URL: {task_url}")
                        
                        # Poll for task completion
                        max_retries = 60  # Increase from 30 to 60
                        retry_count = 0
                        start_time = time.time()
                        max_wait_time = 180  # Increase from 60 to 180 seconds (3 minutes)
                        
                        while retry_count < max_retries and (time.time() - start_time) < max_wait_time:
                            # Update spinner
                            current_time = time.time()
                            if current_time - last_update > update_interval:
                                update_spinner()
                                last_update = current_time
                                
                            try:
                                task_response = dnac.session.get(
                                    task_url,
                                    headers={"x-auth-token": dnac.token},
                                    timeout=5  # 5 second timeout for each request
                                )
                                logging.debug(f"Task poll response status: {task_response.status_code}")
                                task_data = task_response.json()
                                logging.debug(f"Task poll data: {json.dumps(task_data, indent=2)}")
                                
                                if "response" in task_data:
                                    task_result = task_data["response"]
                                    if task_result.get("isError", False):
                                        error_msg = task_result.get("failureReason", "Unknown task error")
                                        logging.error(f"Task failed: {error_msg}")
                                        raise Exception(f"Task failed: {error_msg}")
                                        
                                    if task_result.get("endTime", None):
                                        logging.debug("Task completed successfully!")
                                        success = True
                                        break
                                
                                logging.debug(f"Task still in progress. Retry {retry_count+1}/{max_retries}")
                                retry_count += 1
                                time.sleep(2)  # Wait 2 seconds before polling again
                            except Exception as e:
                                logging.error(f"Error polling task: {str(e)}")
                                
                        if not success:
                            logging.error(f"Task monitoring timed out after {max_retries} attempts")
                            
                            # Even if we time out, check if the site was created anyway
                            try:
                                logging.debug("Checking if site was created despite timeout...")
                                verify_url = f"{base_url}/dna/intent/api/v1/site"
                                verify_response = dnac.session.get(
                                    verify_url, 
                                    headers={"x-auth-token": dnac.token},
                                    timeout=10
                                )
                                
                                if verify_response.status_code == 200:
                                    verify_data = verify_response.json()
                                    if 'response' in verify_data and isinstance(verify_data['response'], list):
                                        for site in verify_data['response']:
                                            if site.get('name') == site_name:
                                                logging.info(f"Site {site_name} appears to have been created despite timeout!")
                                                success = True
                                                break
                            except Exception as ve:
                                logging.error(f"Error during verification after timeout: {str(ve)}")
                            
                            if not success:
                                raise Exception("Task timed out")
                    except Exception as task_error:
                        logging.error(f"Error monitoring task: {str(task_error)}")
                        raise
                
                # Handle execution status URL format
                elif "executionId" in response_data and "executionStatusUrl" in response_data:
                    execution_id = response_data["executionId"]
                    status_path = response_data["executionStatusUrl"]
                    
                    # Create the full URL
                    if status_path.startswith('/'):
                        status_path = status_path[1:]
                    execution_url = f"{base_url}/{status_path}"
                    
                    logging.debug(f"Monitoring execution: {execution_id}")
                    logging.debug(f"Execution status URL: {execution_url}")
                    
                    # Poll for execution completion
                    max_retries = 60  # Increase from 30 to 60
                    retry_count = 0
                    start_time = time.time()
                    max_wait_time = 180  # Increase from 60 to 180 seconds (3 minutes)
                    
                    while retry_count < max_retries and (time.time() - start_time) < max_wait_time:
                        # Update spinner
                        current_time = time.time()
                        if current_time - last_update > update_interval:
                            update_spinner()
                            last_update = current_time
                            
                        try:
                            exec_response = dnac.session.get(
                                execution_url,
                                headers={"x-auth-token": dnac.token},
                                timeout=5  # 5 second timeout for each request
                            )
                            
                            try:
                                exec_data = exec_response.json()
                                logging.debug(f"Execution status (attempt {retry_count+1}): {json.dumps(exec_data, indent=2)}")
                                
                                # Check status
                                status = exec_data.get("status", "").lower()
                                if status == "failed":
                                    error_msg = exec_data.get("bapiError", "Unknown execution error")
                                    logging.error(f"Execution failed: {error_msg}")
                                    raise Exception(f"Execution failed: {error_msg}")
                                    
                                if status == "success":
                                    logging.debug("Execution completed successfully!")
                                    success = True
                                    break
                                
                                # Still in progress
                                if status in ["running", "pending"]:
                                    logging.debug(f"Execution still in progress: {status}")
                            except Exception as e:
                                logging.error(f"Error parsing execution status: {str(e)}")
                            
                            # Wait before polling again
                            retry_count += 1
                            time.sleep(2)
                        except Exception as e:
                            logging.error(f"Error polling execution status: {str(e)}")
                        
                    if not success:
                        logging.error(f"Execution monitoring timed out after {max_retries} attempts")
                        
                        # Even if we time out, check if the site was created anyway
                        try:
                            logging.debug("Checking if site was created despite timeout...")
                            verify_url = f"{base_url}/dna/intent/api/v1/site"
                            verify_response = dnac.session.get(
                                verify_url, 
                                headers={"x-auth-token": dnac.token},
                                timeout=10
                            )
                            
                            if verify_response.status_code == 200:
                                verify_data = verify_response.json()
                                if 'response' in verify_data and isinstance(verify_data['response'], list):
                                    for site in verify_data['response']:
                                        if site.get('name') == site_name:
                                            logging.info(f"Site {site_name} appears to have been created despite timeout!")
                                            success = True
                                            break
                        except Exception as ve:
                            logging.error(f"Error during verification after timeout: {str(ve)}")
                        
                        if not success:
                            raise Exception("Execution timed out")
                
                else:
                    # Direct success response
                    logging.debug("API call succeeded but no task ID or execution ID found")
                    success = True
            
            if not success:
                error_msg = response_data.get('detail', response.text)
                logging.error(f"API Error: {error_msg}")
                raise Exception(f"API Error: {error_msg}")
            
            # Final verification - always check if the site exists
            try:
                logging.debug("Performing final verification to confirm site creation...")
                verify_url = f"{base_url}/dna/intent/api/v1/site"
                verify_response = dnac.session.get(
                    verify_url, 
                    headers={"x-auth-token": dnac.token},
                    timeout=10
                )
                
                site_exists = False
                if verify_response.status_code == 200:
                    verify_data = verify_response.json()
                    if 'response' in verify_data and isinstance(verify_data['response'], list):
                        for site in verify_data['response']:
                            if site.get('name') == site_name:
                                logging.info(f"Final verification: Site {site_name} exists!")
                                site_exists = True
                                break
                
                if not site_exists:
                    logging.warning(f"Final verification: Site {site_name} NOT found. This indicates a potential failure.")
                    # We've already spent time waiting in the verification loop, so this is likely a real issue
                    success = False
                    raise Exception(f"Site {site_name} was not found in the final verification. Creation appears to have failed.")
            except Exception as ve:
                logging.error(f"Error during final verification: {str(ve)}")
                if "was not found in the final verification" in str(ve):
                    raise  # Re-raise this specific exception
                # Don't fail the operation due to other verification errors
            
        except Exception as e:
            logging.error(f"Exception during API call: {str(e)}")
            raise
        
        # If we get here, the site was created successfully
        stdscr.clear()
        logging.info(f"Successfully created site: {site_name} of type {site_type}")
        try:
            stdscr.addstr(0, 2, "Site created successfully!")
            
            # Show site hierarchy
            stdscr.addstr(2, 2, "Current Site Hierarchy:")
            stdscr.refresh()
            
            # Fetch the updated hierarchy
            try:
                hierarchy_response = dnac.get("site", ver="v1")
                if hasattr(hierarchy_response, 'response') and hasattr(hierarchy_response.response, 'json'):
                    sites_data = hierarchy_response.response.json()
                    
                    # Handle response format
                    if isinstance(sites_data, dict) and 'response' in sites_data:
                        sites_data = sites_data['response']
                    
                    # Display sites hierarchy
                    if isinstance(sites_data, list):
                        # Start at line 4 to leave space for the header
                        current_line = 4
                        # Display "Global" as the root
                        stdscr.addstr(current_line, 4, "Global")
                        current_line += 1
                        
                        # Sort sites by name for better readability
                        sites_data.sort(key=lambda x: x.get('name', ''))
                        
                        # Store the newly created site details for comparison
                        new_site_name = site_name  # This is from our form input
                        new_site_type = site_type  # This is from our form input
                        
                        # Display each site with proper indentation
                        for site in sites_data:
                            curr_site_name = site.get('name', 'Unknown')
                            curr_site_type = "Unknown"
                            
                            # Determine site type
                            if "area" in str(site.get('additionalInfo', {})):
                                curr_site_type = "Area"
                            elif "building" in str(site.get('additionalInfo', {})):
                                curr_site_type = "Building"
                            elif "floor" in str(site.get('additionalInfo', {})):
                                curr_site_type = "Floor"
                            
                            # Display with indentation based on type
                            indent = 6  # Default indent for sites
                            prefix = "├─ "  # Default prefix for tree structure
                            
                            site_str = f"{prefix}{curr_site_name} ({curr_site_type})"
                            
                            # Highlight if this is the newly created site (case-insensitive comparison)
                            is_new_site = (curr_site_name.lower() == new_site_name.lower() and 
                                          curr_site_type.lower()[0] == new_site_type[0])  # Compare first letter
                            
                            if is_new_site:
                                try:
                                    stdscr.attron(curses.A_BOLD | curses.A_REVERSE)
                                    stdscr.addstr(current_line, indent, site_str)
                                    stdscr.addstr(current_line, indent + len(site_str) + 1, " <- NEW")
                                    stdscr.attroff(curses.A_BOLD | curses.A_REVERSE)
                                except curses.error:
                                    # Fallback if highlighting fails
                                    try:
                                        stdscr.addstr(current_line, indent, site_str + " (NEW)")
                                    except curses.error:
                                        pass
                            else:
                                try:
                                    stdscr.addstr(current_line, indent, site_str)
                                except curses.error:
                                    pass
                            
                            current_line += 1
                            
                            # Check if we're at the bottom of the screen
                            if current_line >= h - 3:
                                try:
                                    stdscr.addstr(current_line, 4, "... (more sites not shown)")
                                    current_line += 1
                                except curses.error:
                                    pass
                                break
                    else:
                        stdscr.addstr(4, 4, "Unable to fetch hierarchy data")
                else:
                    stdscr.addstr(4, 4, "Unable to fetch hierarchy data")
            except Exception as e:
                stdscr.addstr(4, 4, f"Error fetching hierarchy: {str(e)[:w-20]}")
            
            # Add navigation instructions at the bottom
            stdscr.addstr(h-2, 2, "Press any key to return to the menu...")
            stdscr.refresh()
        except curses.error:
            pass
        stdscr.getch()
    except Exception as e:
        stdscr.clear()
        try:
            error_msg = f"Error creating site: {str(e)[:w-4]}"
            stdscr.addstr(0, 2, error_msg)
            stdscr.addstr(1, 2, "Press any key to continue...")
            stdscr.refresh()
        except curses.error:
            pass
        stdscr.getch()


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="Add a new site to Cisco Catalyst Centre")
    parser.add_argument("-c", "--config", help=f"Config file (default: {DEFAULT_CONFIG_FILE})")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--from-menu", action="store_true", help="Indicates script is being run from the menu")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("urllib3.connectionpool").setLevel(logging.DEBUG)

    # Always use curses wrapper - the menu.py will handle proper curses cleanup/restore
    curses.wrapper(add_site_ui, args)


if __name__ == "__main__":
    main() 