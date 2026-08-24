"""Detect newly arrived mempool txs. Isolated from viz and oracle.

First poll only stores the id set (no flood of fake bolts). Later polls
return up to LIMIT new entries with vsize + sat/vB.
"""
from __future__ import annotations

from typing import Any

from .bitcoin import Bitcoin, BitcoinRPCError
from . import log

LIMIT = 16
_prev: set[str] | None = None


def ingress(btc: Bitcoin) -> list[dict[str, float]]:
    global _prev
    try:
        ids = btc.call("getrawmempool", False, timeout=12)
    except (BitcoinRPCError, OSError) as e:
        log.emit("mempool", "ids-fail", err=str(e))
        return []
    if not isinstance(ids, list):
        return []
    cur = {str(x) for x in ids}
    if _prev is None:
        _prev = cur
        log.emit("mempool", "prime", n=len(cur))
        return []
    new_ids = list(cur - _prev)[:LIMIT]
    _prev = cur
    out: list[dict[str, float]] = []
    for txid in new_ids:
        try:
            e: dict[str, Any] = btc.call("getmempoolentry", txid, timeout=4) or {}
        except (BitcoinRPCError, OSError):
            continue
        vb = int(e.get("vsize") or e.get("size") or 200)
        fee_btc = 0.0
        fees = e.get("fees") or {}
        if isinstance(fees, dict) and fees.get("base") is not None:
            fee_btc = float(fees["base"])
        elif e.get("fee") is not None:
            fee_btc = float(e["fee"])
        sat_vb = (fee_btc * 1e8) / max(vb, 1)
        out.append({"vb": vb, "sat_vb": round(sat_vb, 2)})
    if out:
        log.emit("mempool", "ingress", n=len(out), sample=out[0])
    return out
