"""Wrapper around bitcoind JSON-RPC (cookie auth). Stdlib only."""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from typing import Any

from .config import Config


class BitcoinRPCError(RuntimeError):
    pass


class Bitcoin:
    """Thin JSON-RPC client. The rest of the app never speaks HTTP to bitcoind."""

    def __init__(self, cfg: Config):
        self._url = cfg.rpc_url
        self._cookie = cfg.bitcoin_cookie

    def _auth(self) -> str:
        try:
            raw = self._cookie.read_text(encoding="utf-8").strip()
        except OSError as e:
            raise BitcoinRPCError(f"cannot read RPC cookie {self._cookie}") from e
        return "Basic " + base64.b64encode(raw.encode()).decode()

    def call(self, method: str, *params: Any, timeout: float = 20) -> Any:
        payload = json.dumps(
            {"jsonrpc": "1.0", "id": "vox-templi", "method": method, "params": list(params)}
        ).encode()
        req = urllib.request.Request(
            self._url,
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": self._auth()},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            raise BitcoinRPCError(f"HTTP {e.code} {method}") from e
        except OSError as e:
            raise BitcoinRPCError(f"unreachable {self._url}") from e
        if body.get("error"):
            raise BitcoinRPCError(f"{method}: {body['error']}")
        return body.get("result")

    @staticmethod
    def sat_vb(btc_per_kvb: float | None) -> float | None:
        if not btc_per_kvb:
            return None
        return round(float(btc_per_kvb) * 1e8 / 1000.0, 2)
