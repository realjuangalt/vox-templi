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


def _stub_conf(cfg: Config) -> None:
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


def invoke(cfg: Config, extra_args: list[str], timeout: int | None = None) -> tuple[int | None, str, int]:
    """Run UTXOracle; return (usd, combined_output, returncode). Isolated from HTTP."""
    _stub_conf(cfg)
    args = ["UTXOracle.py", "-p", str(cfg.bitcoin_conf_stub.parent), *extra_args]
    runner = f"""
import webbrowser, runpy, sys, os
webbrowser.open = lambda *a, **k: False
webbrowser.open_new = webbrowser.open
webbrowser.open_new_tab = webbrowser.open
os.chdir({str(cfg.state_dir)!r})
sys.argv = {args!r}
ns = runpy.run_path({str(cfg.vendor_oracle)!r})
print("VOX_PRICE", int(ns.get("central_price") or 0))
"""
    proc = subprocess.run(
        [sys.executable, "-c", runner],
        capture_output=True,
        text=True,
        timeout=timeout or int(os.environ.get("VOX_ORACLE_TIMEOUT", "2400")),
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        cwd=str(cfg.state_dir),
    )
    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    return _parse_price(text), text, proc.returncode


def _write(cfg: Config, payload: dict) -> dict:
    cfg.state_dir.mkdir(parents=True, exist_ok=True)
    tmp = cfg.oracle_json.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(cfg.oracle_json)
    log.emit(
        "oracle",
        payload.get("state") or "?",
        **{k: payload[k] for k in ("usd", "kind", "note", "returncode") if k in payload},
    )
    return payload


def run(cfg: Config) -> dict:
    if not cfg.vendor_oracle.is_file():
        return _write(cfg, {
            "state": "error", "usd": None, "kind": "missing-script",
            "note": "UTXOracle.py not found", "computing": False,
        })
    if not cfg.bitcoin_cookie.is_file():
        return _write(cfg, {
            "state": "error", "usd": None, "kind": "missing-cookie",
            "note": "bitcoin RPC cookie not readable", "computing": False,
        })

    cfg.state_dir.mkdir(parents=True, exist_ok=True)
    prev: dict = {}
    if cfg.oracle_json.is_file():
        try:
            prev = json.loads(cfg.oracle_json.read_text(encoding="utf-8"))
        except Exception:
            prev = {}
    _write(cfg, {
        **prev,
        "state": "warming",
        "kind": "running",
        "computing": True,
        "note": "scanning last 144 blocks",
    })
    log.emit("oracle", "start", script=str(cfg.vendor_oracle))
    started = time.time()
    try:
        usd, text, rc = invoke(cfg, ["-rb"])
    except subprocess.TimeoutExpired:
        return _write(cfg, {
            "state": "error", "usd": prev.get("usd"), "kind": "timeout",
            "note": "oracle scan timed out", "computing": False,
        })
    except OSError as e:
        return _write(cfg, {
            "state": "error", "usd": prev.get("usd"), "kind": "spawn",
            "note": str(e), "computing": False,
        })
    cfg.oracle_log.write_text(text[-80_000:], encoding="utf-8")
    kind = "ok" if usd else "no-price"
    if rc not in (0, None) and not usd:
        kind = f"exit-{rc}"
    return _write(cfg, {
        "state": "ok" if usd else "error",
        "usd": usd if usd else prev.get("usd"),
        "as_of": int(time.time()),
        "elapsed_s": int(time.time() - started),
        "mode": "last-144-blocks",
        "lock": "STRONG" if usd else "NONE",
        "kind": kind,
        "computing": False,
        "note": "on-chain implied USD (UTXOracle, this node)" if usd else "scan finished but no USD parsed",
        "returncode": rc,
    })
