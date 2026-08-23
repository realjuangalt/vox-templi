#!/usr/bin/env python3
"""Embassy monitor: static kiosk + /api/status from local bitcoind."""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from collect import STATE_PATH, snapshot, write_snapshot  # noqa: E402

ROOT = Path(os.environ.get("EM_ROOT", HERE.parent / "www"))
HOST = os.environ.get("EM_HOST", "127.0.0.1")
PORT = int(os.environ.get("EM_PORT", "8090"))
POLL = float(os.environ.get("EM_POLL", "8"))

_lock = threading.Lock()
_status: dict = {"ok": False, "note": "starting"}


def poller() -> None:
    global _status
    while True:
        try:
            data = snapshot()
            write_snapshot(data)
            with _lock:
                _status = data
        except Exception as e:
            with _lock:
                _status = {"ok": False, "ts": int(time.time()), "note": str(e)}
            print(f"[monitor] poll error: {e}", file=sys.stderr, flush=True)
        time.sleep(POLL)


class Handler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt, *args):
        print(f"[monitor] {self.address_string()} {fmt % args}", file=sys.stderr, flush=True)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/api/status", "/status.json"):
            with _lock:
                body = json.dumps(_status).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/healthz":
            body = b"ok\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path == "/kiosk-log":
            n = int(self.headers.get("Content-Length", "0"))
            line = self.rfile.read(n).decode("utf-8", "replace").strip()
            if line:
                print(f"[kiosk] {line}", file=sys.stderr, flush=True)
            self.send_response(204)
            self.end_headers()
            return
        self.send_error(404)


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    threading.Thread(target=poller, name="rpc-poll", daemon=True).start()
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"embassy-monitor http://{HOST}:{PORT}  root={ROOT}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
