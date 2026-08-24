"""Rolling debug log. Isolated from RPC, oracle, and HTTP.

Default: truncate when the file exceeds VOX_LOG_MAX_BYTES (2 MiB).
Set VOX_LOG_FOREVER=1 to never shrink (disk can fill).
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any

_lock = threading.Lock()
_path: Path | None = None
_max = 2 * 1024 * 1024
_forever = False


def configure(path: Path, max_bytes: int = 2 * 1024 * 1024, forever: bool = False) -> None:
    global _path, _max, _forever
    _path = path
    _max = max(32_768, int(max_bytes))
    _forever = forever
    path.parent.mkdir(parents=True, exist_ok=True)


def _trim(p: Path) -> None:
    if _forever or not p.is_file():
        return
    size = p.stat().st_size
    if size <= _max:
        return
    keep = _max // 2
    with p.open("rb") as f:
        f.seek(size - keep)
        blob = f.read()
    nl = blob.find(b"\n")
    if nl >= 0:
        blob = blob[nl + 1 :]
    tmp = p.with_suffix(".tmp")
    tmp.write_bytes(blob)
    tmp.replace(p)


def emit(channel: str, msg: str, **data: Any) -> None:
    """One JSON line. Never throws into callers."""
    rec = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ch": channel,
        "msg": msg,
    }
    if data:
        rec["data"] = data
    line = json.dumps(rec, default=str) + "\n"
    path = _path
    if path is None:
        print(line, end="", flush=True)
        return
    try:
        with _lock:
            with path.open("a", encoding="utf-8") as f:
                f.write(line)
            _trim(path)
    except OSError as e:
        print(f"[vox-log] {e}: {line}", end="", flush=True)


def tail(n: int = 80) -> list[str]:
    path = _path
    if path is None or not path.is_file():
        return []
    n = max(1, min(500, n))
    try:
        with path.open("rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - 64_000))
            text = f.read().decode("utf-8", "replace")
        lines = [ln for ln in text.splitlines() if ln.strip()]
        return lines[-n:]
    except OSError:
        return []
