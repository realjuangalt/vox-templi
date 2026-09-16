"""Wrapper around bitcoind JSON-RPC (cookie auth). Stdlib only."""
from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from typing import Any

from .config import Config
from . import log


class BitcoinRPCError(RuntimeError):
    pass


class Bitcoin:
    """Thin JSON-RPC client. The rest of the app never speaks HTTP to bitcoind."""

    def __init__(self, cfg: Config):
        self._url = cfg.rpc_url
        self._cookie = cfg.bitcoin_cookie
        self._timeout = float(getattr(cfg, "rpc_timeout", 45) or 45)

    def _auth(self) -> str:
        try:
            raw = self._cookie.read_text(encoding="utf-8").strip()
        except OSError as e:
            raise BitcoinRPCError(f"cannot read RPC cookie {self._cookie}") from e
        return "Basic " + base64.b64encode(raw.encode()).decode()

    def call(self, method: str, *params: Any, timeout: float | None = None) -> Any:
        payload = json.dumps(
            {"jsonrpc": "1.0", "id": "vox-templi", "method": method, "params": list(params)}
        ).encode()
        req = urllib.request.Request(
            self._url,
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": self._auth()},
            method="POST",
        )
        if timeout is None:
            timeout = self._timeout
        t0 = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            log.emit(
                "rpc",
                "http error",
                method=method,
                code=e.code,
                ms=int((time.monotonic() - t0) * 1000),
            )
            raise BitcoinRPCError(f"HTTP {e.code} {method}") from e
        except OSError as e:
            log.emit(
                "rpc",
                "unreachable",
                method=method,
                err=str(e),
                ms=int((time.monotonic() - t0) * 1000),
            )
            raise BitcoinRPCError(f"unreachable {self._url}") from e
        ms = int((time.monotonic() - t0) * 1000)
        if body.get("error"):
            log.emit("rpc", "error", method=method, error=body["error"], ms=ms)
            raise BitcoinRPCError(f"{method}: {body['error']}")
        result = body.get("result")
        hint = type(result).__name__
        if isinstance(result, dict) and "blocks" in result:
            hint = f"blocks={result.get('blocks')}"
        elif isinstance(result, (list, dict)):
            hint = f"{type(result).__name__}[{len(result)}]"
        # Fast successes are noise; snapshot lines already have height/peers.
        if ms >= 2000:
            log.emit("rpc", "slow", method=method, ms=ms, out=hint)
        return result

    @staticmethod
    def sat_vb(btc_per_kvb: float | None) -> float | None:
        if not btc_per_kvb:
            return None
        return round(float(btc_per_kvb) * 1e8 / 1000.0, 2)
