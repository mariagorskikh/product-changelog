#!/usr/bin/env python3
"""Send a changelog issue to the test recipients only.

Dry run by default: prints what would be sent and sends nothing.

    python3 scripts/send_test.py ISSUE_DIR                 # dry run
    python3 scripts/send_test.py ISSUE_DIR --send          # really send the test
    python3 scripts/send_test.py ISSUE_DIR --to me@x.example --send

ISSUE_DIR holds email.html, email.txt and subject.txt, using the {{NAME}}
and {{UNSUB_URL}} placeholders. Recipients default to test_recipients in
config.yaml.

Screenshots referenced under paths.image_base_url that exist as local files
in ISSUE_DIR are embedded inline (cid:), so a test renders correctly before
the images are deployed. The real blast never does this: hosted images must
return 200 first.
"""

from __future__ import annotations

import argparse
import base64
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    PLACEHOLDERS, Resend, api_key, die, first_name, from_header, get,
    load_config, personalize, read_issue, require, unsubscribe_url,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("issue_dir")
    ap.add_argument("--to", action="append", help="override recipient email (repeatable)")
    ap.add_argument("--send", action="store_true", help="actually send (default is a dry run)")
    ap.add_argument("--config")
    args = ap.parse_args()

    cfg = load_config(args.config)
    workdir = Path(args.issue_dir)
    html_t, text_t, subject = read_issue(workdir)
    sender = from_header(cfg)
    reply_to = get(cfg, "sender.reply_to") or require(cfg, "sender.from_email")

    if args.to:
        recipients = [(first_name(a.split("@")[0]) or get(cfg, "email.greeting_fallback", "there"), a) for a in args.to]
    else:
        recipients = [(r.get("name", ""), r.get("email", "")) for r in get(cfg, "test_recipients", []) or []]
    recipients = [(n, e) for n, e in recipients if e]
    if not recipients:
        die("no test recipients: set test_recipients in config.yaml or pass --to")
    for _, e in recipients:
        if any(p in e for p in PLACEHOLDERS):
            die(f"test recipient {e!r} is still a placeholder")

    attachments = []
    base = get(cfg, "paths.image_base_url", "")
    if base:
        for img in sorted(set(re.findall(r'src="' + re.escape(base) + r'([^"]+)"', html_t))):
            local = workdir / img
            if local.exists():
                html_t = html_t.replace(base + img, f"cid:{img}")
                attachments.append({
                    "filename": img,
                    "content": base64.b64encode(local.read_bytes()).decode(),
                    "content_id": img,
                })

    mode = get(cfg, "unsubscribe.mode", "broadcast")
    print(f"subject:    {subject}")
    print(f"from:       {sender}")
    print(f"recipients: {', '.join(e for _, e in recipients)}")
    print(f"inline images: {len(attachments)}")
    if not args.send:
        print("\nDRY RUN: nothing sent. Re-run with --send to deliver the test copies.")
        return

    client = Resend(api_key(cfg))
    for name, addr in recipients:
        greet = first_name(name) or get(cfg, "email.greeting_fallback", "there")
        unsub = unsubscribe_url(cfg, addr) if mode == "own_endpoint" else "#unsubscribe-preview"
        payload = {
            "from": sender,
            "to": [addr],
            "reply_to": reply_to,
            "subject": f"[TEST] {subject}",
            "html": personalize(html_t, greet, unsub),
            "text": personalize(text_t, greet, unsub),
        }
        if attachments:
            payload["attachments"] = attachments
        if mode == "own_endpoint":
            payload["headers"] = {
                "List-Unsubscribe": f"<{unsub}>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            }
        status, body = client.request("POST", "/emails", payload)
        print(addr, status, str(body)[:200])


if __name__ == "__main__":
    main()
