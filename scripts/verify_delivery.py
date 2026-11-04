#!/usr/bin/env python3
"""Spot-check delivery of a one-by-one blast. Read-only.

Samples ids from ISSUE_DIR/results.jsonl, asks Resend for each message's
last event, and prints a tally. Expect almost all "delivered".

    python3 scripts/verify_delivery.py ISSUE_DIR [--sample 40]

For broadcasts, read delivered, opened, clicked and bounced in the Resend
dashboard under Broadcasts instead.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Resend, api_key, die, load_config  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("issue_dir")
    ap.add_argument("--sample", type=int, default=40)
    ap.add_argument("--config")
    args = ap.parse_args()

    cfg = load_config(args.config)
    path = Path(args.issue_dir) / "results.jsonl"
    if not path.exists():
        die(f"{path} not found")
    recs = [json.loads(l) for l in path.open() if l.strip()]
    ok = [r for r in recs if r.get("ok") and r.get("info")]
    failed = [r for r in recs if not r.get("ok")]
    print(f"results: {len(ok)} accepted, {len(failed)} failed at send time")
    client = Resend(api_key(cfg))
    tally: Counter[str] = Counter()
    for r in random.sample(ok, min(args.sample, len(ok))):
        status, body = client.request("GET", f"/emails/{r['info']}")
        event = body.get("last_event", "unknown") if isinstance(body, dict) else f"http {status}"
        tally[event] += 1
        if event not in ("delivered", "opened", "clicked"):
            print(f"  {r['email']}: {event}")
    print("sample:", dict(tally))


if __name__ == "__main__":
    main()
