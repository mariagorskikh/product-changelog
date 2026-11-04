---
name: product-changelog
description: Write and send a recurring product changelog email to your users, then draft the matching X thread, LinkedIn post and community (Discord or Slack) announcement, and optionally outline an animated changelog video. Use when the user says "changelog email", "write the changelog", "next changelog", "product update email", "what's new email", "send the changelog", "changelog blast", "release notes email", "changelog X thread", "post the changelog on LinkedIn", "changelog video", or asks how many people get the changelog or unsubscribed. Covers picking what goes in, voice and formatting rules, the screenshot pipeline, test sends, suppression-aware sending through Resend (broadcasts or one by one), social templates and the archive of past issues. Drafts first, test send second, the real send only on an explicit go.
---

# Product changelog

A recurring email that tells users what changed in the product, written like a person, sent safely, then reused for social posts. The email is the source of truth for each issue; every other channel is cut down from it.

## Three approval gates (never skip)

1. **Draft gate.** Show the subject, the email and the item list in chat. Nothing is sent until the user approves the copy.
2. **Test gate.** Send only to `test_recipients`. The user reads it in a real inbox and says go or gives fixes.
3. **Blast gate.** Show the dry-run counts (queued, excluded, unsubscribed). Send to everyone only when the user says yes to that specific send in chat. A yes to an earlier step is not a yes to this one.

Every script is a dry run by default. Real sends need explicit flags (`--send`, `--yes-send-to-everyone`, `--yes-send-broadcast`). Never pass them before the matching gate. Never send ad hoc mail outside the scripts, because the scripts are what enforce opt-outs.

## Step 0: load the config

1. Look for `config.yaml` in the current project root, then in this skill's folder (or `$CHANGELOG_CONFIG`).
2. If there is none, copy `config.example.yaml` to `config.yaml` in the project root and ask the user for the missing values in one short message: product name and URL, sender name and title, from address and reply-to, test recipients, brand link color, cadence, unsubscribe mode, image hosting location, and (for sending) the Resend audience ID and the name of the env var holding the API key. Do not guess any of them.
3. Any value still set to an UPPERCASE placeholder or a `yourproduct.example` address counts as missing.
4. Read `voice.notes` and `voice.banned_phrases`. They override the defaults in the references.
5. Secrets never go in config or in chat. API keys and the unsubscribe signing secret live in environment variables.

## Step 1: pick what goes in

Read [references/voice-and-format.md](references/voice-and-format.md) first.

- Find the last issue in `paths.issues_dir` (folders named `NNN-YYYY-MM-DD-slug`). The newest one is the template for the next.
- Gather candidates since that date: `git log --since=<date> --no-merges --oneline`, merged pull requests, release notes. Ask the user what shipped outside git.
- Keep only user-visible changes. **3 to 5 items**, ranked by usefulness to the reader. **Lead with the most useful change**, the one most readers can use today.
- Check every claim against the live product and website.
- Propose the list with one line per item and the order. Get a quick yes before writing.

## Step 2: draft the email

Create `paths.issues_dir/NNN-YYYY-MM-DD-slug/` and write:

- `subject.txt`: benefit-led and product-first ("You can now export reports to Sheets"). Never "Changelog #N".
- `email.html`: from [templates/email.html](templates/email.html) (or the last issue), filling every `[[...]]` marker from config and content.
- `email.txt`: the same words as plain text with bare URLs.

Keep `{{NAME}}` and `{{UNSUB_URL}}` as literal placeholders; the send scripts fill them per recipient.

Core rules (detail in the reference):

- `Hi {{NAME}},`, then the one-line opener from config, then straight into the lead item.
- Each item: what changed, then why it matters, in flowing sentences. No labeled bullets.
- Short sentences, plain words, "you can now" over "we built".
- At most one bold accent per paragraph.
- One screenshot per item at most; the hero item always gets one, and it links to the feature.
- Styled-minimal HTML: 600px wrapper, system font, inline styles, no buttons or banners.
- No "excited to announce" and the rest of the banned list. No em or en dashes if `voice.no_dashes` is on.
- Optional casual P.S. ("BTW, ...").
- Sign-off from config. The unsubscribe line is the last line, small and muted.

## Step 3: screenshots

Follow [references/screenshots.md](references/screenshots.md): stage real state on a demo account (no customer data), capture at 2x with Playwright, clip to the panel, name files `<issue>-<slug>.png`, host them at `paths.image_base_url`, and confirm each URL returns 200 before any blast.

## Step 4: lint and self-review

```bash
python3 scripts/lint_email.py ISSUE_DIR --check-links
```

Fix every failure. Then read the email once as a busy customer would and fix what reads like a press release. Show the user the subject, the rendered text and the item order. **Draft gate.**

## Step 5: test send

```bash
python3 scripts/send_test.py ISSUE_DIR           # dry run
python3 scripts/send_test.py ISSUE_DIR --send    # after the draft gate
```

Test copies go only to `test_recipients`, with a `[TEST]` subject prefix, and embed images inline if they are not deployed yet. Ask the user to check desktop and phone, images, links and the greeting. Apply fixes, re-lint, re-test if anything changed. **Test gate.**

In `own_endpoint` mode, also confirm the unsubscribe link from the test copy records the opt-out, then resubscribe the test address.

## Step 6: build the audience

Full detail in [references/sending.md](references/sending.md).

- Build `ISSUE_DIR/audience.jsonl` fresh from the user's database (`{"email", "name"}` per line). Never reuse an old list.
- Build `ISSUE_DIR/unsubs.txt` from the opt-out table. In broadcast mode, first run `python3 scripts/broadcast_unsubs.py --out <issues_dir>/unsubs.txt` and copy it in.
- Founders, test and demo accounts are in config `exclude`; they get test copies instead.

## Step 7: send to everyone

Pick the path from `unsubscribe.mode`.

**Broadcast mode** (provider hosts unsubscribe):

```bash
python3 scripts/broadcast_sync.py ISSUE_DIR/audience.jsonl            # plan
python3 scripts/broadcast_sync.py ISSUE_DIR/audience.jsonl --apply    # upsert contacts
python3 scripts/broadcast_create.py ISSUE_DIR --create                # draft only
python3 scripts/broadcast_create.py --send BROADCAST_ID               # shows the recipient count, refuses
```

**Own endpoint mode** (signed links to your own page):

```bash
python3 scripts/blast.py ISSUE_DIR                                    # dry run with counts
```

Report the counts to the user. **Blast gate.** Only on an explicit yes, re-run with `--yes-send-broadcast` or `--send --yes-send-to-everyone`. The one-by-one blast is resumable: if it stops, re-run the same command and it skips addresses already sent.

## Step 8: verify and sync

- One by one: `python3 scripts/verify_delivery.py ISSUE_DIR --sample 40`. Broadcasts: read the provider dashboard.
- Pull opt-outs back after a day (`broadcast_unsubs.py`) and tell the user to import them into their own database if they keep one.
- Report: recipients, failures, delivery sample, unsubscribes so far.

## Step 9: social posts

Draft from the final email, following [references/social.md](references/social.md):

- **X thread**: hook tweet starting with `social.hook_prefix` that names every item, no link, strongest screenshot. Then one numbered tweet per item with its link and screenshot. Plus a one-line personal quote-post for a founder.
- **LinkedIn**: one post, hook first line, one short paragraph per item, plain text, image gallery.
- **Community** (Discord or Slack): opener line, one line per item with a bare link, the thread link once live.

4 to 5 items max, no policy notices, claims match the live site. The user posts; you hand over text and images.

## Step 10: video (optional, only on request)

After the send, if the user asks, follow [references/video.md](references/video.md): a 15 to 25 second motion reel from the issue screenshots, no title slide, big headline per item, screenshots dominate, outro with the product URL. Hand the user the local mp4. Never post it.

## Step 11: archive

In the issue folder keep: `subject.txt`, `email.html`, `email.txt`, the screenshots, `social.md`, and a `NOTES.md` with send date, path used, audience size, sent and failed counts, broadcast ID, and unsubscribes after a day. If the product has a public web changelog page (`product.changelog_page`), add the issue there too. When the user corrects the voice or format, add the lesson to `voice.notes` in config so the next issue starts from it.

## Answering "how many subscribers?"

Subscribers = users minus opt-outs. Count opt-outs from the user's opt-out table or `unsubs.txt` (in broadcast mode, run `broadcast_unsubs.py` first). Give the latest issue's unsubscribe rate too.

## Files

- `config.example.yaml`: every company-specific value.
- `templates/email.html`, `templates/email.txt`: the starting layout.
- `scripts/`: `lint_email.py`, `send_test.py`, `blast.py`, `broadcast_sync.py`, `broadcast_create.py`, `broadcast_unsubs.py`, `verify_delivery.py`. Python 3.9+, stdlib plus PyYAML.
- `references/`: voice and format, screenshots, sending, social, video.
