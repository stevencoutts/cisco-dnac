#!/usr/bin/env python3
"""
API client module for interacting with Cisco Catalyst Centre API.
Author: Steven Coutts
"""
import requests
import urllib3
import json
import warnings
import time
from typing import Dict, Any, Optional, Union, List, Tuple

# Suppress warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=ResourceWarning)

class ApiResponse:
    """Wrapper for API responses with attribute access."""
    
    def __init__(self, response):
        self.response = response
        
    def __getattr__(self, name):
        if hasattr(self.response, name):
            return getattr(self.response, name)
        elif hasattr(self.response, 'json') and callable(self.response.json):
            try:
                data = self.response.json()
                if isinstance(data, dict) and name in data:
                    return data[name]
            except:
                pass
        raise AttributeError(f"No attribute {name}")

class ApiError(Exception):
    """API error with response details."""
    
    def __init__(self, message, response=None):
        self.message = message
        self.response = response
        super().__init__(message)

class TaskError(ApiError):
    """Error occurred during task execution."""
    pass

class TimeoutError(ApiError):
    """Operation timed out."""
    pass

class Dnac:
    """Cisco Catalyst Centre REST API client."""
    
    def __init__(self, host):
        """Initialize with host address."""
        # Add protocol if missing
        if not host.startswith('http'):
            host = f'https://{host}'
        # Remove trailing slash
        if host.endswith('/'):
            host = host[:-1]
        self.host = host
        self.port = None  # Will default to 443 for HTTPS
        self.path = ""
        self.verify = False
        self.token = None
        self.token_time = 0
        self.session = requests.Session()
        self.session.verify = self.verify
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.close()
    
    def close(self):
        """Close the session."""
        if self.session:
            self.session.close()
    
    def login(self, username, password):
        """Login and get authentication token."""
        auth_endpoint = f"{self.host}/dna/system/api/v1/auth/token"
        response = self.session.post(
            auth_endpoint,
            auth=(username, password)
        )
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get('Token')
            self.token_time = time.time()
            return True
        else:
            raise ApiError(f"Login failed: {response.status_code} {response.text}", response)
    
    def _build_url(self, path, ver=None):
        """Build the full URL for an API endpoint."""
        if path.startswith('/'):
            path = path[1:]
        
        # If path already has a protocol and host, return as is
        if path.startswith('http'):
            return path
            
        # Add version prefix if specified
        if ver is not None:
            if ver and not path.startswith(f"dna/intent/api/{ver}/"):
                path = f"dna/intent/api/{ver}/{path}"
        
        # Construct full URL
        port_str = f":{self.port}" if self.port else ""
        return f"{self.host}{port_str}/{path}"
    
    def _check_token(self):
        """Check if token is still valid."""
        if not self.token:
            raise ApiError("Not authenticated. Call login() first")
        
        # Token refresh logic could be added here
        return True
    
    def get(self, path, ver="v1", params=None):
        """Make a GET request to the API."""
        self._check_token()
        url = self._build_url(path, ver)
        
        headers = {
            "x-auth-token": self.token,
            "Content-Type": "application/json"
        }
        
        response = self.session.get(url, headers=headers, params=params)
        return ApiResponse(response)
    
    def post(self, path, ver="v1", data=None, params=None):
        """Make a POST request to the API."""
        self._check_token()
        url = self._build_url(path, ver)
        
        headers = {
            "x-auth-token": self.token,
            "Content-Type": "application/json"
        }
        
        if isinstance(data, dict):
            data = json.dumps(data)
            
        response = self.session.post(url, headers=headers, data=data, params=params)
        return ApiResponse(response)
    
    def put(self, path, ver="v1", data=None, params=None):
        """Make a PUT request to the API."""
        self._check_token()
        url = self._build_url(path, ver)
        
        headers = {
            "x-auth-token": self.token,
            "Content-Type": "application/json"
        }
        
        if isinstance(data, dict):
            data = json.dumps(data)
            
        response = self.session.put(url, headers=headers, data=data, params=params)
        return ApiResponse(response)
    
    def delete(self, path, ver="v1", params=None):
        """Make a DELETE request to the API."""
        self._check_token()
        url = self._build_url(path, ver)
        
        headers = {
            "x-auth-token": self.token,
            "Content-Type": "application/json"
        }
        
        response = self.session.delete(url, headers=headers, params=params)
        return ApiResponse(response)
    
    def wait_on_task(self, task_id, timeout=120, interval=1, backoff=1.5):
        """Wait for a task to complete."""
        start_time = time.time()
        current_interval = interval
        
        while time.time() - start_time < timeout:
            response = self.get(f"task/{task_id}")
            
            # Check response format
            if not response or not hasattr(response, 'response'):
                time.sleep(current_interval)
                current_interval *= backoff
                continue
                
            # Get response data
            try:
                data = response.response.json()
                if isinstance(data, dict) and 'response' in data:
                    data = data['response']
                
                # Check if task is done
                if data.get('isError', False):
                    raise TaskError(f"Task failed: {data.get('failureReason', 'Unknown error')}", response.response)
                
                if data.get('endTime', None):
                    return data
            except Exception as e:
                pass
                
            # Wait before checking again
            time.sleep(current_interval)
            current_interval *= backoff
            
        raise TimeoutError(f"Task did not complete within {timeout} seconds", None) 