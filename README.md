# Vox Templi

**Voice of the temple.** A sounding oracle for a Bitcoin full node.

HDMI kiosk: look up into a Greco-futurist oculus. Coffers fill from **your mempool**. Light in the hole is the chain tip. Pitch follows local fees. USD on the south wall is **UTXOracle** over the last 144 blocks on **this** node.

No mempool.space. No price HTTP API. No Tone.js. No WebGL.

```
bitcoind JSON-RPC  →  python -m vox_templi serve  →  cage + Chromium (tty1)
                              ↑
                   python -m vox_templi oracle   (hourly, cached)
```

## What this is

Not a node. The room that sits on one.

| In this repo | Not in this repo |
|--------------|------------------|
| Viz, Web Audio, oracle cache, kiosk wrappers | bitcoind / Fulcrum / electrs |
| Wrappers around Chromium, cage, ALSA, RPC | Those programs themselves |
| Successor *idea* to Proof of Sound | A fork of that Tone.js page |

## Name

**Vox Templi** — Latin for *voice of the temple*. Sound (the lineage from Proof of Sound) plus the building (Pantheon / tholos / oracle).

## Dependencies (wrapped, not vendored)

| External | Wrapper |
|----------|---------|
| bitcoind (`server=1`, cookie auth) | `vox_templi.bitcoin.Bitcoin` |
| UTXOracle.py | `vox_templi.oracle` |
| Chromium | `wrappers/chromium.sh` |
| cage | `wrappers/kiosk.sh` |
| ALSA | `wrappers/alsa.sh` |
| Python 3.11+ | stdlib only — no pip |

Not required: GPU, internet after IBD, Fulcrum, Pulse/PipeWire.

## Config

Copy `config.example.env` to `/etc/vox-templi/env`. The git tree has **no hostnames, usernames, or site paths**.

```bash
export VOX_BITCOIN_COOKIE=~/.bitcoin/.cookie
python3 -m vox_templi status
python3 -m vox_templi serve
python3 -m vox_templi oracle
```

## Install

```bash
VOX_DEPLOY_HOST=your-node ./scripts/deploy.sh
# first time: edit /etc/vox-templi/env
# kiosk user (video/audio/seat):
#   mkdir -p /etc/systemd/system/vox-kiosk.service.d
#   echo -e '[Service]\nUser=kiosk\nGroup=kiosk' > .../override.conf
```

**Space** toggles sound.

Daily prices live in [`data/utxoracle-daily.json`](data/utxoracle-daily.json). Same UTC day ⇒ same integer USD on every node (UTXOracle 9.1 on settled blocks). The node **does not recompute** dates already in that file; it only appends newer days.

```bash
python3 -m vox_templi history         # one missing day
python3 -m vox_templi history --fill   # backfill until yesterday
python3 -m vox_templi history --export  # rewrite the bundled JSON
```

## Logging

JSON lines at `$VOX_STATE_DIR/vox.log` (default `/var/lib/vox-templi/vox.log`). RPC in/out, snapshots, oracle runs.

When the file exceeds `VOX_LOG_MAX_BYTES` (default 2 MiB) it is cut to the last half. Set `VOX_LOG_FOREVER=1` to never shrink.

```bash
tail -f /var/lib/vox-templi/vox.log
curl -sS http://127.0.0.1:8090/api/log
```

## Layout

```
vox_templi/     Python package (config, RPC, collect, httpd, oracle)
wrappers/       ALSA, cage, Chromium
www/            oculus + rim HUD
systemd/        vox-templi, vox-oracle.timer, vox-kiosk
vendor/         UTXOracle.py 9.1 (RPC only) + NOTICE
```

## License

MIT for Vox Templi. UTXOracle: `vendor/NOTICE`.
