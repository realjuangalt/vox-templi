"""Runtime config from environment. No hostnames, users, or site paths."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _path(key: str, default: Path) -> Path:
    raw = os.environ.get(key)
    return Path(raw).expanduser() if raw else default


@dataclass(frozen=True)
class Config:
    """All knobs. Defaults are generic; override with env or /etc/vox-templi/env."""

    bitcoin_cookie: Path
    rpc_url: str
    bind: str
    port: int
    poll_s: float
    state_dir: Path
    www: Path
    vendor_oracle: Path
    prefix: Path
    alsa_device: str
    kiosk_url: str
    chromium_profile: Path
    log_path: Path
    log_max_bytes: int
    log_forever: bool

    @classmethod
    def load(cls) -> Config:
        state = _path("VOX_STATE_DIR", Path("/var/lib/vox-templi"))
        prefix = _path("VOX_PREFIX", ROOT)
        port = int(os.environ.get("VOX_PORT", "8090"))
        bind = os.environ.get("VOX_BIND", "127.0.0.1")
        return cls(
            bitcoin_cookie=_path("VOX_BITCOIN_COOKIE", Path.home() / ".bitcoin" / ".cookie"),
            rpc_url=os.environ.get("VOX_RPC_URL", "http://127.0.0.1:8332"),
            bind=bind,
            port=port,
            poll_s=float(os.environ.get("VOX_POLL", "8")),
            state_dir=state,
            www=_path("VOX_WWW", prefix / "www"),
            vendor_oracle=_path("VOX_ORACLE_SCRIPT", prefix / "vendor" / "UTXOracle.py"),
            prefix=prefix,
            alsa_device=os.environ.get("VOX_ALSA_DEVICE", "plughw:0,0"),
            kiosk_url=os.environ.get("VOX_KIOSK_URL", f"http://{bind}:{port}/"),
            chromium_profile=_path("VOX_CHROMIUM_PROFILE", state / "chromium"),
            log_path=_path("VOX_LOG_PATH", state / "vox.log"),
            log_max_bytes=int(os.environ.get("VOX_LOG_MAX_BYTES", str(2 * 1024 * 1024))),
            log_forever=os.environ.get("VOX_LOG_FOREVER", "0") in ("1", "true", "yes"),
        )

    @property
    def oracle_json(self) -> Path:
        return self.state_dir / "oracle.json"

    @property
    def oracle_log(self) -> Path:
        return self.state_dir / "oracle.log"

    @property
    def status_json(self) -> Path:
        return self.state_dir / "status.json"

    @property
    def bitcoin_conf_stub(self) -> Path:
        return self.state_dir / "btcconf" / "bitcoin.conf"

    @property
    def history_json(self) -> Path:
        return self.state_dir / "history.json"
