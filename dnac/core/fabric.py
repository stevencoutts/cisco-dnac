#!/usr/bin/env python3
"""
Fabric detection module for Cisco Catalyst Centre SDA.
Author: Steven Coutts
"""
from typing import Dict, Any
from dnac.core.api import Dnac

def is_fabric_enabled(config: Dict[str, Any]) -> bool:
    """
    Check if Fabric/SDA is enabled on the Catalyst Centre.
    
    This checks for the presence of virtual networks, which indicates
    that SDA is enabled and configured.
    """
    # Extract server and auth details
    server_config = config.get('server', {})
    host = server_config.get('host')
    
    auth_config = config.get('auth', {})
    username = auth_config.get('username')
    password = auth_config.get('password')
    
    if not all([host, username, password]):
        return False
    
    try:
        # Initialize DNAC client
        dnac = Dnac(host)
        
        # Set SSL verification based on config
        dnac.verify = server_config.get('verify_ssl', False)
        
        # Login and get token
        dnac.login(username, password)
        
        # Try to get virtual networks which only exist with SDA
        response = dnac.get("virtual-network", ver="v2")
        
        # Check if response indicates SDA is enabled
        if hasattr(response, 'response') and hasattr(response.response, 'json'):
            data = response.response.json()
            return isinstance(data, list) and len(data) > 0
        
        return False
        
    except Exception:
        return False 