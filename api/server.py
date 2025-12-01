"""Lightweight HTTP server for Ruby agent."""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import Callable, Dict, Optional
from urllib.parse import parse_qs, urlparse


class RubyAgentHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Ruby agent endpoints."""

    def __init__(self, *args, handlers: Optional[Dict[str, Callable]] = None, **kwargs):
        """Initialize the handler with custom route handlers."""
        self.handlers = handlers or {}
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)

        if path in self.handlers:
            try:
                response_data = self.handlers[path](query_params)
                self._send_json_response(200, response_data)
            except Exception as e:
                self._send_error_response(500, str(e))
        else:
            self._send_error_response(404, f"Endpoint not found: {path}")

    def do_POST(self):
        """Handle POST requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path in self.handlers:
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length)
                request_data = json.loads(body.decode("utf-8")) if body else {}

                response_data = self.handlers[path](request_data)
                self._send_json_response(200, response_data)
            except json.JSONDecodeError:
                self._send_error_response(400, "Invalid JSON in request body")
            except Exception as e:
                self._send_error_response(500, str(e))
        else:
            self._send_error_response(404, f"Endpoint not found: {path}")

    def _send_json_response(self, status_code: int, data: Dict):
        """Send a JSON response."""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        response = json.dumps(data).encode("utf-8")
        self.wfile.write(response)

    def _send_error_response(self, status_code: int, message: str):
        """Send an error response."""
        self._send_json_response(status_code, {"error": message})

    def log_message(self, format, *args):
        """Override to customize logging."""
        pass  # Suppress default logging


class RubyAgentServer:
    """Lightweight HTTP server for Ruby agent."""

    def __init__(self, host: str = "localhost", port: int = 8000):
        """
        Initialize the server.

        Args:
            host: Host to bind to.
            port: Port to listen on.
        """
        self.host = host
        self.port = port
        self.handlers: Dict[str, Callable] = {}
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[Thread] = None

    def register_handler(self, path: str, handler: Callable):
        """
        Register a handler for a specific path.

        Args:
            path: URL path (e.g., "/analyze").
            handler: Function that takes request data and returns response dict.
        """
        self.handlers[path] = handler

    def start(self, daemon: bool = True):
        """
        Start the server in a background thread.

        Args:
            daemon: Whether the thread should be a daemon thread.
        """
        if self._server is not None:
            raise RuntimeError("Server is already running")

        def handler_factory(*args, **kwargs):
            return RubyAgentHandler(*args, handlers=self.handlers, **kwargs)

        self._server = HTTPServer((self.host, self.port), handler_factory)
        self._thread = Thread(target=self._server.serve_forever, daemon=daemon)
        self._thread.start()
        print(f"Ruby agent server started on http://{self.host}:{self.port}")

    def stop(self):
        """Stop the server."""
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
            self._thread = None
            print("Ruby agent server stopped")

    def is_running(self) -> bool:
        """Check if the server is running."""
        return self._server is not None

