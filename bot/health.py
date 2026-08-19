import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


class HealthHandler(BaseHTTPRequestHandler):

    def _send_health_response(
        self,
        include_body: bool = True,
    ):
        body = b"RSS-Sky-Mvz Bot is running."

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8",
        )
        self.send_header(
            "Content-Length",
            str(len(body)),
        )
        self.end_headers()

        if include_body:
            self.wfile.write(body)

    def do_GET(self):
        self._send_health_response(
            include_body=True,
        )

    def do_HEAD(self):
        self._send_health_response(
            include_body=False,
        )

    def log_message(
        self,
        format,
        *args,
    ):
        return


def start_health_server():
    port = int(
        os.getenv(
            "PORT",
            "10000",
        )
    )

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler,
    )

    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )

    thread.start()
