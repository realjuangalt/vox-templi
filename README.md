# Tholos

**A sounding oracle for a Bitcoin full node.**

HDMI kiosk: you look *up* into a Greco-futurist oculus. Coffers fill with your mempool. Light through the hole is the chain tip. The room hums from **your** mempool, not a website. USD on the south inscription is **UTXOracle** — implied from this node’s last 144 blocks.

No mempool.space. No price API. No Tone.js. No WebGL.

```
bitcoind RPC  →  python collector :8090  →  cage + Chromium on tty1
                         ↑
              hourly UTXOracle.py -rb (cached JSON)
```

## What this is (and isn’t)

| This repo | Not this repo |
|-----------|----------------|
| The temple: viz, sound, oracle cache, kiosk | bitcoind itself |
| Local RPC client + a 12fps canvas | Electrum/Fulcrum (wallets can use those; Tholos doesn’t) |
| Spiritual successor to [Proof of Sound](https://www.proofofsound.co.za/) | A fork of that HTML/Tone.js stack |

You already run a node. Tholos is the thing you glance at instead of a login prompt.

## Name

**Tholos** — a round Greek temple. The picture is the Pantheon soffit: coffers, oculus, sky. Sound is the other half (Proof of Sound). Price is an **oracle** in the Greek sense: read from offerings on the chain, not from a priest in California.

Runners-up, if you hate it:

| Name | Why |
|------|-----|
| **Adyton** | Innermost room of an oracle temple. Only the node speaks. |
| **Oraculum** | The pronouncement. |
| **Cella** | Inner sanctum. |
| **Vox Templi** | Voice of the temple. |
| **Pantheon** | The building we drew. Crowded name. |
| **Kithara** | The instrument. Weak on “node + oracle.” |

Working copy on this machine is still `embassy-monitor/` until you create the GitHub repo. Rename the folder whenever.

## Dependencies

**Must already exist on the box**

| Piece | Why |
|-------|-----|
| **bitcoind** with `server=1`, cookie auth | All chain/mempool/fee data |
| **Python 3.11+** | Collector, oracle wrapper (stdlib only) |
| **Chromium** | Kiosk browser (Web Audio + canvas) |
| **cage** | Fullscreen Wayland compositor |
| **seatd** | seat for tty1 |
| **ALSA** | 3.5mm jack (PipeWire is *stopped* so Chromium can open the device) |

**Not required**

- mempool backend / mempool.space
- Fulcrum / electrs (unless you want wallets)
- GPU / WebGL
- Internet, after the node is synced
- pip packages

**Pi notes:** 4GB is enough if bitcoind is already tuned. Kiosk is capped at 700MB RAM, 120% CPU. Collector is ~150MB. First UTXOracle pass walks 144 raw blocks over RPC (~2–20 min). Then hourly.

## Layout

```
scripts/serve.py      HTTP :8090 + /api/status
scripts/collect.py    bitcoind snapshot
scripts/oracle.py     wraps vendor/UTXOracle.py -rb
scripts/kiosk.sh      cage + ALSA jack + Chromium
www/index.html        oculus + rim metrics + Web Audio
systemd/              monitor, oracle timer, kiosk
vendor/UTXOracle.py   upstream 9.1, RPC only
```

## Install (example: Arch ARM kiosk)

1. bitcoind running, cookie readable (this tree defaults to `/home/bitcoin/.bitcoin/.cookie`).
2. From a machine with ssh:

```bash
./scripts/deploy.sh          # HOST=your-node REMOTE=/opt/embassy-monitor
```

Units:

| Unit | Role |
|------|------|
| `embassy-monitor.service` | UI + JSON |
| `embassy-oracle.timer` | hourly implied USD |
| `embassy-kiosk.service` | cage/Chromium, **conflicts with getty@tty1** |

Env knobs: `EM_COOKIE`, `EM_PORT`, `EM_KIOSK_URL`, `EM_ALSA_DEVICE` (default `plughw:0,0`).

**Space** toggles sound.

## Credits

- Visual/audio *idea* lineage: Proof of Sound (Spotkolours / Gareth). Rebuilt from scratch for a Pi.
- Price algorithm: [UTXOracle](https://utxo.live/oracle/UTXOracle.py) (Clark Moody / utxo.live). We do not fetch their site.

## License

MIT for Tholos code. UTXOracle: see `vendor/NOTICE`.
