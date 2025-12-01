"""HTTP client for sending requests to external services."""

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional


class ExternalAPIClient:
    """Lightweight HTTP client for making requests to external services."""

    def __init__(self, base_url: str, timeout: float = 30.0):
        """
        Initialize the external API client.

        Args:
            base_url: Base URL of the external service.
            timeout: Request timeout in seconds.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make an HTTP request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            endpoint: API endpoint path.
            data: Request body data (for POST/PUT).
            params: Query parameters (for GET).

        Returns:
            Response data as dictionary.

        Raises:
            urllib.error.HTTPError: If the request fails.
            urllib.error.URLError: If there's a network error.
        """
        url = f"{self.base_url}{endpoint}"

        if params:
            query_string = urllib.parse.urlencode(params)
            url = f"{url}?{query_string}"

        request_data = None
        headers = {}

        if data is not None:
            request_data = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=request_data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                response_data = response.read().decode("utf-8")
                if response_data:
                    return json.loads(response_data)
                return {}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            raise urllib.error.HTTPError(
                e.url, e.code, f"{e.reason}: {error_body}", e.headers, e.fp
            )

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a GET request to the external service.

        Args:
            endpoint: API endpoint path.
            params: Query parameters.

        Returns:
            Response data as dictionary.
        """
        return self._make_request("GET", endpoint, params=params)

    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a POST request to the external service.

        Args:
            endpoint: API endpoint path.
            data: Request body data.

        Returns:
            Response data as dictionary.
        """
        return self._make_request("POST", endpoint, data=data)

    def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a PUT request to the external service.

        Args:
            endpoint: API endpoint path.
            data: Request body data.

        Returns:
            Response data as dictionary.
        """
        return self._make_request("PUT", endpoint, data=data)

    def delete(self, endpoint: str) -> Dict[str, Any]:
        """
        Send a DELETE request to the external service.

        Args:
            endpoint: API endpoint path.

        Returns:
            Response data as dictionary.
        """
        return self._make_request("DELETE", endpoint)

