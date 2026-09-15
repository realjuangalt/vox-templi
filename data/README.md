# UTXOracle daily prices

`utxoracle-daily.json` holds an optional **bundled seed** of daily USD integers from vendored `UTXOracle.py` 9.1 on settled blocks. Same UTC day ⇒ same integer on every node that runs the same script.

The file in this repo may ship with an empty `points` array (schema stub). Each node builds or extends the series locally.

- Earliest date the algorithm supports: `2023-12-15`
- Format: `{"v":1,"algo":"UTXOracle-9.1","points":[{"d":"YYYY-MM-DD","usd":12345}]}`
- Points are never overwritten. The node only **appends days after the last stored date**.

Build or extend (needs local bitcoind RPC):

```bash
python3 -m vox_templi history          # one missing day
python3 -m vox_templi history --fill    # loop until yesterday is filled
```

Optional: copy `$VOX_STATE_DIR/history.json` points into this file and commit if you want a shared seed.
