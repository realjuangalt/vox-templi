"""Daily on-chain price history. Separate from the last-144-block live scan.

Stores compact {d, usd} points. One UTC day per invocation so the Pi stays usable.
Newest point is what the HUD should show; labeled as beyond the last 144 blocks.
"""
from __future__ import annotations

import json
import time
from datetime import date, datetime, timedelta, timezone

from .config import Config
from . import log
from .oracle import invoke

EARLIEST = date(2023, 12, 15)
MAX_POINTS = 400  # ~13 months of daily ints — a few KB


def _load(cfg: Config) -> dict:
    p = cfg.history_json
    if not p.is_file():
        return {"v": 1, "computing": False, "computing_date": None, "points": []}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        data.setdefault("points", [])
        return data
    except Exception:
        return {"v": 1, "computing": False, "computing_date": None, "points": []}


def _save(cfg: Config, data: dict) -> dict:
    cfg.state_dir.mkdir(parents=True, exist_ok=True)
    data["points"] = data["points"][-MAX_POINTS:]
    tmp = cfg.history_json.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    tmp.replace(cfg.history_json)
    return data


def newest(data: dict) -> dict | None:
    pts = data.get("points") or []
    if not pts:
        return None
    return max(pts, key=lambda p: p.get("d") or "")


def _next_date(have: set[str]) -> date | None:
    today = datetime.now(timezone.utc).date()
    d = today - timedelta(days=1)
    while d >= EARLIEST:
        key = d.isoformat()
        if key not in have:
            return d
        d -= timedelta(days=1)
    return None


def step(cfg: Config) -> dict:
    """Fill the next missing UTC day. Safe to run from a timer."""
    data = _load(cfg)
    have = {p["d"] for p in data["points"] if "d" in p}
    day = _next_date(have)
    if day is None:
        data["computing"] = False
        data["computing_date"] = None
        log.emit("history", "complete", n=len(data["points"]))
        return _save(cfg, data)

    key = day.isoformat()
    data["computing"] = True
    data["computing_date"] = key
    _save(cfg, data)
    log.emit("history", "start", date=key)

    arg = day.strftime("%Y/%m/%d")
    try:
        usd, text, rc = invoke(cfg, ["-d", arg])
    except Exception as e:
        data["computing"] = False
        log.emit("history", "error", date=key, err=str(e))
        return _save(cfg, data)

    (cfg.state_dir / "history-last.log").write_text(text[-40_000:], encoding="utf-8")
    data["computing"] = False
    data["computing_date"] = None
    if usd:
        data["points"] = [p for p in data["points"] if p.get("d") != key]
        data["points"].append({"d": key, "usd": usd, "t": int(time.time())})
        log.emit("history", "ok", date=key, usd=usd)
    else:
        log.emit("history", "skip", date=key, rc=rc)
    return _save(cfg, data)
