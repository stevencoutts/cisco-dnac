#!/usr/bin/env python3
"""
Fabric detection module for Cisco Catalyst Centre SDA.
Author: Steven Coutts
"""
from typing import Dict, Any
from dnac.core.api import ApiClient

def is_fabric_enabled(config: Dict[str, Any]) -> bool:
    """
    Check if Fabric/SDA is enabled on the Catalyst Centre.
    
    This checks for the presence of virtual networks, which indicates
    that SDA is enabled and configured.
    """
    client = ApiClient(config)
    
    # Try to authenticate
    if not client.authenticate():
        return False
    
    # Check for virtual networks
    vn_data = client.get("dna/intent/api/v2/virtual-network")
    
    # If we get a valid response with data, SDA is enabled
    return bool(vn_data and isinstance(vn_data, list) and len(vn_data) > 0) 