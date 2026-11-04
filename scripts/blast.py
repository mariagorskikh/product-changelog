#!/usr/bin/env python3
"""Send a changelog issue one message per recipient, honoring unsubscribes.

Use this path when you host your own unsubscribe endpoint
(unsubscribe.mode: own_endpoint). For provider-hosted unsubscribe, use the
broadcast scripts instead.

Dry run by default. Sending needs BOTH flags:

    python3 scripts/blast.py ISSUE_DIR                                   # dry run
    python3 scripts/blast.py ISSUE_DIR --send --yes-send-to-everyone     # real send

Pass the send flags only after the copy is reviewed: by the self-review gate
in autonomous mode (the agent passes them itself), or by the user in review
mode. If provider.monthly_quota is set and this send would exceed it, the
script refuses unless --yes-over-quota is passed, which needs the user's yes
in chat in every mode because it costs money.

ISSUE_DIR must contain:
    email.html, email.txt, subject.txt   the approved copy
    audience.jsonl                       {"email": ..., "name": ...} per line, built fresh
    unsubs.txt                           (optional) one opted-out address per line

Filters: config `exclude`, unsubs.txt, invalid addresses, case-insensitive
duplicates. Every message carries List-Unsubscribe and one-click headers.
Resumable: results go to ISSUE_DIR/results.jsonl and a rerun skips every
address already marked ok.

Stops itself mid-send when provider errors pile up (provider.max_failures in
total, or a failure share above provider.max_failure_rate after 20 sends),
and exits 2. That is a hard stop: report it, fix the cause, then rerun the
same command to resume.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    EMAIL_RE, Resend, api_key, die, first_name, from_header, get, load_config,
    personalize, quota_check, read_email_set, read_issue, read_jsonl, require,
    unsubscribe_url,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("issue_dir")
    ap.add_argument("--send", action="store_true", help="really send (with --yes-send-to-everyone)")
    ap.add_argument("--yes-send-to-everyone", action="store_true",
                    help="confirms the whole audience; passed after the self-review gate (or the user's okay in review mode)")
    ap.add_argument("--sent-this-month", type=int, default=0,
                    help="emails already sent this month on the plan, for the quota check")
    ap.add_argument("--yes-over-quota", action="store_true",
                    help="only after the user's explicit yes in chat: going over the quota costs money")
    ap.add_argument("--config")
    args = ap.parse_args()

    cfg = load_config(args.config)
    if get(cfg, "unsubscribe.mode") != "own_endpoint":
        die("blast.py needs unsubscribe.mode: own_endpoint (signed links to your own page). "
            "With provider-hosted unsubscribe, use broadcast_sync.py + broadcast_create.py.")
    workdir = Path(args.issue_dir)
    html_t, text_t, subject = read_issue(workdir)
    if "{{UNSUB_URL}}" not in html_t or "{{UNSUB_URL}}" not in text_t:
        die("both email.html and email.txt must contain {{UNSUB_URL}}")
    sender = from_header(cfg)
    reply_to = get(cfg, "sender.reply_to") or require(cfg, "sender.from_email")
    fallback = get(cfg, "email.greeting_fallback", "there")

    audience_path = workdir / "audience.jsonl"
    if not audience_path.exists():
        die(f"{audience_path} is missing; build the audience fresh before every send")
    exclude = {e.lower() for e in (get(cfg, "exclude", []) or [])}
    unsubs = read_email_set(workdir / "unsubs.txt")

    results_path = workdir / "results.jsonl"
    already: set[str] = set()
    if results_path.exists():
        for line in results_path.open():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("ok"):
                already.add(rec["email"])

    seen: set[str] = set()
    queue: list[tuple[str, str]] = []
    skipped = {"excluded": 0, "unsubscribed": 0, "invalid": 0, "already_sent": 0}
    for row in read_jsonl(audience_path):
        e = (row.get("email") or "").strip().lower()
        if not e or e in seen:
            continue
        seen.add(e)
        if e in exclude:
            skipped["excluded"] += 1
        elif e in unsubs:
            skipped["unsubscribed"] += 1
        elif not EMAIL_RE.match(e):
            skipped["invalid"] += 1
        elif e in already:
            skipped["already_sent"] += 1
        else:
            queue.append((e, first_name(row.get("name")) or fallback))

    interval = float(get(cfg, "provider.send_interval_seconds", 0.6))
    print(f"subject:   {subject}")
    print(f"from:      {sender}")
    print(f"unique addresses: {len(seen)}  queued: {len(queue)}  skipped: {skipped}")
    print(f"estimated time: {len(queue) * (interval + 0.3) / 60:.1f} min")
    for e, n in queue[:5]:
        print(f"  sample: {e} -> Hi {n},")

    quota_check(cfg, len(queue), args.sent_this_month, args.yes_over_quota)

    if not (args.send and args.yes_send_to_everyone):
        print("\nDRY RUN: nothing sent. Once the copy passed review (self-review gate in autonomous "
              "mode, the user's okay in review mode) and the test copy read back clean, "
              "re-run with --send --yes-send-to-everyone.")
        return

    max_failures = int(get(cfg, "provider.max_failures", 10))
    max_rate = float(get(cfg, "provider.max_failure_rate", 0.05))

    client = Resend(api_key(cfg))
    sent = failed = 0
    start = time.time()
    with results_path.open("a") as out:
        for i, (email, name) in enumerate(queue):
            unsub = unsubscribe_url(cfg, email)
            payload = {
                "from": sender,
                "to": [email],
                "reply_to": reply_to,
                "subject": subject,
                "html": personalize(html_t, name, unsub),
                "text": personalize(text_t, name, unsub),
                "headers": {
                    "List-Unsubscribe": f"<{unsub}>",
                    "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
                },
            }
            status, body = client.request("POST", "/emails", payload)
            ok = status == 200 and isinstance(body, dict)
            info = body.get("id", "") if ok else f"{status}: {str(body)[:200]}"
            out.write(json.dumps({"email": email, "name": name, "ok": ok, "info": info}) + "\n")
            out.flush()
            if ok:
                sent += 1
            else:
                failed += 1
                print(f"FAIL {email}: {info}", flush=True)
                done = sent + failed
                if failed >= max_failures or (done >= 20 and failed / done > max_rate):
                    print(f"STOPPED: {failed} failures in {done} sends (limits: {max_failures} total, "
                          f"{max_rate:.0%} rate). Nothing more was sent. Fix the cause, then rerun "
                          "the same command to resume; addresses already sent are skipped.", flush=True)
                    sys.exit(2)
            if (i + 1) % 50 == 0:
                rate = (i + 1) / (time.time() - start)
                eta = (len(queue) - i - 1) / rate / 60
                print(f"{i + 1}/{len(queue)} sent={sent} failed={failed} eta={eta:.1f}m", flush=True)
            time.sleep(interval)

    print(f"DONE sent={sent} failed={failed} of {len(queue)}")


if __name__ == "__main__":
    main()
