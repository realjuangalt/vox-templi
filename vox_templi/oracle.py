"""Wrapper around vendored UTXOracle.py. No browser, no utxo.live."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time

from .config import Config
from . import log


def _parse_price(text: str) -> int | None:
    m = re.search(r"VOX_PRICE\s+([0-9]+)", text)
    if m:
        n = int(m.group(1))
        return n if n > 0 else None
    hits = re.findall(r"\$\s*([0-9][0-9,]*)", text)
    if not hits:
        return None
    return int(hits[-1].replace(",", ""))


def _write(cfg: Config, payload: dict) -> dict:
    cfg.state_dir.mkdir(parents=True, exist_ok=True)
    tmp = cfg.oracle_json.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(cfg.oracle_json)
    log.emit("oracle", payload.get("state") or "?", **{k: payload[k] for k in ("usd", "kind", "note", "returncode") if k in payload})
    return payload


def run(cfg: Config) -> dict:
    if not cfg.vendor_oracle.is_file():
        return _write(cfg, {
            "state": "error", "usd": None, "kind": "missing-script",
            "note": "UTXOracle.py not found",
        })
    if not cfg.bitcoin_cookie.is_file():
        return _write(cfg, {
            "state": "error", "usd": None, "kind": "missing-cookie",
            "note": "bitcoin RPC cookie not readable",
        })

    cfg.state_dir.mkdir(parents=True, exist_ok=True)
    stub = cfg.bitcoin_conf_stub
    stub.parent.mkdir(parents=True, exist_ok=True)
    stub.write_text(
        "\n".join(
            [
                "rpcconnect=127.0.0.1",
                "rpcport=8332",
                f"rpccookiefile={cfg.bitcoin_cookie}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    # -rb never prints "$…"; we pull central_price from the module namespace.
    runner = f"""
import webbrowser, runpy, sys, os
webbrowser.open = lambda *a, **k: False
webbrowser.open_new = webbrowser.open
webbrowser.open_new_tab = webbrowser.open
os.chdir({str(cfg.state_dir)!r})
sys.argv = {['UTXOracle.py', '-p', str(stub.parent), '-rb']!r}
ns = runpy.run_path({str(cfg.vendor_oracle)!r})
print("VOX_PRICE", int(ns.get("central_price") or 0))
"""
    log.emit("oracle", "start", cookie=str(cfg.bitcoin_cookie), script=str(cfg.vendor_oracle))
    started = time.time()
    try:
        proc = subprocess.run(
        [sys.executable, "-c", runner],
        capture_output=True,
        text=True,
        timeout=int(os.environ.get("VOX_ORACLE_TIMEOUT", "2400")),
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        cwd=str(cfg.state_dir),
        )
    except subprocess.TimeoutExpired:
        return _write(cfg, {
            "state": "error", "usd": None, "kind": "timeout",
            "note": "oracle scan timed out",
        })
    except OSError as e:
        return _write(cfg, {
            "state": "error", "usd": None, "kind": "spawn",
            "note": str(e),
        })
    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    cfg.oracle_log.write_text(text[-80_000:], encoding="utf-8")
    usd = _parse_price(text)
    kind = "ok" if usd else "no-price"
    if proc.returncode not in (0, None) and not usd:
        kind = f"exit-{proc.returncode}"
    payload = {
        "state": "ok" if usd else "error",
        "usd": usd,
        "as_of": int(time.time()),
        "elapsed_s": int(time.time() - started),
        "mode": "last-144-blocks",
        "lock": "STRONG" if usd else "NONE",
        "kind": kind,
        "note": "on-chain implied USD (UTXOracle, this node)" if usd else "scan finished but no USD parsed",
        "returncode": proc.returncode,
    }
    return _write(cfg, payload)
