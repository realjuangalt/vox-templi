"""Snapshot chain + mempool + cached oracle. Speaks only through Bitcoin wrapper."""
from __future__ import annotations

import json
import time
from pathlib import Path

from .bitcoin import Bitcoin, BitcoinRPCError
from .config import Config
from .mempool_watch import ingress
from . import log

# Tip / sync thresholds for kiosk health flags (seconds / block counts).
_STALE_WARN_S = 30 * 60
_STALE_BAD_S = 2 * 3600
_BEHIND_WARN = 3
_BEHIND_BAD = 12
_last_health_key: tuple | None = None


def _ingress(btc: Bitcoin) -> list:
    try:
        return ingress(btc)
    except Exception as e:
        log.emit("mempool", "ingress-fail", err=str(e))
        return []


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


def _feed(cfg: Config) -> dict:
    live = _oracle(cfg.oracle_json)
    hist: dict = {"points": []}
    if cfg.history_json.is_file():
        try:
            hist = json.loads(cfg.history_json.read_text(encoding="utf-8"))
        except Exception:
            hist = {"points": []}
    pts = hist.get("points") or []
    newest = max(pts, key=lambda p: p.get("d") or "") if pts else None
    computing = bool(hist.get("computing") or live.get("computing"))
    if newest and newest.get("usd"):
        return {
            "state": "ok",
            "usd": newest["usd"],
            "kind": "history",
            "source": "daily-history",
            "as_of_date": newest.get("d"),
            "n": len(pts),
            "computing": computing,
            "computing_date": hist.get("computing_date"),
            "note": "on-chain daily history · beyond last 144 blocks",
        }
    live = dict(live)
    live["source"] = "last-144"
    live["computing"] = computing or bool(live.get("computing"))
    if live.get("usd"):
        live["note"] = "last 144 blocks · daily history filling"
    return live


def _flag(code: str, level: str, text: str) -> dict:
    return {"code": code, "level": level, "text": text}


def health_flags(
    *,
    peers: int,
    behind: int,
    block_age_s: int,
    ibd: bool,
    progress: float,
    mempool_loaded: bool | None,
) -> dict:
    """Derive human-readable health flags for the kiosk HUD."""
    flags: list[dict] = []

    if peers < 0:
        pass
    elif peers <= 0:
        flags.append(_flag("NO_PEERS", "bad", "0 peers · network may be down"))
    elif peers < 2:
        flags.append(_flag("LOW_PEERS", "warn", f"{peers} peer · weak connectivity"))

    if ibd:
        flags.append(
            _flag("IBD", "warn", f"initial block download {(progress * 100):.2f}%")
        )

    if behind >= _BEHIND_BAD:
        flags.append(
            _flag(
                "BEHIND_HEADERS",
                "bad",
                f"{behind} blocks behind headers · catching up or stuck",
            )
        )
    elif behind >= _BEHIND_WARN:
        flags.append(_flag("BEHIND_HEADERS", "warn", f"{behind} blocks behind headers"))

    if block_age_s >= _STALE_BAD_S:
        hours = block_age_s // 3600
        flags.append(
            _flag(
                "STALE_TIP",
                "bad",
                f"tip age {hours}h · likely offline or not receiving blocks",
            )
        )
    elif block_age_s >= _STALE_WARN_S and not ibd:
        mins = block_age_s // 60
        flags.append(_flag("STALE_TIP", "warn", f"tip age {mins}m · no recent block"))

    if mempool_loaded is False:
        flags.append(_flag("MEMPOOL_LOADING", "warn", "mempool still loading from disk"))

    if not flags:
        flags.append(_flag("OK", "ok", "node healthy"))

    order = {"bad": 0, "warn": 1, "ok": 2}
    level = min((f["level"] for f in flags), key=lambda lv: order.get(lv, 9))
    return {"level": level, "flags": flags}


def health_from_error(note: str, *, had_snapshot: bool = False) -> dict:
    text = (note or "rpc unreachable").strip()
    low = text.lower()
    if "timed out" in low or "unreachable" in low or "connection" in low:
        if had_snapshot:
            return {
                "level": "warn",
                "flags": [
                    _flag(
                        "RPC_SLOW",
                        "warn",
                        "bitcoind RPC slow · showing last good snapshot",
                    )
                ],
            }
        code, level = "RPC_DOWN", "bad"
        text = "bitcoind RPC unreachable · node starting, overloaded, or down"
    else:
        code, level = "RPC_ERROR", "bad"
    return {"level": level, "flags": [_flag(code, level, text)]}


def _soft(btc: Bitcoin, method: str, *params, timeout: float | None = None):
    try:
        return btc.call(method, *params, timeout=timeout)
    except (BitcoinRPCError, OSError, ValueError, TypeError) as e:
        log.emit("rpc", "soft-fail", method=method, err=str(e))
        return None


def merge_status(prev: dict, incoming: dict) -> dict:
    """Keep last-good HUD fields when this poll is incomplete or failed."""
    incoming = restore_net(prev, incoming)
    if incoming.get("ok") and incoming.get("chain"):
        return incoming
    prev = prev or {}
    out = dict(prev)
    for k in ("chain", "net", "mempool", "oracle"):
        if incoming.get(k):
            out[k] = incoming[k]
    now = int(incoming.get("ts") or time.time())
    out["ok"] = False
    out["ts"] = now
    out["stale"] = True
    out["note"] = incoming.get("note") or prev.get("note") or "rpc slow"
    prev_flags = [
        f
        for f in ((prev.get("health") or {}).get("flags") or [])
        if f.get("code") not in ("OK", "RPC_DOWN", "RPC_SLOW", "RPC_ERROR", "STARTING")
    ]
    slow = health_from_error(out["note"], had_snapshot=bool(prev.get("chain")))
    flags = list(slow.get("flags") or []) + prev_flags
    if incoming.get("net") and int((incoming.get("net") or {}).get("peers") or 0) > 0:
        flags = [f for f in flags if f.get("code") not in ("NO_PEERS", "LOW_PEERS")]
    order = {"bad": 0, "warn": 1, "ok": 2}
    level = min((f["level"] for f in flags), key=lambda lv: order.get(lv, 9), default="warn")
    out["health"] = {"level": level, "flags": flags}
    return out


def restore_net(prev: dict, data: dict) -> dict:
    """Do not let a failed getnetworkinfo publish peers=0 over a live node."""
    incoming_net = data.get("net")
    if incoming_net is not None and incoming_net.get("peers") is not None:
        return data
    prev_net = (prev or {}).get("net")
    if not prev_net:
        return data
    data = dict(data)
    data["net"] = prev_net
    peers = int(prev_net.get("peers") or 0)
    if peers > 0:
        flags = [
            f
            for f in ((data.get("health") or {}).get("flags") or [])
            if f.get("code") not in ("NO_PEERS", "LOW_PEERS")
        ]
        if not flags:
            flags = [_flag("OK", "ok", "node healthy")]
        order = {"bad": 0, "warn": 1, "ok": 2}
        level = min((f["level"] for f in flags), key=lambda lv: order.get(lv, 9), default="ok")
        data["health"] = {"level": level, "flags": flags}
    return data


def snapshot(cfg: Config, btc: Bitcoin | None = None) -> dict:
    btc = btc or Bitcoin(cfg)
    now = int(time.time())
    # Peers first. A timeout must not be recorded as 0 connections.
    net = _soft(btc, "getnetworkinfo", timeout=15)
    if net is None:
        cnt = _soft(btc, "getconnectioncount", timeout=8)
        if cnt is not None:
            net = {
                "connections": int(cnt),
                "connections_in": 0,
                "connections_out": int(cnt),
                "subversion": "",
            }
    chain = _soft(btc, "getblockchaininfo", timeout=max(60.0, btc._timeout))
    mem = _soft(btc, "getmempoolinfo", timeout=10) if net is not None else None
    net_out = None
    peers = -1
    if isinstance(net, dict):
        peers = int(net.get("connections") or 0)
        net_out = {
            "peers": peers,
            "in": int(net.get("connections_in") or 0),
            "out": int(net.get("connections_out") or 0),
            "version": (net.get("subversion") or "").strip(),
        }
    if not chain:
        out = {
            "ok": False,
            "ts": now,
            "note": "getblockchaininfo timed out",
            "health": health_from_error("timed out", had_snapshot=False),
            "oracle": _feed(cfg),
        }
        if net_out is not None:
            out["net"] = net_out
        return out
    height = int(chain["blocks"])
    headers = int(chain.get("headers") or height)
    behind = max(0, headers - height)
    header = _soft(btc, "getblockheader", chain["bestblockhash"], timeout=12) or {}
    block_time = int(header.get("time") or 0)
    block_age = max(0, now - block_time) if block_time else 0
    mem = mem or {}
    mem_bytes = int(mem.get("bytes") or 0)
    mem_tx = int(mem.get("size") or 0)
    mem_cap = int(mem.get("maxmempool") or 300_000_000) or 300_000_000
    mempool_loaded = mem.get("loaded")
    if mempool_loaded is not None:
        mempool_loaded = bool(mempool_loaded)
    ibd = bool(chain.get("initialblockdownload"))
    progress = float(chain.get("verificationprogress") or 0)
    mining = _soft(btc, "getmininginfo", timeout=6) if net is not None else None
    mining = mining or {}
    health = health_flags(
        peers=peers,
        behind=behind,
        block_age_s=block_age,
        ibd=ibd,
        progress=progress,
        mempool_loaded=mempool_loaded,
    )
    busy = ibd or behind >= _BEHIND_WARN or mempool_loaded is False
    out = {
        "ok": True,
        "ts": now,
        "health": health,
        "chain": {
            "height": height,
            "headers": headers,
            "behind": behind,
            "hash": chain.get("bestblockhash"),
            "ibd": ibd,
            "progress": progress,
            "disk_gb": round(int(chain.get("size_on_disk") or 0) / 1e9, 1),
            "pruned": bool(chain.get("pruned")),
            "difficulty": float(mining.get("difficulty") or chain.get("difficulty") or 0),
            "nethash_eh": round(float(mining.get("networkhashps") or 0) / 1e18, 2),
            "block_time": block_time,
            "block_age_s": block_age,
            "next_halving_blocks": 210000 - (height % 210000),
        },
        "mempool": {
            "tx": mem_tx,
            "mb": round(mem_bytes / 1e6, 2),
            "usage_mb": round(int(mem.get("usage") or 0) / 1e6, 1),
            "fill": min(1.0, mem_bytes / mem_cap) if mem_cap else 0,
            "loaded": mempool_loaded,
            "min_sat_vb": Bitcoin.sat_vb(mem.get("mempoolminfee")),
            "fee_fast": None if busy else _fee(btc, 1),
            "fee_mid": None if busy else _fee(btc, 3),
            "fee_slow": None if busy else _fee(btc, 6),
            "ingress": [] if busy else _ingress(btc),
        },
        "oracle": _feed(cfg),
    }
    if net_out is not None:
        out["net"] = net_out
    ora = out["oracle"]
    flags = ",".join(f["code"] for f in health.get("flags") or [])
    log.emit(
        "snapshot",
        "ok",
        height=height,
        behind=behind,
        peers=peers,
        health=health.get("level"),
        flags=flags,
        mempool=mem_tx,
        oracle=ora.get("state"),
        usd=ora.get("usd"),
        oracle_kind=ora.get("kind"),
    )
    global _last_health_key
    key = (health.get("level"), flags, peers, behind)
    if key != _last_health_key:
        log.emit(
            "health",
            "change",
            level=health.get("level"),
            flags=flags,
            peers=peers,
            behind=behind,
            height=height,
        )
        _last_health_key = key
    return out


def write_snapshot(cfg: Config, data: dict) -> None:
    cfg.status_json.parent.mkdir(parents=True, exist_ok=True)
    tmp = cfg.status_json.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(cfg.status_json)
