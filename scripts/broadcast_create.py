#!/usr/bin/env python3
"""Create a changelog broadcast draft on Resend, then send it with an explicit flag.

    python3 scripts/broadcast_create.py ISSUE_DIR              # dry run: show payload summary
    python3 scripts/broadcast_create.py ISSUE_DIR --create     # create a DRAFT (sends nothing)
    python3 scripts/broadcast_create.py --send BROADCAST_ID    # shows the recipient count, refuses
    python3 scripts/broadcast_create.py --send BROADCAST_ID --yes-send-broadcast

Pass --yes-send-broadcast only after the copy is reviewed: by the self-review
gate in autonomous mode (the agent passes it itself), or by the user in review
mode. If provider.monthly_quota is set and the send would exceed it, the
script refuses unless --yes-over-quota is passed, which needs the user's yes
in chat in every mode because it costs money.

The draft is visible in the Resend dashboard, so you can eyeball it there.
Sending delivers to EVERY subscribed contact in the audience; the script
prints that count first.

ISSUE_DIR holds email.html, email.txt and subject.txt with {{NAME}} and
{{UNSUB_URL}}. They are converted to Resend merge tags in memory:
    {{NAME}}      -> {{{contact.first_name|<greeting_fallback>}}}
    {{UNSUB_URL}} -> {{{RESEND_UNSUBSCRIBE_URL}}}
Resend does not append a footer to API broadcasts, so keep your own small
unsubscribe line as the last line of the email.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    Resend, api_key, die, from_header, get, load_config, quota_check, read_issue,
    require,
)


def to_merge_tags(text: str, fallback: str) -> str:
    return (text.replace("{{NAME}}", "{{{contact.first_name|" + fallback + "}}}")
                .replace("{{UNSUB_URL}}", "{{{RESEND_UNSUBSCRIBE_URL}}}"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("issue_dir", nargs="?")
    ap.add_argument("--create", action="store_true", help="create the draft broadcast")
    ap.add_argument("--send", metavar="BROADCAST_ID")
    ap.add_argument("--yes-send-broadcast", action="store_true",
                    help="confirms the whole audience; passed after the self-review gate (or the user's okay in review mode)")
    ap.add_argument("--sent-this-month", type=int, default=0,
                    help="emails already sent this month on the plan, for the quota check")
    ap.add_argument("--yes-over-quota", action="store_true",
                    help="only after the user's explicit yes in chat: going over the quota costs money")
    ap.add_argument("--config")
    args = ap.parse_args()

    cfg = load_config(args.config)
    audience_id = require(cfg, "provider.audience_id")

    if args.send:
        client = Resend(api_key(cfg))
        contacts = client.list_contacts(audience_id)
        live = sum(1 for c in contacts if not c.get("unsubscribed"))
        print(f"broadcast {args.send} would go to {live} subscribed contacts "
              f"({len(contacts) - live} unsubscribed are skipped by Resend)")
        quota_check(cfg, live, args.sent_this_month, args.yes_over_quota)
        if not args.yes_send_broadcast:
            print("\nREFUSING: pass --yes-send-broadcast to deliver to the whole audience, "
                  "once the copy passed review (self-review gate in autonomous mode, the user's "
                  "okay in review mode).")
            return
        status, body = client.request("POST", f"/broadcasts/{args.send}/send", {})
        print(status, str(body)[:300])
        if status not in (200, 201):
            sys.exit(1)
        return

    if not args.issue_dir:
        die("pass ISSUE_DIR, or --send BROADCAST_ID")
    workdir = Path(args.issue_dir)
    html_t, text_t, subject = read_issue(workdir)
    if "{{UNSUB_URL}}" not in html_t:
        die("email.html must contain {{UNSUB_URL}} as its last line")
    fallback = get(cfg, "email.greeting_fallback", "there")
    payload = {
        get(cfg, "provider.broadcast_target_field", "segment_id"): audience_id,
        "from": from_header(cfg),
        "reply_to": get(cfg, "sender.reply_to") or require(cfg, "sender.from_email"),
        "subject": subject,
        "name": f"changelog-{workdir.name}",  # label in the dashboard; unique per issue
        "html": to_merge_tags(html_t, fallback),
        "text": to_merge_tags(text_t, fallback),
    }
    print(f"name:    {payload['name']}")
    print(f"subject: {subject}")
    print(f"from:    {payload['from']}")
    print(f"html:    {len(payload['html'])} chars, text: {len(payload['text'])} chars")
    if not args.create:
        print("\nDRY RUN: nothing created. Re-run with --create to make a draft broadcast.")
        return
    status, body = Resend(api_key(cfg)).request("POST", "/broadcasts", payload)
    print(status, str(body)[:300])
    if status in (200, 201) and isinstance(body, dict):
        print(f"\nDraft created. To send once the copy passed review:\n"
              f"  python3 scripts/broadcast_create.py --send {body.get('id')} --yes-send-broadcast")


if __name__ == "__main__":
    main()
