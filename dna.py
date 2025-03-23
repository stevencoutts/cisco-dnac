"""
This module implements a northbound API client manager for DNA Center.

The module provides a client interface for interacting with Cisco DNA Center's REST API.
It handles authentication, request/response serialization, and task management.

Basic Usage:
    >>> dnac = dna.Dnac('https://10.0.0.1/')
    >>> dnac.login('admin', 'password')
    >>> print(dnac.get('network-device/count'))
    >>> dnac.close()

Or as a context manager:
    >>> with dna.Dnac('10.0.0.1') as dnac:
    ...     dnac.login('admin', 'password')
    ...     print(dnac.get('network-device/count'))
"""

from __future__ import annotations

import json
import time
import logging
from typing import Any, Dict, List, Optional, Union, TypeVar, Generic
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from requests import HTTPError, Response

# Disable SSL warnings
requests.packages.urllib3.disable_warnings()

T = TypeVar("T")


@dataclass
class TaskStatus:
    """Represents the status of a DNA Center task."""

    task_id: str
    is_error: bool
    error_code: Optional[str] = None
    failure_reason: Optional[str] = None
    progress: Optional[str] = None
    end_time: Optional[float] = None
    start_time: Optional[float] = None


class DnacError(Exception):
    """Base exception for DNA Center API errors."""

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
            raise AttributeError(name)

    def __str__(self) -> str:
        """Serialize object to JSON formatted string with indents."""
        return json.dumps(self, indent=4)


class Dnac(requests.Session):
    """REST API session manager for DNA Center.

    This class provides a session manager for interacting with Cisco DNA Center's
    REST API. It handles authentication, request/response serialization, and task management.

    Args:
        url: The base URL of the DNA Center instance

    Raises:
        ValueError: If the URL is invalid
    """

    def __init__(self, url: str) -> None:
        """Initialize the DNA Center client.

        Args:
            url: The base URL of the DNA Center instance

        Raises:
            ValueError: If the URL is invalid
        """
        super().__init__()
        try:
            parsed = urlparse(url)
            self.base_url = f"https://{parsed.netloc}"
        except Exception as e:
            raise ValueError(f"Invalid URL: {url}") from e

        self.headers.update({"Content-Type": "application/json"})
        self.verify = False  # Ignore verifying the SSL certificate

    def login(self, username: str, password: str) -> None:
        """Authenticate with DNA Center.

        Args:
            username: The username for authentication
            password: The password for authentication

        Raises:
            HTTPError: If authentication fails
        """
        response = self.post(
            "auth/token", ver="api/system/v1", auth=(username, password)
        )
        self.headers.update({"X-Auth-Token": response["Token"]})

    def request(
        self,
        method: str,
        api: str,
        ver: str = "api/v1",
        data: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> JsonObj:
        """Send a request to the DNA Center API.

        Args:
            method: The HTTP method to use
            api: The API endpoint to call
            ver: The API version to use
            data: Optional data to send with the request
            **kwargs: Additional arguments to pass to requests

        Returns:
            The parsed JSON response

        Raises:
            HTTPError: If the request fails
            ValueError: If the response is not valid JSON
        """
        url = f"{self.base_url}/{ver.strip('/')}/{api.strip('/')}"
        data = json.dumps(data).encode("utf-8") if data is not None else None
        response = super().request(method, url, data=data, **kwargs)

        try:
            json_obj = response.json(object_hook=JsonObj)
        except ValueError:
            logging.debug("Response is not JSON encoded")
            json_obj = response
        else:
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
