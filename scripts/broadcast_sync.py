#!/usr/bin/env python3
"""Sync recipients into the Resend audience used for changelog broadcasts.

Dry run by default: prints the plan and writes nothing.

    python3 scripts/broadcast_sync.py ISSUE_DIR/audience.jsonl            # plan only
    python3 scripts/broadcast_sync.py ISSUE_DIR/audience.jsonl --apply    # upsert contacts

Input rows: {"email": ..., "name": ...} or {"email": ..., "first_name": ...}.
Rows in config `exclude` or in an unsubs.txt next to the input are skipped.

Safety: a contact already marked unsubscribed in Resend is NEVER touched.
Re-posting it would set unsubscribed=false and silently resubscribe someone
who opted out. Those are reported as skip-unsub.

Contacts persist between issues: anyone left in the audience receives the
next broadcast, so re-sync every issue to pick up new signups.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    EMAIL_RE, Resend, api_key, first_name, get, load_config, read_email_set,
    read_jsonl, require,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("audience_jsonl")
    ap.add_argument("--apply", action="store_true", help="write contacts (default is a dry run)")
    ap.add_argument("--config")
    args = ap.parse_args()

    cfg = load_config(args.config)
    audience_id = require(cfg, "provider.audience_id")
    path = Path(args.audience_jsonl)
    exclude = {e.lower() for e in (get(cfg, "exclude", []) or [])}
    unsubs = read_email_set(path.parent / "unsubs.txt")

    rows: dict[str, str] = {}
    dropped = 0
    for row in read_jsonl(path):
        e = (row.get("email") or "").strip().lower()
        # Resend rejects a whole broadcast if the audience holds a reserved
        # example domain, so keep synthetic test rows out.
        if (not e or not EMAIL_RE.match(e) or e in exclude or e in unsubs
                or e.endswith(("example.com", "example.org", "example.net"))):
            dropped += 1
            continue
        fn = row.get("first_name")
        rows[e] = first_name(fn if fn is not None else row.get("name"))

    client = Resend(api_key(cfg))
    existing = {(c.get("email") or "").lower(): c for c in client.list_contacts(audience_id)}
    print(f"audience holds {len(existing)} contacts; input has {len(rows)} usable rows ({dropped} dropped)")

    todo, skip_unsub, unchanged = [], 0, 0
    for e, fn in rows.items():
        cur = existing.get(e)
        if cur is None:
            todo.append((e, fn))
        elif cur.get("unsubscribed"):
            skip_unsub += 1
        elif fn != (cur.get("first_name") or ""):
            todo.append((e, fn))
        else:
            unchanged += 1
    stale = [e for e, c in existing.items() if e not in rows and not c.get("unsubscribed")]

    print(f"plan: {len(todo)} to upsert, {unchanged} current, {skip_unsub} skipped (unsubscribed in Resend)")
    if stale:
        print(f"note: {len(stale)} subscribed contacts are in the audience but not in this input; "
              "they WILL receive the broadcast. Remove them in the dashboard if that is wrong.")
    if not args.apply:
        print("\nDRY RUN: nothing written. Re-run with --apply to upsert.")
        return

    counts = {"ok": 0, "failed": 0}
    for i, (e, fn) in enumerate(todo, 1):
        payload = {"email": e, "unsubscribed": False}
        if fn:
            payload["first_name"] = fn
        status, body = client.request("POST", f"/audiences/{audience_id}/contacts", payload)
        if status in (200, 201, 409):
            counts["ok"] += 1
        else:
            counts["failed"] += 1
            print(f"FAIL {e}: {status} {str(body)[:150]}", flush=True)
        if i % 100 == 0:
            print(f"{i}/{len(todo)} {counts}", flush=True)
        time.sleep(0.12)  # about 8 requests a second, under the default limit
    print(f"DONE {counts}")


if __name__ == "__main__":
    main()
