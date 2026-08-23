#!/usr/bin/env python3
"""Minimal Bitcoin JSON-RPC via cookie auth. Stdlib only."""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

COOKIE = Path(os.environ.get("EM_COOKIE", "/home/bitcoin/.bitcoin/.cookie"))
RPC_URL = os.environ.get("EM_RPC_URL", "http://127.0.0.1:8332")


def _auth_header() -> str:
    raw = COOKIE.read_text(encoding="utf-8").strip()
    token = base64.b64encode(raw.encode()).decode()
    return f"Basic {token}"


def rpc(method: str, *params, timeout: float = 20):
    payload = json.dumps(
        {"jsonrpc": "1.0", "id": "embassy", "method": method, "params": list(params)}
    ).encode()
    req = urllib.request.Request(
        RPC_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": _auth_header(),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"RPC HTTP {e.code} {method}") from e
    if body.get("error"):
        raise RuntimeError(f"RPC {method}: {body['error']}")
    return body.get("result")


def sat_vb(btc_kvb: float | None) -> float | None:
    if not btc_kvb:
        return None
    return round(float(btc_kvb) * 1e8 / 1000.0, 2)
