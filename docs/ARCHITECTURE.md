# Architecture

```
 tty1 HDMI
    cage  →  Chromium (Web Audio + canvas 2D, ~12 fps)
                 │
                 │  GET /  GET /api/status
                 ▼
         python -m vox_templi serve
                    │
         vox_templi.bitcoin.Bitcoin
                    │
               bitcoind cookie RPC

 python -m vox_templi oracle  (timer, about hourly)
         wraps vendor/UTXOracle.py -rb unchanged
         writes $STATE_DIR/oracle.json
         label: UTXOracle Block Window Price

 python -m vox_templi history (timer)
         one settled UTC day per run
         label: UTXOracle Consensus Price
```

`/api/status` includes `health.flags` (`NO_PEERS`, `STALE_TIP`, `BEHIND_HEADERS`, `IBD`, `MEMPOOL_LOADING`, `RPC_DOWN`, `RPC_SLOW`, …). The page prints those strings. Price jobs read confirmed blocks only.

Wrappers keep third-party binaries behind a single script each (`wrappers/alsa.sh`, `chromium.sh`, `kiosk.sh`). The Python package never shells out to `bitcoin-cli`.
