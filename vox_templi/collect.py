"""Snapshot chain + mempool + cached oracle. Speaks only through Bitcoin wrapper."""
from __future__ import annotations

import json
import time
from pathlib import Path

from .bitcoin import Bitcoin
from .config import Config
from . import log


def _fee(btc: Bitcoin, blocks: int) -> float | None:
    try:
        r = btc.call("estimatesmartfee", blocks, timeout=8)
        return Bitcoin.sat_vb((r or {}).get("feerate"))
    except Exception:
        return None


def _oracle(path: Path) -> dict:
    if not path.exists():
        return {
            "state": "warming",
            "usd": None,
            "kind": "not-run",
            "note": "oracle job has not written a result yet",
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"state": "error", "usd": None, "kind": "bad-json", "note": str(e)}
    if not data.get("usd") and data.get("state") not in ("ok", "warming"):
        data.setdefault("kind", data.get("state") or "error")
        data.setdefault("note", "no USD parsed from last scan")
    return data


def snapshot(cfg: Config, btc: Bitcoin | None = None) -> dict:
    btc = btc or Bitcoin(cfg)
    chain = btc.call("getblockchaininfo")
    net = btc.call("getnetworkinfo")
    mem = btc.call("getmempoolinfo")
    mining = btc.call("getmininginfo")
    height = int(chain["blocks"])
    header = btc.call("getblockheader", chain["bestblockhash"])
    now = int(time.time())
    block_age = max(0, now - int(header.get("time") or now))
    mem_bytes = int(mem.get("bytes") or 0)
    mem_tx = int(mem.get("size") or 0)
    mem_cap = int(mem.get("maxmempool") or 300_000_000) or 300_000_000
    out = {
        "ok": True,
        "ts": now,
        "chain": {
            "height": height,
            "headers": int(chain.get("headers") or height),
            "hash": chain.get("bestblockhash"),
            "ibd": bool(chain.get("initialblockdownload")),
            "progress": float(chain.get("verificationprogress") or 0),
            "disk_gb": round(int(chain.get("size_on_disk") or 0) / 1e9, 1),
            "pruned": bool(chain.get("pruned")),
            "difficulty": float(mining.get("difficulty") or 0),
            "nethash_eh": round(float(mining.get("networkhashps") or 0) / 1e18, 2),
            "block_time": int(header.get("time") or 0),
            "block_age_s": block_age,
            "next_halving_blocks": 210000 - (height % 210000),
        },
        "net": {
            "peers": int(net.get("connections") or 0),
            "in": int(net.get("connections_in") or 0),
            "out": int(net.get("connections_out") or 0),
            "version": (net.get("subversion") or "").strip(),
        },
        "mempool": {
            "tx": mem_tx,
            "mb": round(mem_bytes / 1e6, 2),
            "usage_mb": round(int(mem.get("usage") or 0) / 1e6, 1),
            "fill": min(1.0, mem_bytes / mem_cap),
            "min_sat_vb": Bitcoin.sat_vb(mem.get("mempoolminfee")),
            "fee_fast": _fee(btc, 1),
            "fee_mid": _fee(btc, 3),
            "fee_slow": _fee(btc, 6),
        },
        "oracle": _oracle(cfg.oracle_json),
    }
    ora = out["oracle"]
    log.emit(
        "snapshot",
        "ok",
        height=height,
        mempool=mem_tx,
        oracle=ora.get("state"),
        usd=ora.get("usd"),
        oracle_kind=ora.get("kind"),
    )
    return out


def write_snapshot(cfg: Config, data: dict) -> None:
    cfg.status_json.parent.mkdir(parents=True, exist_ok=True)
    tmp = cfg.status_json.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(cfg.status_json)
