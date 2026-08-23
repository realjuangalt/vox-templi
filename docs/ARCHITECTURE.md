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

 python -m vox_templi oracle  (timer)
         wraps vendor/UTXOracle.py -rb
         writes $STATE_DIR/oracle.json
```

Wrappers keep third-party binaries behind a single script each (`wrappers/alsa.sh`, `chromium.sh`, `kiosk.sh`). The Python package never shells out to `bitcoin-cli`.
