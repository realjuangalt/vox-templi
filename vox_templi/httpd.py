"""Local HTTP for the kiosk page + /api/status."""
from __future__ import annotations

import json
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from .collect import snapshot, write_snapshot
from .config import Config

_lock = threading.Lock()
_status: dict = {"ok": False, "note": "starting"}


def _poller(cfg: Config) -> None:
    global _status
    while True:
        try:
            data = snapshot(cfg)
            write_snapshot(cfg, data)
            with _lock:
                _status = data
        except Exception as e:
            with _lock:
                _status = {"ok": False, "ts": int(time.time()), "note": str(e)}
            print(f"[vox] poll error: {e}", flush=True)
        time.sleep(cfg.poll_s)


def serve(cfg: Config) -> None:
    cfg.www.mkdir(parents=True, exist_ok=True)
    cfg.state_dir.mkdir(parents=True, exist_ok=True)
    threading.Thread(target=_poller, args=(cfg,), name="rpc-poll", daemon=True).start()

    www = cfg.www

    class Handler(SimpleHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(www), **kwargs)

        def log_message(self, fmt, *args):
            print(f"[vox] {self.address_string()} {fmt % args}", flush=True)

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
                self.rfile.read(n)
                self.send_response(204)
                self.end_headers()
                return
            self.send_error(404)

    httpd = ThreadingHTTPServer((cfg.bind, cfg.port), Handler)
    print(f"vox-templi http://{cfg.bind}:{cfg.port}  www={cfg.www}", flush=True)
    httpd.serve_forever()
