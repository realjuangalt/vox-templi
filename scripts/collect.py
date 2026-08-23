#!/usr/bin/env python3
"""Snapshot node + mempool + cached UTXOracle into one JSON blob."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from rpc import rpc, sat_vb

ORACLE_PATH = Path(os.environ.get("EM_ORACLE_JSON", "/var/lib/embassy-monitor/oracle.json"))
STATE_PATH = Path(os.environ.get("EM_STATE_JSON", "/var/lib/embassy-monitor/status.json"))


def _fee(blocks: int) -> float | None:
    try:
        r = rpc("estimatesmartfee", blocks, timeout=8)
        return sat_vb((r or {}).get("feerate"))
    except Exception:
        return None


def _oracle() -> dict:
    if not ORACLE_PATH.exists():
        return {"state": "warming", "usd": None, "note": "first on-chain scan not finished"}
    try:
        return json.loads(ORACLE_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        return {"state": "error", "usd": None, "note": str(e)}


def snapshot() -> dict:
    chain = rpc("getblockchaininfo")
    net = rpc("getnetworkinfo")
    mem = rpc("getmempoolinfo")
    mining = rpc("getmininginfo")
    height = int(chain["blocks"])
    header = rpc("getblockheader", chain["bestblockhash"])
    now = int(time.time())
    block_age = max(0, now - int(header.get("time") or now))
    next_halving = 210000 - (height % 210000)
    mem_bytes = int(mem.get("bytes") or 0)
    mem_tx = int(mem.get("size") or 0)
    mem_cap = int(mem.get("maxmempool") or 300_000_000) or 300_000_000
    min_fee = sat_vb(mem.get("mempoolminfee"))
    return {
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
            "next_halving_blocks": next_halving,
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
            "min_sat_vb": min_fee,
            "fee_fast": _fee(1),
            "fee_mid": _fee(3),
            "fee_slow": _fee(6),
        },
        "oracle": _oracle(),
    }


def write_snapshot(data: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(STATE_PATH)
