#!/usr/bin/env python3
"""
Creates a building under UK using the correct hierarchical path format.
Based on the diagnostic results showing Global/Europe/UK is the working format.
"""

import os
import sys
import json
import logging
import requests
import yaml
import argparse

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='uk_building_fixed.log',
    filemode='w'
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

def get_auth_token(host, username, password, verify=False):
    """Get DNAC authentication token"""
    url = f"{host.rstrip('/')}/dna/system/api/v1/auth/token"
    session = requests.Session()
    session.verify = verify
    
    try:
        response = session.post(
            url,
            auth=(username, password),
            verify=verify
        )
        response.raise_for_status()
        token = response.json()["Token"]
        logging.info("Successfully obtained authentication token")
        return token, session
    except Exception as e:
        logging.error(f"Failed to get auth token: {str(e)}")
        raise

def get_config():
    """Load configuration from config.yaml"""
    try:
        with open("config.yaml", 'r') as f:
            config_data = yaml.safe_load(f)
            
        # Extract from server/auth format
        if 'server' in config_data and 'auth' in config_data:
            config = {
                'host': config_data.get('server', {}).get('host'),
                'username': config_data.get('auth', {}).get('username'),
                'password': config_data.get('auth', {}).get('password'),
                'verify': False
            }
            return config
        else:
            logging.error("Unexpected config format")
            return None
    except Exception as e:
        logging.error(f"Error loading config: {str(e)}")
        return None

def get_uk_site_id(host, session, token):
    """Get UK site ID using the correct hierarchical format"""
    url = f"{host.rstrip('/')}/dna/intent/api/v1/site?name=Global/Europe/UK"
    
    try:
        response = session.get(
            url,
            headers={"x-auth-token": token}
        )
        response.raise_for_status()
        data = response.json()
        
        if 'response' in data and data['response']:
            # Handle both list and dict response formats
            if isinstance(data['response'], list) and data['response']:
                uk_site = data['response'][0]
                uk_id = uk_site.get('id')
                uk_name = uk_site.get('name')
                logging.info(f"Found UK site: {uk_name} (ID: {uk_id})")
                print(f"Found UK site: {uk_name} (ID: {uk_id})")
                return uk_id
            elif isinstance(data['response'], dict):
                uk_id = data['response'].get('id')
                uk_name = data['response'].get('name')
                logging.info(f"Found UK site: {uk_name} (ID: {uk_id})")
                print(f"Found UK site: {uk_name} (ID: {uk_id})")
                return uk_id
        
        logging.error("UK site not found in response")
        print("ERROR: UK site not found in response")
        print(json.dumps(data, indent=2))
        return None
    except Exception as e:
        logging.error(f"Error getting UK site ID: {str(e)}")
        print(f"ERROR: Failed to get UK site ID: {str(e)}")
        return None

def create_building(host, session, token, building_name, uk_id):
    """Create a building under UK with the correct parent ID format"""
    url = f"{host.rstrip('/')}/dna/intent/api/v1/site"
    
    # Create building payload with the correct format
    payload = {
        "type": "building",
        "site": {
            "building": {
                "name": building_name,
                "parentId": uk_id,
                "address": "1 Main Street",
                "latitude": 51.50853,
                "longitude": -0.12574,
                "country": "United Kingdom"
            }
        }
    }
    
    logging.info(f"Creating building '{building_name}' under UK (ID: {uk_id})")
    logging.debug(f"Payload: {json.dumps(payload, indent=2)}")
    print(f"Creating building '{building_name}' under UK...")
    
    try:
        response = session.post(
            url,
            headers={
                "x-auth-token": token,
                "Content-Type": "application/json"
            },
            json=payload
        )
        
        logging.info(f"Response status: {response.status_code}")
        logging.debug(f"Response: {response.text}")
        
        if response.status_code in (200, 201, 202):
            print(f"SUCCESS! Building creation initiated with status {response.status_code}")
            
            try:
                resp_data = response.json()
                logging.debug(f"JSON Response: {json.dumps(resp_data, indent=2)}")
                
                if 'executionId' in resp_data:
                    exec_id = resp_data['executionId']
                    print(f"Execution ID: {exec_id}")
                    logging.info(f"Execution ID: {exec_id}")
            except:
                pass
                
            return True
        else:
            print(f"ERROR: Failed to create building, status {response.status_code}")
            print(f"Response: {response.text}")
            logging.error(f"Failed to create building: {response.text}")
            return False
    except Exception as e:
        logging.error(f"Error creating building: {str(e)}")
        print(f"ERROR: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Create a building under UK in DNA Center")
    parser.add_argument("-n", "--name", required=True, help="Building name")
    args = parser.parse_args()
    
    # Load config
    config = get_config()
    if not config:
        print("ERROR: Failed to load configuration")
        return 1
    
    try:
        # Get auth token
        token, session = get_auth_token(
            config['host'],
            config['username'],
            config['password'],
            config.get('verify', False)
        )
        
        # Get UK site ID
        uk_id = get_uk_site_id(config['host'], session, token)
        if not uk_id:
            print("ERROR: Failed to get UK site ID")
            return 1
        
        # Create building
        success = create_building(
            config['host'],
            session,
            token,
            args.name,
            uk_id
        )
        
        if success:
            print("\nBuilding creation process initiated successfully!")
            print("Check the DNA Center UI to verify the building was created.")
        else:
            print("\nFailed to create building.")
        
        return 0 if success else 1
    
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        print(f"ERROR: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 