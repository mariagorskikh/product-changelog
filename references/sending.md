# Sending: test first, then blast

The one hard rule: **never email an address that has opted out.** Build the audience fresh at every send and filter it against the opt-out list. The scripts enforce this; do not bypass them with ad-hoc sends.

Everything below assumes Resend, the default provider. The flow carries over to any provider with a send API and a contact list (Postmark, SendGrid, Amazon SES, Mailgun, Loops): swap the `Resend` class in `scripts/_common.py`.

## Setup once

These are one-time choices made on the first run. Verifying a domain you already own is free; buying a new domain or upgrading the provider plan costs money and needs the user's yes.

- Verify the sending domain with your provider (SPF, DKIM, and a DMARC record). Unverified domains land in spam.
- Create an API key with sending and audience access, export it as the env var named in `provider.api_key_env`.
- Choose an unsubscribe mode in config:
  - `broadcast` (recommended to start): the provider hosts the unsubscribe page and suppresses opt-outs within the audience. No code on your side.
  - `own_endpoint`: you host the page. Scripts mint a personal link per address: `token = base64url(HMAC-SHA256(secret, lowercase email))`. Your endpoint recomputes the token to verify, so links never expire and cannot be forged. Support both a GET (shows a confirm page) and a one-click POST (what mail clients call from the List-Unsubscribe header). Offer a resubscribe action on the same page.

## The audience file

`ISSUE_DIR/audience.jsonl`, one JSON object per line:

```json
{"email": "someone@customer.example", "name": "Sam Lee"}
```

Build it fresh from your user database every issue. A typical query:

```sql
select json_build_object('email', lower(email), 'name', name)
from users
where email_verified = true
  and lower(email) not in (select lower(email) from email_unsubscribes where category = 'changelog');
```

Opt-outs go in `ISSUE_DIR/unsubs.txt` (one address per line) even when the query already filters them; the scripts check both.

Optional ranking, useful when a plan caps how many contacts you can hold: put paying customers first, then order by most recent activity.

First-name cleaning (done by the scripts): take the first word of the display name, strip punctuation, reject it if it has `@` or digits, has no letters, or is shorter than 2 or longer than 20 characters. Capitalize an all-lowercase name. Otherwise fall back to `there`.

## Step by step

1. **Lint.** `python3 scripts/lint_email.py ISSUE_DIR --check-links` must pass.
2. **Test send dry run.** `python3 scripts/send_test.py ISSUE_DIR` shows subject, sender, recipients.
3. **Test send.** After the copy passed the self-review gate (or, in review mode, the user approved the draft): `python3 scripts/send_test.py ISSUE_DIR --send`. Only to `test_recipients`.
   Then `python3 scripts/send_test.py ISSUE_DIR --readback` pulls each delivered message from the provider API and checks the last event, subject, rendered greeting, unsubscribe line and leftover placeholders. In review mode the user also reads it in a real inbox on desktop and phone and replies with fixes or a go.
4. **Verify unsubscribe works** (own_endpoint mode): open the link from the test copy, confirm the opt-out is recorded, then resubscribe so the test address is clean.
5. **Build the audience** (fresh) and the opt-out list.
6. **Dry run the blast** and check the counts: unique addresses, queued, excluded, unsubscribed, invalid, and the quota line. In review mode, show them to the user.
7. **Blast.** In autonomous mode, pass the send flag yourself once the audience checklist in SKILL.md passes. In review mode, the user must say yes to this specific send in chat. In every mode, a send that would exceed `provider.monthly_quota` costs money: ask the user, and pass `--yes-over-quota` only after their yes.

### Path A: broadcasts (provider-hosted unsubscribe)

```bash
python3 scripts/broadcast_unsubs.py --out ./changelog-issues/unsubs.txt   # pull opt-outs first
cp ./changelog-issues/unsubs.txt ISSUE_DIR/unsubs.txt
python3 scripts/broadcast_sync.py ISSUE_DIR/audience.jsonl                # plan
python3 scripts/broadcast_sync.py ISSUE_DIR/audience.jsonl --apply        # upsert contacts
python3 scripts/broadcast_create.py ISSUE_DIR                             # dry run
python3 scripts/broadcast_create.py ISSUE_DIR --create                    # draft, sends nothing
python3 scripts/broadcast_create.py --send BROADCAST_ID --yes-send-broadcast
```

A rendered test through the real broadcast path: use a separate test audience that holds only the test recipients, create and send a broadcast to it, then create a NEW broadcast against the real audience.

Caveats:
- Contacts persist between issues. Anyone left in the audience gets the next broadcast. `broadcast_sync.py` warns about contacts that are in the audience but not in your input.
- Never re-post a contact that is unsubscribed in the provider; that resubscribes them. The sync script skips them.
- The provider does not add a footer to API broadcasts. Keep your own unsubscribe line as the last line.
- Some providers reject a whole broadcast if any contact uses a reserved example domain. The sync script drops those.

### Path B: one by one (own endpoint)

```bash
python3 scripts/blast.py ISSUE_DIR                                 # dry run with counts
python3 scripts/blast.py ISSUE_DIR --send --yes-send-to-everyone   # real send
```

Sequential, paced by `provider.send_interval_seconds`, resumable (a rerun skips every address already `ok` in `results.jsonl`). It stops itself and exits 2 when send errors reach `provider.max_failures` or the failure share goes above `provider.max_failure_rate` after 20 sends. Treat that as a hard stop: report the error, fix the cause, rerun to resume. Every message carries `List-Unsubscribe` and `List-Unsubscribe-Post: List-Unsubscribe=One-Click`, which gives Gmail and Yahoo their native unsubscribe button and is required for bulk senders.

## After the send

- **Verify delivery.** Path B: `python3 scripts/verify_delivery.py ISSUE_DIR --sample 40`, expect nearly all delivered. Path A: `GET /broadcasts/{id}` for its status, and the provider dashboard for delivered, opened, clicked, bounced.
- **Sync opt-outs back.** Path A: run `broadcast_unsubs.py` again after a day, and import the list into your own database if you keep one, so every other email you send honors it.
- **Watch replies.** Replies to a changelog are the best product feedback you will get. Route them to someone who answers.

## Subscriber math

Subscribers = total users minus opt-outs. When someone asks "how many get the changelog" or "how many unsubscribed", answer from the opt-out table (or `unsubs.txt`) and the user count, and report the unsubscribe rate for the latest issue (opt-outs since send divided by recipients). Around 0.5 percent per issue is normal for a product audience; a sudden jump means the content or the cadence is off.
