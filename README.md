# Vox Templi

**A real-time mempool and block dashboard for your own Bitcoin node.**

Full screen, on the hardware you already have. Coffers in a bronze oculus fill as the mempool fills. A bolt leaves the center for each new transaction: bigger means more vbytes, hotter color means higher sat/vB. When a block is found, a ring of light travels from the oculus out to the edge of the screen. Height, tip, peer count, fees, halving distance, and hashrate sit on the rim, large enough to read from across the room. Space turns the sound on. Pitch follows your fees.

The dollar figure is not an exchange quote. [**UTXOracle**](https://utxo.live/), by Steve Jeffress ([@SteveSimple](https://twitter.com/SteveSimple)), reads output patterns in the UTXO set on **this** node and estimates a USD price from confirmed blocks alone. Vox Templi vendors that program unchanged and never calls an exchange API, or utxo.live, at runtime.

If something looks wrong with the node, the south wall says so in words: no peers, a stale tip, blocks stuck behind headers, initial block download, a mempool still loading off disk, or bitcoind not answering.

> **As-is.** No warranty and no guarantee of any kind, about the price, the health line, the fees, or anything else. Read [DISCLAIMER.md](DISCLAIMER.md) before you trust a number on this screen.

Open it in a browser at `http://127.0.0.1:8090/`, or let the HDMI kiosk take tty1.

## Public page

[`pages/index.html`](pages/index.html) is the same oculus, built as one static file for GitHub Pages. It does not talk to your node. Mempool size, new transactions, blocks, and fees come from the public [mempool.space](https://mempool.space/) API. The USD figure on that page is mempool.space’s published price. UTXOracle stays on the appliance, because a static page cannot read your UTXO set.

The public page still says when something looks wrong: the feed is down, the live socket dropped, the tip is old, the mempool is heavy, or fees are unusually high. Those flags describe the public network and the data source. They do not describe your node.

After this is on `main`, turn on Pages (Settings → Pages → Source: GitHub Actions). [`.github/workflows/pages.yml`](.github/workflows/pages.yml) publishes the `pages/` folder. The site will be at `https://realjuangalt.github.io/vox-templi/`.

```
bitcoind JSON-RPC  →  python -m vox_templi serve  →  cage + Chromium (tty1)
                              ↑
                   python -m vox_templi oracle   (hourly, cached)
                   python -m vox_templi history  (one settled UTC day at a time)
```

## What you see

| On screen | Source |
|-----------|--------|
| Mempool count, size, fill | `getmempoolinfo` on your node |
| Lightning bolts | new transactions since the last poll (vbytes, sat/vB) |
| Slow / mid / fast fee | `estimatesmartfee` 6, 3, and 1 |
| Height, tip hash, last-block age | `getblockchaininfo` + `getblockheader` |
| Ring of light | height went up |
| Peers and user-agent | `getnetworkinfo` |
| Halving distance, EH/s | chain height and `getmininginfo` |
| Sound | Web Audio. Mempool load sets the rhythm, fees set the pitch |
| USD | UTXOracle, local RPC only |

H opens a short legend. The page is one HTML file: canvas 2D and Web Audio, no WebGL, no build step.

## When the node looks wrong

The HUD does not stay green just because a number is on screen. `/api/status` carries a `health` object, and the south wall prints the flag text.

| Flag | Meaning |
|------|---------|
| `NO_PEERS` | Zero peers. The network path may be down. |
| `LOW_PEERS` | Fewer than two peers. |
| `IBD` | Still in initial block download, with a percent. |
| `BEHIND_HEADERS` | Three or more blocks behind the headers you already have. Twelve or more is treated as bad. |
| `STALE_TIP` | No block for 30 minutes (bad after two hours). Hidden during IBD, because a syncing node is expected to look old. |
| `MEMPOOL_LOADING` | bitcoind is still loading the mempool from disk. |
| `RPC_DOWN` / `RPC_ERROR` | bitcoind did not answer. |
| `RPC_SLOW` | This poll failed. The screen keeps the last good snapshot and says so. |
| `OK` | None of the above. |

A timed-out peer call is not displayed as zero peers. The last real peer count stays up until a real answer arrives.

## Price, from the UTXO set

Credit: **[UTXOracle](https://utxo.live/)** by **Steve Jeffress** ([@SteveSimple](https://twitter.com/SteveSimple)). Bitcoin Magazine wrote up the method [here](https://bitcoinmagazine.com/technical/a-new-trustless-way-to-calculate-the-bitcoin-price). The program looks at amounts in the UTXO set, on your node, and finds the USD price those amounts imply. Same confirmed blocks, same script, same integer.

Vox Templi shows two results, under the names in [UTXOracle’s license](vendor/UTXORACLE_LICENSE.md):

- **UTXOracle Block Window Price** — the last 144 confirmed blocks. `python3 -m vox_templi oracle`, and hourly via `vox-oracle.timer`.
- **UTXOracle Consensus Price** — one settled UTC day. `python3 -m vox_templi history`, backfilled locally. Same UTC day means the same integer on every node that runs this script.

The page repaints every few seconds so height, fees, and health stay live. The USD number updates when those jobs finish, not from the mempool and not from an exchange. Until the first scan has been written, the glyphs scramble and the label says the oracle is still warming up.

Upstream terms live in `vendor/UTXORACLE_LICENSE.md`. The price logic in `vendor/UTXOracle.py` is vendored unmodified. Local, non-commercial use of those two prices is what this dashboard does. Commercial use, a streaming live price, and renaming the output are the author’s to license. Read that file before you ship a product on top of it.

## Name

**Vox Templi** — Latin for *voice of the temple*. The picture is a tholos: coffers, oculus, sky. The sound continues the idea of [Proof of Sound](https://www.proofofsound.co.za/). This repository is not a fork of that page.

## Requirements

A machine you control, next to a node you control.

- Linux with systemd, for the install script
- bitcoind with `server=1` and cookie auth, on this host (synced, or at least catching up)
- Python 3.11+ (stdlib only, no pip)
- Optional HDMI kiosk: `cage`, Chromium, ALSA, on `tty1`

A browser on the same machine is enough if you skip the kiosk. GPU, Fulcrum, and an internet connection after IBD are not required.

Keep `VOX_BIND=127.0.0.1`. The HTTP API has **no authentication**. `/api/status` is your node’s height, peers, and mempool. See [SECURITY.md](SECURITY.md).

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

The Chromium package may be named `chromium-browser`. Skip `cage` if you only want the page in a normal browser.

### 2. bitcoind

`bitcoin.conf` needs at least:

```
server=1
```

Cookie auth is the default (`~/.bitcoin/.cookie` for the user that runs bitcoind). Vox Templi reads that file. It does not need `rpcuser` / `rpcpassword`.

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

That copies the tree to `/opt/vox-templi`, installs systemd units, writes `/etc/vox-templi/env` from the example if it is missing, and starts `vox-templi.service`.

From another machine:

```bash
git clone https://github.com/realjuangalt/vox-templi.git
cd vox-templi
VOX_DEPLOY_HOST=user@your-node ./scripts/deploy.sh
```

`VOX_DEPLOY_HOST` is required. It is never stored in the repo.

### 4. Point at your RPC cookie

```bash
sudo chmod 600 /etc/vox-templi/env
sudo $EDITOR /etc/vox-templi/env
```

Set `VOX_BITCOIN_COOKIE` to a cookie file this service can read:

```
VOX_BITCOIN_COOKIE=/home/bitcoin/.bitcoin/.cookie
```

Then:

```bash
sudo systemctl restart vox-templi
curl -sS http://127.0.0.1:8090/healthz
```

Open http://127.0.0.1:8090/ . **Space** toggles sound. **H** toggles the legend.

Quick run without systemd, from a checkout:

```bash
export VOX_BITCOIN_COOKIE=~/.bitcoin/.cookie
python3 -m vox_templi status
python3 -m vox_templi serve
```

### 5. Optional HDMI kiosk

The kiosk unit runs as user `kiosk` (video, audio, seat, render). Create that user, or reuse one:

```bash
sudo useradd --system --home /var/lib/vox-templi --create-home kiosk
sudo usermod -aG video,render,input,audio,seat kiosk
```

```bash
sudo VOX_KIOSK_USER=youruser ./scripts/install.sh
sudo systemctl enable --now vox-kiosk
```

It takes **tty1** (it conflicts with `getty@tty1`). Plug HDMI in before starting it.

If cage crash-loops (`No DRM devices found`, black screen, restart every few seconds), the compositor is on the wrong DRM card. This shows up often when a board has both a 3D device and an HDMI device, including many Raspberry Pi layouts. The kiosk script tries to pick the connected HDMI connector automatically. To pin it:

```bash
ls -l /sys/class/drm
sudo install -D -m 644 /opt/vox-templi/systemd/kiosk-drm.example.conf \
  /etc/systemd/system/vox-kiosk.service.d/drm.conf
sudo $EDITOR /etc/systemd/system/vox-kiosk.service.d/drm.conf
sudo systemctl daemon-reload
sudo systemctl restart vox-kiosk
```

Set `WLR_DRM_DEVICES` to the card that owns HDMI, and `VOX_OUTPUT` to that connector (`HDMI-A-1`, `HDMI-A-2`, …).

### 6. Oracle and daily history

```bash
sudo systemctl start vox-oracle.service     # first 144-block price; can take a while
python3 -m vox_templi history               # one missing UTC day
python3 -m vox_templi history --fill        # loop until yesterday is filled
```

[`data/utxoracle-daily.json`](data/utxoracle-daily.json) may ship with an empty `points` array. Each node fills history locally and does not recompute a date it already has. Earliest date the algorithm supports: `2023-12-15`.

## Config

Copy `config.example.env` to `/etc/vox-templi/env` and `chmod 600`. Do not commit a filled copy.

| Variable | Default | Meaning |
|----------|---------|---------|
| `VOX_BITCOIN_COOKIE` | `~/.bitcoin/.cookie` | bitcoind RPC cookie path |
| `VOX_RPC_URL` | `http://127.0.0.1:8332` | JSON-RPC |
| `VOX_BIND` | `127.0.0.1` | HTTP listen address |
| `VOX_PORT` | `8090` | HTTP port |
| `VOX_POLL` | `8` | Seconds between snapshots |
| `VOX_ALSA_DEVICE` | `plughw:0,0` | Kiosk sound device |
| `VOX_OUTPUT` | unset | `wlr-randr` connector, if you pin HDMI |

## Logging

JSON lines at `$VOX_STATE_DIR/vox.log` (default `/var/lib/vox-templi/vox.log`). RPC slowness, snapshots, health changes, oracle runs. Cookie values are not logged.

When the file exceeds `VOX_LOG_MAX_BYTES` (default 16 MiB) it is cut to the last half. Set `VOX_LOG_FOREVER=1` to keep growing it.

```bash
tail -f /var/lib/vox-templi/vox.log
curl -sS http://127.0.0.1:8090/api/log
```

## For agents

[AGENTS.md](AGENTS.md) is the local integration guide: commands, files, the price rule, the health flags, and what must never be committed.

## Layout

```
vox_templi/     Python package (config, RPC, collect, httpd, oracle, history)
wrappers/       ALSA, cage, Chromium
www/            oculus + rim HUD
systemd/        vox-templi, vox-oracle.timer, vox-history.timer, vox-kiosk
scripts/        install.sh (on-box), deploy.sh (rsync over SSH)
vendor/         UTXOracle.py 9.1, NOTICE, and the upstream license
```

## License

Vox Templi itself is [MIT](LICENSE). That license, and [DISCLAIMER.md](DISCLAIMER.md), are the whole promise: the software is provided as-is, with no warranty.

`vendor/UTXOracle.py` is Steve Jeffress’s program. Its license is not MIT. The text is in [vendor/UTXORACLE_LICENSE.md](vendor/UTXORACLE_LICENSE.md). Keep that file with the script if you redistribute it.

Vulnerability reports: [SECURITY.md](SECURITY.md). That file is the reporting policy, not a security review.
