# Architecture

```
                   HDMI (1280×720)
                         │
                    cage (Wayland)
                         │
                    Chromium kiosk
                         │  GET /
                         │  GET /api/status  (8s)
                         ▼
              embassy-monitor :127.0.0.1:8090
                    │              ▲
                    │              │ oracle.json (hourly)
                    ▼              │
              bitcoind RPC    UTXOracle.py -rb
              cookie auth     last 144 blocks
```

Sound is synthesized in the page (Web Audio). Kick/hats follow mempool fill; pitch follows fee; a new block is a hit plus an expanding ring in the oculus.

Coffers lighting up = mempool pressure. Oculus brightness = time since last block. Rim labels = RPC snapshot.
