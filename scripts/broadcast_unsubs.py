#!/usr/bin/env python3
"""Pull unsubscribed contacts from the Resend audience into a local list.

Read-only on Resend. Merges every address marked unsubscribed into a
plain text file (one address per line, deduped, sorted), so the next
audience build and every other email you send can honor it.

    python3 scripts/broadcast_unsubs.py --out ./changelog-issues/unsubs.txt

Run it after every broadcast and before building any future audience.
If you keep opt-outs in your own database, import this file there too:
your database should stay the source of truth for every sender.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Resend, api_key, load_config, read_email_set, require  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="unsubs.txt to create or merge into")
    ap.add_argument("--config")
    args = ap.parse_args()

    cfg = load_config(args.config)
    contacts = Resend(api_key(cfg)).list_contacts(require(cfg, "provider.audience_id"))
    remote = {(c.get("email") or "").lower() for c in contacts if c.get("unsubscribed")}
    out = Path(args.out)
    local = read_email_set(out)
    new = remote - local
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(f"{e}\n" for e in sorted(local | remote) if e))
    print(f"{len(remote)} unsubscribed on Resend, {len(new)} new; {out} now lists {len(local | remote)}")
    for e in sorted(new):
        print(f"  new: {e}")


if __name__ == "__main__":
    main()
