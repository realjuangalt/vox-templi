"""python -m vox_templi serve|oracle"""
from __future__ import annotations

import json
import sys

from .config import Config


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0] if argv else "serve"
    cfg = Config.load()
    from . import log

    log.configure(cfg.log_path, cfg.log_max_bytes, cfg.log_forever)
    if cmd in ("serve", "httpd"):
        from .httpd import serve

        serve(cfg)
        return 0
    if cmd == "oracle":
        from .oracle import run

        print(json.dumps(run(cfg)))
        return 0
    if cmd == "history":
        from .history import step

        print(json.dumps(step(cfg)))
        return 0
    if cmd == "status":
        from .collect import snapshot

        print(json.dumps(snapshot(cfg), indent=2))
        return 0
    print("usage: python -m vox_templi [serve|oracle|history|status]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
