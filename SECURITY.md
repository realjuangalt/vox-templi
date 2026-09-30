# Security policy

This file is the project’s vulnerability-reporting policy. GitHub shows it on the Security tab. It is not an audit, not a pentest, and not a claim that the software is safe. It tells you how to report a problem in private, and what an operator should already know before turning the kiosk on.

## Reporting

If you find a way to leak the Bitcoin RPC cookie, expose node data unintentionally, or run code on a machine that installed this repo, report it privately:

1. Open a [private security advisory](https://github.com/realjuangalt/vox-templi/security/advisories/new) on this repository.
2. Do not open a public GitHub issue for an unfixed vulnerability, and do not paste cookie contents, RPC credentials, or log excerpts that contain them.

If private advisories are unavailable, contact the maintainer through GitHub (`realjuangalt`) and wait for a private channel. Give the version (git commit), what you expected, and what happened. Please allow time to respond before any public write-up.

## What operators should know

The HTTP server has no authentication. `/api/status` includes chain height, tip hash, peer count, peer user-agent, mempool size, fee estimates, and the cached UTXOracle price. `/api/log` returns recent local log lines. Keep `VOX_BIND=127.0.0.1`. Putting that port on a LAN or the public internet publishes your node’s status to anyone who can open the URL.

The RPC cookie (`VOX_BITCOIN_COOKIE`) is a secret. It is read to call bitcoind. The app is written not to log the cookie value. A filled `/etc/vox-templi/env`, `*.cookie`, and `*.log` are gitignored. Do not commit them. `chmod 600` the env file. The service user must be able to read the cookie, and other users should not.

The HDMI kiosk runs Chromium as the configured kiosk user on tty1. Treat that session like a local display, not a multi-user service.

UTXOracle is third-party code under `vendor/`. Its terms are in `vendor/UTXORACLE_LICENSE.md`. This policy does not cover Bitcoin Core itself.

## Scope

In scope: `vox_templi/`, `www/`, `wrappers/`, `scripts/install.sh`, `scripts/deploy.sh`, and the systemd units, as published on the default branch.

Out of scope: someone binding the port publicly on purpose, a compromised host, or a stolen cookie file.
