---
name: product-changelog
description: Write and send a recurring product changelog email to your users, then write and post the matching X thread, LinkedIn post and community (Discord or Slack) announcement, and optionally outline an animated changelog video. Use when the user says "changelog email", "write the changelog", "next changelog", "product update email", "what's new email", "send the changelog", "changelog blast", "release notes email", "changelog X thread", "post the changelog on LinkedIn", "changelog video", or asks how many people get the changelog or unsubscribed. Covers picking what goes in, voice and formatting rules, the screenshot pipeline, test sends with a read-back of the delivered copy, suppression-aware sending through Resend (broadcasts or one by one), social posts and the archive of past issues. Asks setup questions once, then runs the whole issue end to end on its own; only anything that costs money waits for the user's yes.
---

# Product changelog

A recurring email that tells users what changed in the product, written like a person, sent safely, then reused for social posts. The email is the source of truth for each issue; every other channel is cut down from it.

## How this skill runs

- **Ask once, up front.** On the first run (or when config is missing or a needed value is blank), ask the setup questions in one short batch, write `config.yaml`, then continue without further questions.
- **Then do everything.** In `autonomy.mode: autonomous` (the default) you pick the items, draft, lint, self-review, screenshot, test send, read the test back, build the audience, dry run, send to everyone, verify, pull opt-outs, write and post the social posts, and archive. No approval step. Each outward action passes a **self-review gate** first.
- **Money is the only approval.** Anything that costs money waits for the user's explicit yes in chat, in every mode: a send that would go over the provider plan's included quota (`provider.monthly_quota`), upgrading the provider plan, buying a domain, paid tools or licenses (for example a paid Remotion company license). Nothing else needs a yes.
- **Hard stops are not approvals.** They halt that one action. Finish whatever else is safe, then report. See [Hard stops](#hard-stops).
- **Report at the end.** One summary: the subject and full text that went out, counts (queued, sent, failed, excluded, unsubscribed), delivery sample, the test read-back result, every post with its link, anything skipped and why.
- **`review` mode** keeps the old per-action approval gates. See [Review mode](#review-mode).

Every script is a dry run by default. Real sends need explicit flags (`--send`, `--yes-send-to-everyone`, `--yes-send-broadcast`). In autonomous mode you pass them yourself, and only after the matching self-review gate passes. Never send ad hoc mail outside the scripts, because the scripts are what enforce opt-outs.

## Step 0: load the config

1. Look for `config.yaml` in the current project root, then in this skill's folder (or `$CHANGELOG_CONFIG`).
2. If there is none, copy `config.example.yaml` to `config.yaml` in the project root and ask, in one message:
   - product name, website, dashboard and docs URLs
   - sender name and title, from address, reply-to
   - test recipients (names and addresses)
   - provider: the Resend audience ID, the env var holding the API key, and the plan's included monthly emails if they know it (`provider.monthly_quota`, optional)
   - unsubscribe mode (`broadcast` or `own_endpoint`)
   - image hosting: where screenshots go and their public base URL
   - optional: cadence, brand link color, and how to post each social channel (`social.post_via`)
   Do not guess any of them. Write the answers into `config.yaml`, then carry on.
3. Any value still set to an UPPERCASE placeholder or a `yourproduct.example` address counts as missing.
4. Read `autonomy.mode` (default `autonomous`), `voice.notes` and `voice.banned_phrases`. Voice settings override the defaults in the references.
5. Secrets never go in config or in chat. API keys and the unsubscribe signing secret live in environment variables.

Later issues ask nothing. The one optional question is "Anything shipped outside git this time (pricing, partnerships, docs)?" If the user is not around, skip it and work from git and release notes.

## Step 1: pick what goes in

Read [references/voice-and-format.md](references/voice-and-format.md) first.

- Find the last issue in `paths.issues_dir` (folders named `NNN-YYYY-MM-DD-slug`). The newest one is the template for the next.
- Gather candidates since that date: `git log --since=<date> --no-merges --oneline`, merged pull requests, release notes, plus anything the user mentioned.
- Keep only user-visible changes. **3 to 5 items**, ranked by usefulness to the reader. **Lead with the most useful change**, the one most readers can use today.
- Check every claim against the live product and website. Never invent a feature, a number or a date. If a claim cannot be verified, drop the item.
- Write the list and order into the issue's `NOTES.md` and move on.

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

## Step 4: lint and self-review (gate 1: copy)

```bash
python3 scripts/lint_email.py ISSUE_DIR --check-links
```

Fix every failure, then work through this checklist. Fix and re-run until every box passes.

- [ ] `lint_email.py --check-links` exits 0.
- [ ] Read top to bottom as a busy customer: the most useful change is clear in 5 seconds.
- [ ] Every item is something a user can see or use today.
- [ ] Every claim, number and link matches the live product and site.
- [ ] Nothing reads like a press release; it sounds like the sender talking.
- [ ] Subject under 60 characters, benefit-led, no "Changelog #N".
- [ ] Every image has alt text and its hosted URL returns 200 (or will be deployed before Step 7).

## Step 5: test send and read-back (gate 2: delivered copy)

```bash
python3 scripts/send_test.py ISSUE_DIR --send      # only to test_recipients, [TEST] prefix
python3 scripts/send_test.py ISSUE_DIR --readback  # a minute later
```

Test copies go only to `test_recipients` and embed images inline if they are not deployed yet. `--readback` pulls each delivered message from the provider API and checks the last event, the subject, the rendered greeting and unsubscribe line, and that no placeholder survived. Also read the returned HTML yourself once. If anything is off, fix it, re-lint, re-test.

In `own_endpoint` mode, open the unsubscribe link from the test copy, confirm the opt-out is recorded, then resubscribe the test address.

## Step 6: build the audience

Full detail in [references/sending.md](references/sending.md).

- Build `ISSUE_DIR/audience.jsonl` fresh from the user's database (`{"email", "name"}` per line). Never reuse an old list.
- Build `ISSUE_DIR/unsubs.txt` from the opt-out table. In broadcast mode, first run `python3 scripts/broadcast_unsubs.py --out <issues_dir>/unsubs.txt` and copy it in.
- Founders, test and demo accounts are in config `exclude`; they get test copies instead.

## Step 7: send to everyone (gate 3: audience)

Pick the path from `unsubscribe.mode`. Run the dry run first and check the counts.

**Broadcast mode** (provider hosts unsubscribe):

```bash
python3 scripts/broadcast_sync.py ISSUE_DIR/audience.jsonl            # plan
python3 scripts/broadcast_sync.py ISSUE_DIR/audience.jsonl --apply    # upsert contacts
python3 scripts/broadcast_create.py ISSUE_DIR --create                # draft only
python3 scripts/broadcast_create.py --send BROADCAST_ID               # shows the recipient count, refuses
python3 scripts/broadcast_create.py --send BROADCAST_ID --yes-send-broadcast
```

**Own endpoint mode** (signed links to your own page):

```bash
python3 scripts/blast.py ISSUE_DIR                                    # dry run with counts
python3 scripts/blast.py ISSUE_DIR --send --yes-send-to-everyone
```

Audience checklist, all must pass before the send flag:

- [ ] Gates 1 and 2 passed on this exact copy (nothing changed since the read-back).
- [ ] The opt-out list was pulled or built in this run and is non-empty if the product has ever had an unsubscribe.
- [ ] Dry-run counts make sense: queued is close to users minus opt-outs minus excluded; no surprise jump against the last issue's `NOTES.md`.
- [ ] Broadcast mode: `broadcast_sync.py` reported no unexpected stale contacts.
- [ ] Every hosted image URL returns 200.
- [ ] Quota: if `provider.monthly_quota` is set, pass `--sent-this-month N` (sum the sent counts in this month's issue `NOTES.md` plus other mail on the same plan if known). If the script says the send would go over quota, **stop and ask the user**; pass `--yes-over-quota` only after their explicit yes.

The one-by-one blast is resumable: if it stops, re-run the same command and it skips addresses already sent.

## Step 8: verify and sync

- One by one: `python3 scripts/verify_delivery.py ISSUE_DIR --sample 40`. Broadcasts: `GET /broadcasts/{id}` through the provider API, or the dashboard.
- Pull opt-outs back after a day (`broadcast_unsubs.py`). If the user keeps opt-outs in their own database and you have write access, import them; otherwise say so in the report.

## Step 9: social posts

Write from the final email, following [references/social.md](references/social.md):

- **X thread**: hook tweet starting with `social.hook_prefix` that names every item, no link, strongest screenshot. Then one numbered tweet per item with its link and screenshot. Plus a one-line personal quote-post for a founder.
- **LinkedIn**: one post, hook first line, one short paragraph per item, plain text, image gallery.
- **Community** (Discord or Slack): opener line, one line per item with a bare link, the thread link once live.

4 to 5 items max, no policy notices, claims match the live site. Run the same banned-phrase and dash checks on `social.md` (`lint_email.py` reads it). Then, for each channel with a tool in `social.post_via`, post it yourself and record the post URL. For channels with no tool, hand the user the final text and images. The founder quote-post is from a personal account, so hand it over unless a tool for that account is configured.

## Step 10: video (optional, only on request)

If the user asks, follow [references/video.md](references/video.md): a 15 to 25 second motion reel from the issue screenshots, no title slide, big headline per item, screenshots dominate, outro with the product URL. Remotion needs a paid company license above a certain team size; that is a money question for the user.

## Step 11: archive and report

In the issue folder keep: `subject.txt`, `email.html`, `email.txt`, the screenshots, `social.md`, `test_results.jsonl`, and a `NOTES.md` with the item list, send date, path used, audience size, sent and failed counts, broadcast ID, post URLs, and unsubscribes after a day. If the product has a public web changelog page (`product.changelog_page`) and its source is in this repo, add the issue there too. When the user corrects the voice or format, add the lesson to `voice.notes` in config so the next issue starts from it. Then send the one summary described at the top.

## Hard stops

Stop that action, finish everything else that is safe, and report what stopped and why. Never work around a stop.

- Lint failures you cannot fix.
- A broken link or image you cannot fix (still not 200 after deploying or correcting it).
- The test read-back fails and you cannot find the cause.
- Opt-out filtering fails: the opt-out list cannot be pulled or built, the audience query errors, or a script refuses on `unsubs.txt`. Never send without it.
- Provider errors above the threshold mid-send (`blast.py` exits 2 at `provider.max_failures` or `provider.max_failure_rate`). Report the error; the blast is resumable once fixed.
- A send that would go over quota, a plan upgrade or any other spend: ask the user (money rule).
- Login, 2FA or re-auth prompts, CAPTCHAs, platform warnings or rate-limit notices on a posting tool, payment or billing forms.
- Anything that would break opt-out or anti-spam law (missing unsubscribe line, resubscribing someone who opted out).
- A claim you cannot verify. Drop it instead of guessing.

## Review mode

With `autonomy.mode: review`, the three gates also need the user's okay:

1. **Draft gate.** Show the subject, the email and the item list in chat. Nothing is sent until the user approves the copy.
2. **Test gate.** Send only to `test_recipients`. The user reads it in a real inbox and says go or gives fixes.
3. **Blast gate.** Show the dry-run counts (queued, excluded, unsubscribed). Send to everyone only when the user says yes to that specific send in chat. A yes to an earlier step is not a yes to this one.

Social posts are shown before posting, and the item list is proposed before writing. Never pass a send flag before the matching gate.

## Answering "how many subscribers?"

Subscribers = users minus opt-outs. Count opt-outs from the user's opt-out table or `unsubs.txt` (in broadcast mode, run `broadcast_unsubs.py` first). Give the latest issue's unsubscribe rate too.

## Files

- `config.example.yaml`: every company-specific value, plus `autonomy`, `provider.monthly_quota` and `social.post_via`.
- `templates/email.html`, `templates/email.txt`: the starting layout.
- `scripts/`: `lint_email.py`, `send_test.py` (with `--readback`), `blast.py`, `broadcast_sync.py`, `broadcast_create.py`, `broadcast_unsubs.py`, `verify_delivery.py`. Python 3.9+, stdlib plus PyYAML.
- `references/`: voice and format, screenshots, sending, social, video.
