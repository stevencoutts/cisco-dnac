#!/usr/bin/env python3
"""
API client module for interacting with Cisco Catalyst Centre API.
Author: Steven Coutts
"""
import requests
import urllib3
import json
import warnings
from typing import Dict, Any, Optional, Union

# Suppress warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=ResourceWarning)

class ApiClient:
    """API Client for Cisco Catalyst Centre."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize API client with configuration."""
        self.config = config
        self.token = None
        self.base_url = self._build_base_url()
        
    def _build_base_url(self) -> str:
        """Build the base URL from configuration."""
        host = self.config['server']['host']
        if not host.startswith('http'):
            host = f"https://{host}"
        if host.endswith('/'):
            host = host[:-1]
            
        port = self.config['server'].get('port', 443)
        return f"{host}:{port}"
    
    def authenticate(self) -> bool:
        """Authenticate with the DNAC API and get a token."""
        auth_url = f"{self.base_url}/dna/system/api/v1/auth/token"
        username = self.config['auth']['username']
        password = self.config['auth']['password']
        verify_ssl = self.config['server'].get('verify_ssl', True)
        timeout = self.config['server'].get('timeout', 30)
        
        try:
            response = requests.post(
                auth_url,
                auth=(username, password),
                verify=verify_ssl,
                timeout=timeout
            )
            response.raise_for_status()
            self.token = response.json().get('Token')
            return bool(self.token)
        except (requests.exceptions.RequestException, json.JSONDecodeError):
            return False
    
    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Union[Dict[str, Any], list]]:
        """Make a GET request to the DNAC API."""
        if not self.token and not self.authenticate():
            return None
            
        url = f"{self.base_url}/{path}"
        headers = {
            'x-auth-token': self.token,
            'Content-Type': 'application/json'
        }
        verify_ssl = self.config['server'].get('verify_ssl', True)
        timeout = self.config['server'].get('timeout', 30)
        
        try:
            response = requests.get(
                url,
                headers=headers,
                params=params,
                verify=verify_ssl,
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, json.JSONDecodeError):
            return None 