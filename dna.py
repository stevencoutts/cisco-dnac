"""
This module implements a northbound API client manager for Catalyst Centre

The module provides a client interface for interacting with Cisco Catalyst Centre's REST API.
It handles authentication, request/response serialization, and task management.

Basic Usage:
    >>> dnac = dna.Dnac('https://10.0.0.1/')
    >>> dnac.login('admin', 'password')
    >>> print(dnac.get('network-device/count'))
    >>> dnac.close()

Or as a context manager:
    >>> with dna.Dnac('https://10.0.0.1/') as dnac:
    ...     dnac.login('admin', 'password')
    ...     print(dnac.get('network-device/count'))
"""

from __future__ import annotations

import json
import time
import logging
from typing import Any, Dict, List, Optional, Union, TypeVar, Generic
from dataclasses import dataclass
from urllib.parse import urlparse, urljoin

import requests
from requests import HTTPError, Response

# Disable SSL warnings
requests.packages.urllib3.disable_warnings()

T = TypeVar("T")


@dataclass
class TaskStatus:
    """Represents the status of a Catalyst Centre task."""

    task_id: str
    is_error: bool
    error_code: Optional[str] = None
    failure_reason: Optional[str] = None
    progress: Optional[str] = None
    end_time: Optional[float] = None
    start_time: Optional[float] = None


class DnacError(Exception):
    """Base exception for Catalyst Centre API errors."""

    pass


class TimeoutError(DnacError):
    """Raised when a task exceeds its timeout period."""

    pass


class TaskError(DnacError):
    """Raised when a task fails to complete successfully."""

    def __init__(self, message: str, response: Optional[Response] = None) -> None:
        self.response = response
        super().__init__(message)


class JsonObj(dict, Generic[T]):
    """Dictionary with attribute access for JSON objects.

    This class provides dictionary-like access to JSON objects with the ability
    to access keys as attributes. It also provides type hints for better IDE support.
    """

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __getattr__(self, name: str) -> Any:
        """Access dictionary keys as attributes.

        Args:
            name: The key to access

        Returns:
            The value associated with the key

        Raises:
            AttributeError: If the key doesn't exist
        """
        try:
            return self[name]
        except KeyError:
            # If this is a Response object, try to get the method from it
            if hasattr(self, '_response') and hasattr(self._response, name):
                return getattr(self._response, name)
            raise AttributeError(name)

    def __str__(self) -> str:
        """Serialize object to JSON formatted string with indents."""
        return json.dumps(self, indent=4)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._response = None  # Store the original Response object

    @classmethod
    def from_response(cls, response: Response) -> 'JsonObj':
        """Create a JsonObj from a Response object.

        Args:
            response: The Response object to create from

        Returns:
            A new JsonObj instance
        """
        obj = cls(response.json())
        obj._response = response
        return obj


class Dnac(requests.Session):
    """REST API session manager for Catalyst Centre.

    This class provides a session manager for interacting with Cisco Catalyst Centre's
    REST API. It handles authentication, request/response serialization, and task management.

    Args:
        url: The base URL of the Catalyst Centre instance

    Raises:
        ValueError: If the URL is invalid
    """

    def __init__(self, url: str) -> None:
        """Initialize the Catalyst Centre client.

        Args:
            url: The base URL of the Catalyst Centre instance

        Raises:
            ValueError: If the URL is invalid
        """
        super().__init__()
        try:
            parsed = urlparse(url)
            if not parsed.scheme:
                url = f"https://{url}"
                parsed = urlparse(url)
            if not parsed.netloc:
                raise ValueError(f"Invalid URL: {url} - No host supplied")
            self.base_url = url.rstrip('/')  # Keep the full URL including protocol
        except Exception as e:
            raise ValueError(f"Invalid URL: {url}") from e

        self.headers.update({"Content-Type": "application/json"})
        self.verify = False  # Ignore verifying the SSL certificate

    def login(self, username: str, password: str) -> None:
        """Authenticate with Catalyst Centre.

        Args:
            username: The username for authentication
            password: The password for authentication

        Raises:
            HTTPError: If authentication fails
        """
        # First try to get a token
        response = self.post(
            "system/api/v1/auth/token",  # Fixed authentication endpoint path
            auth=(username, password),
            headers={"Content-Type": "application/json"}
        )
        
        # Check status code first
        response.raise_for_status()
            
        try:
            # Try to parse the response as JSON
            data = response.json()
            token = data.get("Token")
            if not token:
                raise HTTPError("No token received in authentication response")
            self.headers.update({
                "X-Auth-Token": token,
                "Content-Type": "application/json"
            })
        except ValueError:
            # If we get HTML instead of JSON, authentication failed
            raise HTTPError(
                "Authentication failed - received HTML response instead of JSON. "
                "Please check your credentials and server URL."
            )

    def request(
        self,
        method: str,
        api: str,
        ver: str = "api/v1",
        data: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Union[Response, JsonObj]:
        """Send a request to the Catalyst Centre API.

        Args:
            method: The HTTP method to use
            api: The API endpoint to call
            ver: The API version to use
            data: Optional data to send with the request
            **kwargs: Additional arguments to pass to requests

        Returns:
            The parsed JSON response or raw Response object

        Raises:
            HTTPError: If the request fails
            ValueError: If the response is not valid JSON
        """
        # Construct the full URL properly
        base = self.base_url.rstrip('/')
        ver = ver.strip('/')
        api = api.strip('/')
        
        # Special handling for authentication endpoint
        if api == "system/api/v1/auth/token":
            url = f"{base}/dna/{api}"
        else:
            # If the API path already includes the version, don't add it again
            if api.startswith('dna/intent/api/'):
                url = f"{base}/{api}"
            else:
                url = f"{base}/dna/{ver}/{api}"
        
        # Add Accept header for JSON responses
        headers = kwargs.pop('headers', {})
        headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        kwargs['headers'] = headers
        
        # Encode data if provided
        if data is not None:
            kwargs['json'] = data  # Use json parameter instead of manually encoding
        
        response = super().request(method, url, **kwargs)

        # Check status code first
        response.raise_for_status()

        # Then try to parse JSON
        try:
            json_obj = JsonObj.from_response(response)
        except ValueError:
            logging.debug("Response is not JSON encoded")
            return response

        # Handle error responses
        if 400 <= response.status_code < 600 and "response" in json_obj:
            response.reason = _flatten(
                ": ", json_obj.response, ["errorCode", "message", "detail"]
            )
            response.raise_for_status()

        return json_obj

    def wait_on_task(
        self,
        task_id: str,
        timeout: float = 125,
        interval: float = 2,
        backoff: float = 1.15,
    ) -> JsonObj:
        """Wait for a task to complete.

        Args:
            task_id: The ID of the task to wait for
            timeout: Maximum time to wait in seconds
            interval: Initial interval between checks in seconds
            backoff: Multiplier for increasing the interval

        Returns:
            The task response

        Raises:
            TimeoutError: If the task exceeds the timeout
            TaskError: If the task fails
        """
        start_time = time.time()
        while True:
            response = self.get("task/" + task_id)
            if "endTime" in response.response:
                msg = _flatten(
                    ": ", response.response, ["errorCode", "failureReason", "progress"]
                )
                if response.response.get("isError", False):
                    raise TaskError(msg, response=response)
                logging.info(f"TASK {task_id} has completed and returned: {msg}")
                return response
            elif start_time + timeout < time.time():
                raise TimeoutError(
                    f"TASK {task_id} did not complete within the specified "
                    f"time-out ({timeout} seconds)"
                )
            logging.info(
                f"TASK {task_id} has not completed yet. Sleeping {int(interval)} seconds"
            )
            time.sleep(int(interval))
            interval *= backoff


def _flatten(string: str, dct: Dict[str, Any], keys: List[str]) -> str:
    """Join values of given keys existing in dict with a separator.

    Args:
        string: The separator to use
        dct: The dictionary to process
        keys: The keys to look for

    Returns:
        The joined string
    """
    return string.join(str(dct[k]) for k in set(keys) & set(dct.keys()))


def find(
    obj: Union[List[Any], JsonObj], val: Any, key: str = "id"
) -> Optional[JsonObj]:
    """Recursively search JSON object for a value of a key/attribute.

    Args:
        obj: The object to search in
        val: The value to search for
        key: The key to search for

    Returns:
        The matching object or None if not found
    """
    if isinstance(obj, list):
        for item in obj:
            r = find(item, val, key)
            if r is not None:
                return r
    elif isinstance(obj, JsonObj):
        if obj.get(key) == val:
            return obj
        for item in iter(obj):
            if isinstance(obj[item], list):
                return find(obj[item], val, key)
    return None


def ctime(val: Union[int, float]) -> str:
    """Convert time in milliseconds since the epoch to a formatted string.

    Args:
        val: The time in milliseconds

    Returns:
        The formatted time string
    """
    return time.ctime(int(val) // 1000)
