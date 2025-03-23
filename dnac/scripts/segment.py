#!/usr/bin/env python3

"""
Script to display SDA segments
"""

from __future__ import print_function
import dna
import logging
import yaml
import json
from pathlib import Path

def load_config():
    """Load configuration from config.yaml file."""
    config_path = Path("config.yaml")
    if not config_path.exists():
        raise FileNotFoundError("config.yaml not found. Please create it from config.example.yaml")
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    return config

def main():
    # Load configuration
    config = load_config()
    
    # Get server and auth details from config
    host = config['server']['host']  # Get the full URL from config including protocol
    username = config['auth']['username']
    password = config['auth']['password']
    
    # Configure logging if enabled
    if config.get('logging', {}).get('level', 'INFO') == 'DEBUG':
        logging.basicConfig(
            level=logging.DEBUG,
            format=config['logging'].get('format', '%(asctime)s - %(levelname)s - %(message)s')
        )
    
    with dna.Dnac(host) as dnac:
        # Enable debug logging for requests
        logging.getLogger('urllib3').setLevel(logging.DEBUG)
        
        # Login and get token
        dnac.login(username, password)
        print("Successfully authenticated")
        
        # Try a basic endpoint first to verify API access
        try:
            health = dnac.get("dna/intent/api/v1/network-device", ver="")
            print(f"API access: ✓ ({len(health.json())} network devices found)")
        except Exception as e:
            print(f"API access: ✗ ({e})")
        
        # Check if SDA is enabled by trying to access SDA endpoints
        print("\nChecking SDA capability...")
        sda_enabled = True
        
        # Try virtual network domains endpoint
        try:
            domains = dnac.get("dna/intent/api/v1/virtual-network/domains", ver="", params={"limit": 100, "offset": 0})
            print(f"Virtual network domains: ✓")
        except Exception as e:
            print(f"Virtual network domains: ✗")
            sda_enabled = False
        
        # Try segments endpoint
        try:
            segments = dnac.get("dna/intent/api/v1/segment", ver="", params={"limit": 100, "offset": 0})
            print(f"Segments: ✓")
        except Exception as e:
            print(f"Segments: ✗")
            sda_enabled = False
        
        # Display warning if SDA is not enabled
        if not sda_enabled:
            print("\n⚠️  WARNING: This Catalyst Centre instance does not have SDA enabled or configured.")
            print("   To use this script, you need a Catalyst Centre with SDA capability.")
            print("   You can still use other API endpoints like network-device.\n")
            return
            
        # Continue with displaying segments if available
        try:
            fmt = "{:4} {:26} {:13} {:7} {:26}"
            print("\nSDA Segments:")
            print(fmt.format("VLAN", "Name", "Traffic type", "Layer 2", "Fabric"))
            print("-" * 80)
            
            # Only process segments if we successfully retrieved them
            if 'segments' in locals() and hasattr(segments, 'json'):
                segments_data = segments.json()
                domains_data = domains.json() if 'domains' in locals() and hasattr(domains, 'json') else []
                
                for segment in segments_data:
                    try:
                        fabric = dna.find(domains_data, segment['connectivityDomain']['idRef'])['name']
                        print(
                            fmt.format(
                                segment['vlanId'],
                                segment['name'],
                                segment['trafficType'],
                                str(segment['isFloodAndLearn']),
                                fabric,
                            )
                        )
                    except Exception as e:
                        pass
            else:
                print("No segments data available")
        except Exception as e:
            print(f"Error: {e}")
            
        print("=" * 80)


if __name__ == "__main__":
    main()
