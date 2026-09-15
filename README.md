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

## Requirements

A **local appliance** on a machine you control:

- Linux with systemd
- A bitcoind with `server=1` and cookie auth on the same host (synced, or at least catching up)
- Python 3.11+ (stdlib only — no pip)
- Optional HDMI kiosk: `cage` + Chromium on `tty1`

Not required: GPU, internet after IBD, Fulcrum, Pulse/PipeWire.

Keep `VOX_BIND=127.0.0.1`. The HTTP API has **no authentication** and `/api/status` reflects your node (height, peers, mempool). Do not expose it to a LAN or the internet without a reverse proxy and auth.

## Install

### 1. Packages

**Arch / Omarchy / Alarm:**

```bash
sudo pacman -S --needed python chromium cage wlr-randr alsa-utils curl rsync
```

**Debian / Ubuntu:**

```bash
sudo apt install python3 chromium cage wlr-randr alsa-utils curl rsync
```

Chromium package name may be `chromium-browser` on some distros. `cage` is the Wayland kiosk compositor; skip it if you only want the HTTP UI in a normal browser.

### 2. bitcoind

`bitcoin.conf` needs at least:

```
server=1
```

Cookie auth is the default (`~/.bitcoin/.cookie` for the user that runs bitcoind). Vox Templi reads that file; it never needs `rpcuser` / `rpcpassword`.

Confirm RPC locally:

```bash
bitcoin-cli getblockchaininfo
```

### 3. Get the code and install units

On the node:

```bash
git clone https://github.com/realjuangalt/vox-templi.git
cd vox-templi
sudo ./scripts/install.sh
```

That copies the tree to `/opt/vox-templi`, installs systemd units, writes `/etc/vox-templi/env` from the example if missing, and starts `vox-templi.service`.

From another machine (SSH as root, or a user that can write those paths):

```bash
git clone https://github.com/realjuangalt/vox-templi.git
cd vox-templi
VOX_DEPLOY_HOST=root@your-node ./scripts/deploy.sh
```

`VOX_DEPLOY_HOST` is required for `deploy.sh`. It is never hardcoded.

### 4. Point at your RPC cookie

```bash
sudo chmod 600 /etc/vox-templi/env
sudo $EDITOR /etc/vox-templi/env
```

Set `VOX_BITCOIN_COOKIE` to the cookie file **this service can read**. Examples:

```
VOX_BITCOIN_COOKIE=/root/.bitcoin/.cookie
VOX_BITCOIN_COOKIE=/home/bitcoin/.bitcoin/.cookie
VOX_BITCOIN_COOKIE=~/.bitcoin/.cookie
```

Then:

```bash
sudo systemctl restart vox-templi
curl -sS http://127.0.0.1:8090/healthz
python3 -m vox_templi status   # from /opt/vox-templi, with PYTHONPATH set
```

Open http://127.0.0.1:8090/ in a browser. **Space** toggles sound.

### 5. Optional HDMI kiosk

The kiosk unit runs as user `kiosk` (video / audio / seat / render). Create that user, **or** override it:

```bash
sudo useradd --system --home /var/lib/vox-templi --create-home kiosk
sudo usermod -aG video,render,input,audio,seat kiosk   # skip groups that do not exist
```

```bash
# or reuse an existing local user
sudo VOX_KIOSK_USER=youruser ./scripts/install.sh
```

Enable and start:

```bash
sudo systemctl enable --now vox-kiosk
```

It takes over **tty1** (conflicts with `getty@tty1`). Plug HDMI in before starting it.

If cage crash-loops (`No DRM devices found`, black screen, or restart every few seconds), the compositor is bound to the wrong DRM card (common on Raspberry Pi: 3D vs HDMI). List connectors, then install the example drop-in and edit it:

```bash
ls -l /sys/class/drm
sudo install -D -m 644 /opt/vox-templi/systemd/kiosk-drm.example.conf \
  /etc/systemd/system/vox-kiosk.service.d/drm.conf
sudo $EDITOR /etc/systemd/system/vox-kiosk.service.d/drm.conf
sudo systemctl daemon-reload
sudo systemctl restart vox-kiosk
```

Set `WLR_DRM_DEVICES` to the card that owns the HDMI connector and `VOX_OUTPUT` to that connector name (`HDMI-A-1`, `HDMI-A-2`, …).

### 6. Oracle and daily history

Hourly UTXOracle (last 144 blocks on **this** node) and a slow daily backfill start with the timers.

```bash
sudo systemctl start vox-oracle.service     # first 144-block price (can take a while)
python3 -m vox_templi history               # one missing UTC day
python3 -m vox_templi history --fill        # loop until yesterday is filled
```

[`data/utxoracle-daily.json`](data/utxoracle-daily.json) may ship empty; each node fills history locally. Same UTC day ⇒ same integer USD. The node does not recompute dates it already has.

## Config

Copy `config.example.env` to `/etc/vox-templi/env` and `chmod 600`. Do not commit a filled copy.

| Variable | Default | Meaning |
|----------|---------|---------|
| `VOX_BITCOIN_COOKIE` | `~/.bitcoin/.cookie` | bitcoind RPC cookie path |
| `VOX_RPC_URL` | `http://127.0.0.1:8332` | JSON-RPC |
| `VOX_BIND` | `127.0.0.1` | HTTP listen address |
| `VOX_PORT` | `8090` | HTTP port |
| `VOX_ALSA_DEVICE` | `plughw:0,0` | Kiosk sound device |
| `VOX_OUTPUT` | unset | `wlr-randr` connector for kiosk |

Quick run without systemd:

```bash
export VOX_BITCOIN_COOKIE=~/.bitcoin/.cookie
export PYTHONPATH=/opt/vox-templi
python3 -m vox_templi status
python3 -m vox_templi serve
python3 -m vox_templi oracle
```

## Logging

JSON lines at `$VOX_STATE_DIR/vox.log` (default `/var/lib/vox-templi/vox.log`). RPC in/out, snapshots, oracle runs. Cookie **values** are not logged.

`/api/status` includes a `health` object with flags such as `NO_PEERS`, `STALE_TIP`, `BEHIND_HEADERS`, `IBD`, `MEMPOOL_LOADING`, and `RPC_DOWN`. The kiosk HUD shows these under the price (sync label, peer color, tip age color).

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
scripts/        install.sh (on-box), deploy.sh (rsync over SSH)
vendor/         UTXOracle.py 9.1 (RPC only) + NOTICE
```

## License

MIT for Vox Templi (see `LICENSE`).

`vendor/UTXOracle.py` is third-party (see `vendor/NOTICE`). Upstream ships no license file with the script. This project vendors it for **local, offline** use against your own bitcoind and does not call utxo.live at runtime. Before you redistribute that file on its own or change how it is used, check the author's terms at [utxo.live](https://utxo.live/).
