"""Wrapper around vendored UTXOracle.py. No browser, no utxo.live."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time

from .config import Config


def _parse_price(text: str) -> int | None:
    m = re.search(r"VOX_PRICE\s+([0-9]+)", text)
    if m:
        n = int(m.group(1))
        return n if n > 0 else None
    hits = re.findall(r"\$\s*([0-9][0-9,]*)", text)
    if not hits:
        return None
    return int(hits[-1].replace(",", ""))


def run(cfg: Config) -> dict:
    if not cfg.vendor_oracle.is_file():
        raise FileNotFoundError(cfg.vendor_oracle)
    if not cfg.bitcoin_cookie.is_file():
        raise FileNotFoundError(cfg.bitcoin_cookie)

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
    started = time.time()
    proc = subprocess.run(
        [sys.executable, "-c", runner],
        capture_output=True,
        text=True,
        timeout=int(os.environ.get("VOX_ORACLE_TIMEOUT", "2400")),
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        cwd=str(cfg.state_dir),
    )
    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    cfg.oracle_log.write_text(text[-80_000:], encoding="utf-8")
    usd = _parse_price(text)
    payload = {
        "state": "ok" if usd else "error",
        "usd": usd,
        "as_of": int(time.time()),
        "elapsed_s": int(time.time() - started),
        "mode": "last-144-blocks",
        "lock": "STRONG" if usd else "NONE",
        "note": "on-chain implied USD (UTXOracle, this node)",
        "returncode": proc.returncode,
    }
    tmp = cfg.oracle_json.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(cfg.oracle_json)
    return payload
