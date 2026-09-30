# Local integration guide for AI agents

You are installing or modifying **Vox Templi** on a machine the user controls. It is a local, real-time mempool and block dashboard for their Bitcoin full node. It also shows when that node looks unhealthy, and a USD estimate from the UTXO set via [UTXOracle](https://utxo.live/) (Steve Jeffress, @SteveSimple). It does not call an exchange API.

Read `DISCLAIMER.md` before you tell the user the numbers are trustworthy. They are not guaranteed.

## What “done” looks like

From the repo root, with a readable bitcoind cookie and `server=1`:

```bash
export VOX_BITCOIN_COOKIE=~/.bitcoin/.cookie
export VOX_BIND=127.0.0.1
export VOX_PORT=8090
python3 -m vox_templi status
python3 -m vox_templi serve
```

`status` prints one JSON snapshot and exits. `serve` listens on `http://127.0.0.1:8090/`. `curl -sS http://127.0.0.1:8090/healthz` returns `ok`. The page at `/` is the dashboard. `/api/status` is the same snapshot the page polls every 8 seconds.

Python 3.11+ standard library only. Do not add a `requirements.txt` or pip packages.

## Layout

| Path | Role |
|------|------|
| `www/index.html` | The dashboard: oculus, HUD, Web Audio. Polls `/api/status`. |
| `vox_templi/collect.py` | One snapshot: chain, mempool, fees, health flags, cached price. |
| `vox_templi/bitcoin.py` | Cookie-auth JSON-RPC. The rest of the app must not HTTP bitcoind itself. |
| `vox_templi/mempool_watch.py` | New mempool transactions since the last poll (vsize, sat/vB). |
| `vox_templi/oracle.py` | Runs vendored `vendor/UTXOracle.py -rb` (last 144 blocks). |
| `vox_templi/history.py` | One settled UTC day per run, appended locally. |
| `vox_templi/httpd.py` | Static files plus `/api/status`, `/api/log`, `/healthz`. |
| `vox_templi/config.py` | Every knob comes from the environment. |
| `config.example.env` | Template for `/etc/vox-templi/env`. |
| `scripts/install.sh` | On-box install to `/opt/vox-templi` and systemd. |
| `scripts/deploy.sh` | `rsync` over SSH. `VOX_DEPLOY_HOST` is required. Never hardcode a host. |
| `vendor/UTXOracle.py` | Upstream 9.1, unmodified price logic. |
| `vendor/UTXORACLE_LICENSE.md` | Upstream terms. Keep this file with the script. |
| `systemd/` | `vox-templi` (HTTP), `vox-oracle.timer` (hourly), `vox-history.timer`, `vox-kiosk`. |

`docs/ARCHITECTURE.md` is the one-screen picture.

## Commands

```bash
python3 -m vox_templi status          # one snapshot
python3 -m vox_templi serve           # dashboard + poller
python3 -m vox_templi oracle          # UTXOracle Block Window Price (slow)
python3 -m vox_templi history         # one missing UTC day
python3 -m vox_templi history --fill  # walk back to 2023-12-15; long
```

Systemd equivalents, after `sudo ./scripts/install.sh`:

```bash
sudo systemctl restart vox-templi
sudo systemctl start vox-oracle.service
sudo systemctl start vox-history.service
```

The oracle and history jobs are heavy RPC reads. Do not start them in a tight loop.

## Price rule

The USD figure comes from UTXOracle on this node.

- Last 144 confirmed blocks: **UTXOracle Block Window Price** (`python3 -m vox_templi oracle`, about hourly under systemd).
- A settled UTC day: **UTXOracle Consensus Price** (`python3 -m vox_templi history`).

Use those names on screen and in docs when the vendored script’s price logic is unchanged. Link [utxo.live](https://utxo.live/) and name Steve Jeffress (@SteveSimple).

Do not add CoinGecko, Kraken, mempool.space, or any other exchange or price HTTP API to the node appliance. The static site in `pages/` is the only place that calls mempool.space. Leave that split alone. Do not point the oracle at mempool transactions. Do not edit the filtering or averaging inside `vendor/UTXOracle.py`. Adapting RPC paths in `vox_templi/oracle.py` is fine. Changing UTXOracle’s price math means you must stop calling the result a UTXOracle price (see `vendor/UTXORACLE_LICENSE.md`).

The number on the wall is a cached result. The page refreshes every 8 seconds so height, fees, and health stay current. The price itself moves when the oracle or history job writes, not on every poll.

## Health flags

`collect.health_flags` is what tells the user something looks wrong. Surface these strings; do not hide them behind a generic “error”.

| Code | When |
|------|------|
| `NO_PEERS` | 0 peers |
| `LOW_PEERS` | fewer than 2 peers |
| `IBD` | initial block download |
| `BEHIND_HEADERS` | 3+ blocks behind headers (bad at 12+) |
| `STALE_TIP` | tip older than 30 minutes (bad after 2 hours), except during IBD |
| `MEMPOOL_LOADING` | `getmempoolinfo` reports not loaded |
| `RPC_DOWN` / `RPC_ERROR` | bitcoind not answering |
| `RPC_SLOW` | this poll failed and the HUD is showing the last good snapshot |
| `OK` | none of the above |

A failed `getnetworkinfo` must not be stored as 0 peers. That bug was already fixed; do not regress it.

## Secrets and this machine

Do not commit, print, or paste:

- `.cookie` files or `rpcpassword`
- `/etc/vox-templi/env` after it has been filled in
- `vox.log`, `oracle.log`, `status.json` from a live node
- SSH destinations, hostnames, LAN IPs, or hardware serials

`VOX_BIND` stays `127.0.0.1` unless the user explicitly asks for something else and understands `/api/status` has no auth. `deploy.sh` must keep requiring `VOX_DEPLOY_HOST`. Do not put a personal host back into the tree.

Cookie path, RPC URL, port, ALSA device, and HDMI connector are environment variables. Defaults in `config.py` are generic (`~/.bitcoin/.cookie`, `127.0.0.1`).

## Dashboard behavior worth preserving

- Coffers fill with mempool load. A new transaction is a bolt: size is vbytes, color is sat/vB.
- A new block is a ring of light from the oculus to the edge of the screen.
- Pitch follows fees. Space toggles sound. H toggles the explainer.
- South wall: price, then health flags.
- Canvas 2D and Web Audio only. Do not add WebGL, Tone.js, or a frontend build step.

## Checks after a change

```bash
python3 -m compileall -q vox_templi
python3 -m vox_templi status
```

If bitcoind is absent, `status` should fail clearly (cookie missing or RPC unreachable), not invent peers or a price. With a browser, open `http://127.0.0.1:8090/`, confirm height and mempool match `bitcoin-cli getblockchaininfo` / `getmempoolinfo`, and confirm a stopped bitcoind surfaces `RPC_DOWN` or `RPC_SLOW` instead of a fake healthy node.
