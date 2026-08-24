# UTXOracle daily prices

`utxoracle-daily.json` is a **canonical, deterministic** series: one USD integer per UTC day, produced by vendored `UTXOracle.py` 9.1 against settled blocks. Any node running the same script for the same date should match.

- Earliest date the algorithm supports: `2023-12-15`
- Format: `{"v":1,"algo":"UTXOracle-9.1","points":[{"d":"YYYY-MM-DD","usd":12345}]}`
- Points are never overwritten. The node only **appends days after the last bundled date**.

Build or extend (needs local bitcoind RPC):

```bash
python3 -m vox_templi history          # one missing day
python3 -m vox_templi history --fill    # loop until yesterday is filled
```

Then copy `$VOX_STATE_DIR/history.json` points into this file and commit.
