#!/usr/bin/env python3
"""Run vendored UTXOracle against local bitcoind; cache USD + lock metadata.

Does not open a browser. Does not contact utxo.live.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "UTXOracle.py"
CONFDIR = Path(os.environ.get("EM_ORACLE_CONFDIR", "/var/lib/embassy-monitor/btcconf"))
COOKIE = Path(os.environ.get("EM_COOKIE", "/home/bitcoin/.bitcoin/.cookie"))
OUT = Path(os.environ.get("EM_ORACLE_JSON", "/var/lib/embassy-monitor/oracle.json"))
LOG = Path(os.environ.get("EM_ORACLE_LOG", "/var/lib/embassy-monitor/oracle.log"))


def stub_conf() -> Path:
    CONFDIR.mkdir(parents=True, exist_ok=True)
    (CONFDIR / "bitcoin.conf").write_text(
        "\n".join(
            [
                "rpcconnect=127.0.0.1",
                "rpcport=8332",
                f"rpccookiefile={COOKIE}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return CONFDIR


def parse_price(text: str) -> int | None:
    m = re.search(r"EM_PRICE\s+([0-9]+)", text)
    if m:
        n = int(m.group(1))
        return n if n > 0 else None
    hits = re.findall(r"\$\s*([0-9][0-9,]*)", text)
    if not hits:
        return None
    return int(hits[-1].replace(",", ""))


def lock_from_log(text: str, usd: int | None) -> str:
    if usd is None:
        return "NONE"
    if "could not" in text.lower() or "error" in text.lower()[:400]:
        return "WEAK"
    return "STRONG"


def main() -> int:
    if not VENDOR.exists():
        print("missing vendor/UTXOracle.py", file=sys.stderr)
        return 1
    if not COOKIE.exists():
        print(f"missing cookie {COOKIE}", file=sys.stderr)
        return 1
    conf = stub_conf()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # -rb (block window) never prints "$…"; price lives in central_price / HTML.
    work = OUT.parent
    work.mkdir(parents=True, exist_ok=True)
    runner = f"""
import webbrowser, runpy, sys, os
webbrowser.open = lambda *a, **k: False
webbrowser.open_new = webbrowser.open
webbrowser.open_new_tab = webbrowser.open
os.chdir({str(work)!r})
sys.argv = {['UTXOracle.py', '-p', str(conf), '-rb']!r}
ns = runpy.run_path({str(VENDOR)!r})
print("EM_PRICE", int(ns.get("central_price") or 0))
"""
    started = time.time()
    proc = subprocess.run(
        [sys.executable, "-c", runner],
        capture_output=True,
        text=True,
        timeout=int(os.environ.get("EM_ORACLE_TIMEOUT", "2400")),
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        cwd=str(work),
    )
    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    LOG.write_text(text[-80_000:], encoding="utf-8")
    usd = parse_price(text)
    payload = {
        "state": "ok" if usd else "error",
        "usd": usd,
        "as_of": int(time.time()),
        "elapsed_s": int(time.time() - started),
        "mode": "last-144-blocks",
        "lock": lock_from_log(text, usd),
        "note": "on-chain implied USD from this node (UTXOracle)",
        "returncode": proc.returncode,
    }
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(OUT)
    print(json.dumps(payload))
    return 0 if usd else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.TimeoutExpired:
        OUT.write_text(
            json.dumps({"state": "timeout", "usd": None, "lock": "NONE", "note": "oracle scan timed out"}),
            encoding="utf-8",
        )
        raise
