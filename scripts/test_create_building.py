#!/usr/bin/env python3
"""
Test script to create a building directly in Cisco Catalyst Centre using API calls.
This bypasses the curses UI to simplify debugging.
"""

import os
import sys
import argparse
import logging
import yaml
import json
import requests
import time
from urllib3.exceptions import InsecureRequestWarning

# Suppress insecure HTTPS warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Configure logging to file and console
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
    handlers=[
        logging.FileHandler("dnac_test_building.log"),
        logging.StreamHandler()
    ]
)

DEFAULT_CONFIG_FILE = "config.yaml"

def load_config(config_file=None):
    """Load configuration from file."""
    if config_file is None:
        config_file = DEFAULT_CONFIG_FILE

    if not os.path.exists(config_file):
        print(f"Config file {config_file} not found")
        sys.exit(1)

    with open(config_file) as f:
        return yaml.safe_load(f)

def create_building(hostname, token, building_name, parent_name="Global"):
    """Create a building using direct API calls."""
    
    # Create site data for building
    site_data = {
        "type": "building",
        "site": {
            "building": {
                "name": building_name,
                "parentName": parent_name,
                "address": "123 Example Street",
                "latitude": 37.409,
                "longitude": -121.965,
                "country": "United States",
                "state": "California",
                "city": "San Jose",
                "zipCode": "95123"
            }
        }
    }
    
    # Print site data for verification
    logging.info(f"Site data: {json.dumps(site_data, indent=2)}")
    
    # Ensure hostname doesn't have trailing slash and doesn't duplicate protocol
    hostname = hostname.rstrip('/')
    if hostname.startswith('http'):
        base_url = hostname
    else:
        base_url = f"https://{hostname}"
    
    # Create building
    url = f"{base_url}/dna/intent/api/v1/site"
    headers = {
        "x-auth-token": token,
        "Content-Type": "application/json"
    }
    
    logging.info(f"Making API call to: {url}")
    logging.info(f"Headers: {headers}")
    
    response = requests.post(
        url,
        headers=headers,
        json=site_data,
        verify=False
    )
    
    logging.info(f"Response status code: {response.status_code}")
    
    try:
        # Parse response
        response_data = response.json()
        logging.info(f"Response data: {json.dumps(response_data, indent=2)}")
        
        # Process response based on status code
        if response.status_code in (200, 201, 202):
            # For 202 Accepted, we need to verify the site was actually created
            if response.status_code == 202:
                logging.info("Got 202 Accepted response, starting verification process...")
                
                # Implement a retry mechanism to verify the site exists
                max_retries = 30
                retry_delay = 3  # seconds
                for attempt in range(max_retries):
                    logging.info(f"Verification attempt {attempt+1}/{max_retries}...")
                    
                    # Check if site exists
                    if verify_building_exists(hostname, token, building_name):
                        logging.info(f"Site {building_name} found after {attempt+1} verification attempts!")
                        return True
                    
                    # If not found and not the last attempt, wait and try again
                    if attempt < max_retries - 1:
                        logging.info(f"Site not found yet, waiting {retry_delay} seconds...")
                        time.sleep(retry_delay)
                
                # If we've exhausted all retries
                logging.error(f"Failed to verify site creation after {max_retries} attempts")
                return False
            
            # Handle the execution status URL format
            elif "executionId" in response_data and "executionStatusUrl" in response_data:
                execution_id = response_data["executionId"]
                status_path = response_data["executionStatusUrl"]
                
                # Create the full URL
                if status_path.startswith('/'):
                    status_path = status_path[1:]
                execution_url = f"{base_url}/{status_path}"
                
                logging.info(f"Monitoring execution: {execution_id}")
                logging.info(f"Execution status URL: {execution_url}")
                
                # Poll for execution completion
                max_retries = 30
                for attempt in range(max_retries):
                    exec_response = requests.get(
                        execution_url,
                        headers={"x-auth-token": token},
                        verify=False
                    )
                    
                    try:
                        exec_data = exec_response.json()
                        logging.info(f"Execution status (attempt {attempt+1}): {json.dumps(exec_data, indent=2)}")
                        
                        # Check status
                        status = exec_data.get("status", "").lower()
                        if status == "failed":
                            error_msg = exec_data.get("bapiError", "Unknown execution error")
                            logging.error(f"Execution failed: {error_msg}")
                            return False
                        
                        if status == "success":
                            logging.info("Execution completed successfully!")
                            return True
                        
                        # Still in progress
                        if status in ["running", "pending"]:
                            logging.info(f"Execution still in progress: {status}")
                    except Exception as e:
                        logging.error(f"Error parsing execution status: {str(e)}")
                    
                    # Wait before polling again
                    time.sleep(2)
                
                logging.error(f"Execution monitoring timed out after {max_retries} attempts")
                return False
            
            else:
                # Direct success response
                logging.info("API call succeeded but no task ID or execution ID found")
                return True
        
        logging.error(f"API call failed with status code {response.status_code}")
        return False
    except Exception as e:
        logging.error(f"Error processing response: {str(e)}")
        return False

def verify_building_exists(hostname, token, building_name):
    """Verify if a building exists by fetching the site list."""
    # Ensure hostname doesn't have trailing slash and doesn't duplicate protocol
    hostname = hostname.rstrip('/')
    if hostname.startswith('http'):
        base_url = hostname
    else:
        base_url = f"https://{hostname}"
    
    url = f"{base_url}/dna/intent/api/v1/site"
    headers = {"x-auth-token": token}
    
    logging.info(f"Verifying building existence: {building_name}")
    
    try:
        response = requests.get(url, headers=headers, verify=False)
        if response.status_code == 200:
            data = response.json()
            if "response" in data and isinstance(data["response"], list):
                sites = data["response"]
                for site in sites:
                    if site.get("name") == building_name:
                        logging.info(f"Building found: {json.dumps(site, indent=2)}")
                        return True
                
                logging.warning(f"Building not found: {building_name}")
                return False
        
        logging.error(f"Error fetching sites: {response.status_code} {response.text}")
        return False
    except Exception as e:
        logging.error(f"Error verifying building: {str(e)}")
        return False

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test creating a building in Cisco Catalyst Centre")
    parser.add_argument("-c", "--config", help=f"Config file (default: {DEFAULT_CONFIG_FILE})")
    parser.add_argument("-n", "--name", default="TestBuilding", help="Building name")
    parser.add_argument("-p", "--parent", default="Global", help="Parent site name")
    args = parser.parse_args()
    
    try:
        # Load configuration
        config = load_config(args.config)
        
        # Extract config values
        server_config = config.get("server", {})
        hostname = server_config.get("host")
        
        auth_config = config.get("auth", {})
        username = auth_config.get("username")
        password = auth_config.get("password")
        
        if not all([hostname, username, password]):
            logging.error("Missing required configuration: hostname, username, or password")
            return
        
        # Ensure hostname doesn't have trailing slash and doesn't duplicate protocol
        hostname = hostname.rstrip('/')
        if hostname.startswith('http'):
            base_url = hostname
        else:
            base_url = f"https://{hostname}"
        
        # Get authentication token
        logging.info(f"Connecting to DNAC: {hostname}")
        auth_url = f"{base_url}/dna/system/api/v1/auth/token"
        
        try:
            auth_response = requests.post(
                auth_url,
                auth=(username, password),
                verify=False
            )
            
            if auth_response.status_code != 200:
                logging.error(f"Authentication failed: {auth_response.status_code} {auth_response.text}")
                return
            
            token = auth_response.json().get("Token")
            logging.info("Authentication successful")
            
            # Create building
            building_name = args.name
            parent_name = args.parent
            
            logging.info(f"Creating building: {building_name} with parent: {parent_name}")
            result = create_building(hostname, token, building_name, parent_name)
            
            if result:
                logging.info(f"Building creation and verification succeeded")
            else:
                logging.error("Building creation or verification failed")
            
        except Exception as e:
            logging.error(f"Error: {str(e)}")
    
    except Exception as e:
        logging.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 