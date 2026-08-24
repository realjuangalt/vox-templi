"""Daily UTXOracle prices. Bundled series is canonical; the node only appends new days.

Dates already in data/utxoracle-daily.json are never recomputed.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .config import ROOT, Config
from . import log
from .oracle import invoke

EARLIEST = date(2023, 12, 15)
BUNDLE = ROOT / "data" / "utxoracle-daily.json"


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {"points": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        data.setdefault("points", [])
        return data
    except Exception:
        return {"points": []}


def _bundled_points() -> list[dict]:
    return list(_read_json(BUNDLE).get("points") or [])


def _load(cfg: Config) -> dict:
    by: dict[str, dict] = {}
    for p in _bundled_points():
        if p.get("d") and p.get("usd"):
            by[p["d"]] = {"d": p["d"], "usd": int(p["usd"])}
    local = _read_json(cfg.history_json)
    for p in local.get("points") or []:
        if p.get("d") and p.get("usd") and p["d"] not in by:
            by[p["d"]] = {"d": p["d"], "usd": int(p["usd"])}
    return {
        "v": 1,
        "computing": bool(local.get("computing")),
        "computing_date": local.get("computing_date"),
        "points": sorted(by.values(), key=lambda p: p["d"]),
    }


def _save_local(cfg: Config, data: dict) -> dict:
    """Persist only points not already in the bundle (runtime appends)."""
    bundled = {p["d"] for p in _bundled_points() if p.get("d")}
    extra = [p for p in data["points"] if p.get("d") not in bundled]
    payload = {
        "v": 1,
        "computing": data.get("computing", False),
        "computing_date": data.get("computing_date"),
        "points": extra,
    }
    cfg.state_dir.mkdir(parents=True, exist_ok=True)
    tmp = cfg.history_json.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    tmp.replace(cfg.history_json)
    return data


def newest(data: dict) -> dict | None:
    pts = data.get("points") or []
    if not pts:
        return None
    return max(pts, key=lambda p: p.get("d") or "")


def _next_date(have: set[str]) -> date | None:
    """Newest missing day first (HUD), then walk back to EARLIEST."""
    today = datetime.now(timezone.utc).date()
    d = today - timedelta(days=1)
    while d >= EARLIEST:
        if d.isoformat() not in have:
            return d
        d -= timedelta(days=1)
    return None


def step(cfg: Config) -> dict:
    data = _load(cfg)
    have = {p["d"] for p in data["points"] if "d" in p}
    day = _next_date(have)
    if day is None:
        data["computing"] = False
        data["computing_date"] = None
        log.emit("history", "complete", n=len(data["points"]))
        return _save_local(cfg, data)

    key = day.isoformat()
    data["computing"] = True
    data["computing_date"] = key
    _save_local(cfg, data)
    log.emit("history", "start", date=key)

    arg = day.strftime("%Y/%m/%d")
    try:
        usd, text, rc = invoke(cfg, ["-d", arg])
    except Exception as e:
        data["computing"] = False
        data["computing_date"] = None
        log.emit("history", "error", date=key, err=str(e))
        return _save_local(cfg, data)

    (cfg.state_dir / "history-last.log").write_text(text[-40_000:], encoding="utf-8")
    data["computing"] = False
    data["computing_date"] = None
    if usd:
        data["points"] = [p for p in data["points"] if p.get("d") != key]
        data["points"].append({"d": key, "usd": usd})
        log.emit("history", "ok", date=key, usd=usd)
    else:
        log.emit("history", "skip", date=key, rc=rc)
    return _save_local(cfg, data)


def fill(cfg: Config) -> dict:
    """Keep stepping until yesterday is present (long-running)."""
    last = None
    while True:
        data = step(cfg)
        last = data
        have = {p["d"] for p in data["points"]}
        if _next_date(have) is None:
            return data
        log.emit("history", "continue", n=len(data["points"]))
    return last or data


def export_bundle(cfg: Config, dest: Path | None = None) -> Path:
    """Write merged series for committing into data/utxoracle-daily.json."""
    data = _load(cfg)
    dest = dest or BUNDLE
    payload = {
        "v": 1,
        "algo": "UTXOracle-9.1",
        "earliest": EARLIEST.isoformat(),
        "note": "Deterministic daily USD from settled chain. Same date ⇒ same price on every node.",
        "points": [{"d": p["d"], "usd": int(p["usd"])} for p in data["points"] if p.get("d") and p.get("usd")],
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return dest
