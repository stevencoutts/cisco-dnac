#!/usr/bin/env python
"""List network devices from Cisco Catalyst Centre."""

import json
import os
import sys
import argparse
import logging
import yaml
from typing import Dict, Any, Optional, List

import dna

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s"
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


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="List network devices from Cisco Catalyst Centre")
    parser.add_argument("-c", "--config", help=f"Config file (default: {DEFAULT_CONFIG_FILE})")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("urllib3.connectionpool").setLevel(logging.DEBUG)

    # Load configuration
    config = load_config(args.config)
    
    # Extract nested configuration values
    server_config = config.get("server", {})
    hostname = server_config.get("host")
    port = server_config.get("port")
    verify = server_config.get("verify_ssl", False)
    
    auth_config = config.get("auth", {})
    username = auth_config.get("username")
    password = auth_config.get("password")
    
    if not all([hostname, username, password]):
        print("Missing required configuration: hostname, username, or password")
        sys.exit(1)
    
    # Initialize DNAC client
    dnac = dna.Dnac(hostname)
    
    # Set SSL verification
    dnac.verify = verify

    try:
        # Login and get token
        dnac.login(username, password)
        print("Successfully authenticated")
        
        # Get network devices
        print("\nFetching network devices...")
        devices_response = dnac.get("dna/intent/api/v1/network-device")
        
        # Display devices
        fmt = "{:20} {:16} {:20} {:16} {:12} {:10}"
        print("\nNetwork Devices:")
        print(fmt.format("Hostname", "Management IP", "Platform", "Serial", "SW Version", "Status"))
        print("-" * 100)
        
        device_count = 0
        try:
            if hasattr(devices_response, 'json') and callable(devices_response.json):
                devices_data = devices_response.json()
                
                # Check if response is a string or dict/list
                if isinstance(devices_data, (dict, list)):
                    # If it's a dict, it might have a 'response' key with the actual data
                    if isinstance(devices_data, dict) and 'response' in devices_data:
                        devices_data = devices_data['response']
                    
                    device_count = len(devices_data)
                    
                    for device in devices_data:
                        try:
                            print(fmt.format(
                                str(device.get('hostname', 'N/A'))[:20],
                                str(device.get('managementIpAddress', 'N/A'))[:16],
                                str(device.get('platformId', 'N/A'))[:20], 
                                str(device.get('serialNumber', 'N/A'))[:16],
                                str(device.get('softwareVersion', 'N/A'))[:12],
                                str(device.get('reachabilityStatus', 'N/A'))[:10]
                            ))
                        except Exception as e:
                            print(f"Error processing device: {e}")
                            print(f"Device data: {repr(device)[:100]}")
                else:
                    print(f"Unexpected response format: {type(devices_data)}")
                    print(f"Response: {repr(devices_data)[:100]}")
        except Exception as e:
            print(f"Error processing devices: {e}")
            
        print("-" * 100)
        print(f"Total devices: {device_count}")
        
        # Get more detailed information about devices
        print("\nDetailed Device Information:")
        if device_count > 0:
            # Get the first device ID for detailed info
            device_id = None
            if isinstance(devices_data, list) and len(devices_data) > 0:
                device_id = devices_data[0].get('id')
                
            if device_id:
                print(f"\nFetching details for device: {devices_data[0].get('hostname')}")
                try:
                    device_details = dnac.get(f"dna/intent/api/v1/network-device/{device_id}")
                    if hasattr(device_details, 'json') and callable(device_details.json):
                        details = device_details.json()
                        
                        # Handle response being inside 'response' key
                        if isinstance(details, dict) and 'response' in details:
                            details = details['response']
                            
                        print(f"Location: {details.get('location', 'N/A')}")
                        print(f"Uptime: {details.get('upTime', 'N/A')}")
                        print(f"Last Updated: {details.get('lastUpdateTime', 'N/A')}")
                        print(f"Role: {details.get('role', 'N/A')}")
                        
                        # Print interfaces if available
                        print("\nInterfaces:")
                        try:
                            interfaces = dnac.get(f"dna/intent/api/v1/interface/network-device/{device_id}")
                            if hasattr(interfaces, 'json') and callable(interfaces.json):
                                interfaces_data = interfaces.json()
                                
                                # Handle response being inside 'response' key
                                if isinstance(interfaces_data, dict) and 'response' in interfaces_data:
                                    interfaces_data = interfaces_data['response']
                                
                                interface_fmt = "{:30} {:15} {:10} {:10}"
                                print(interface_fmt.format("Name", "IP Address", "Status", "Speed"))
                                print("-" * 70)
                                
                                # Get first 5 interfaces or fewer if less are available
                                interfaces_to_show = interfaces_data[:5] if isinstance(interfaces_data, list) else []
                                
                                for interface in interfaces_to_show:
                                    print(interface_fmt.format(
                                        str(interface.get('portName', 'N/A'))[:30],
                                        str(interface.get('ipv4Address', 'N/A'))[:15],
                                        str(interface.get('status', 'N/A'))[:10],
                                        str(interface.get('speed', 'N/A'))[:10]
                                    ))
                                
                                if isinstance(interfaces_data, list):
                                    print(f"(Showing {min(5, len(interfaces_data))}/{len(interfaces_data)} interfaces)")
                        except Exception as e:
                            print(f"Could not fetch interfaces: {e}")
                except Exception as e:
                    print(f"Could not fetch device details: {e}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 