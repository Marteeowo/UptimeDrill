"""Run a status service with a local file dependency."""

import argparse
import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


class StatusService(HTTPServer):
    def __init__(self, port, message_file, host="127.0.0.1"):
        self.message_file = message_file
        super().__init__((host, port), StatusHandler)


class StatusHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.partition("?")[0]
        if path == "/livez":
            self.send_json(200, {"status": "live"})
            return
        if path not in ("/", "/readyz"):
            self.send_json(404, {"status": "not_found"})
            return

        try:
            message = self.server.message_file.read_text(encoding="utf-8").strip()
            if not message:
                raise ValueError("empty message")
        except (OSError, ValueError) as error:
            logging.warning("message dependency unavailable (%s)", type(error).__name__)
            self.send_json(503, {"status": "unavailable"})
            return

        payload = {"status": "ready"} if path == "/readyz" else {"message": message}
        self.send_json(200, payload)

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8080, help="use 0 for an available port")
    parser.add_argument("--message-file", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    with StatusService(args.port, args.message_file, args.host) as server:
        logging.info("Listening on %s:%d", args.host, server.server_port)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
