# product-changelog

A [Claude Code](https://claude.com/claude-code) skill that writes and sends your recurring product changelog email, then turns it into an X thread, a LinkedIn post and a Discord or Slack announcement. Optionally it outlines an animated changelog video from the same screenshots.

It is opinionated about the craft: what goes in, how it reads, and how to send it without ever emailing someone who opted out.

## What it does

- **Picks the content.** Reads your git log and release notes since the last issue, keeps only user-visible changes, and proposes 3 to 5 items ranked by how useful they are to your users.
- **Writes like a person.** Benefit-led subject, one-line opener, flowing sentences instead of labeled bullets, one bold accent per paragraph, no "excited to announce". Your voice notes in config override the defaults.
- **Screenshots.** A Playwright recipe for crisp 2x captures of the exact panel, hosted before you send.
- **Sends safely.** Lint, test send to yourself, dry run with counts, then the real send only on your explicit go. Opt-outs are filtered every time, and an unsubscribed contact is never resubscribed by accident.
- **Social posts.** X thread (hook tweet with no link, one numbered tweet per item), LinkedIn post, short community announcement.
- **Video (optional).** Style guide and a minimal Remotion outline for a 20 second motion recap.
- **Archive.** One folder per issue, so the newest issue is always the template for the next.

## Requirements

- Claude Code
- Python 3.9 or newer, plus PyYAML (`pip install pyyaml`). Everything else is the standard library.
- A [Resend](https://resend.com) account with a verified sending domain, for sending. Other providers work by swapping the small `Resend` class in `scripts/_common.py`.
- Optional: Node and [Playwright](https://playwright.dev) for screenshots, [Remotion](https://www.remotion.dev) for the video (check its license for your company size).

## Install

```bash
git clone https://github.com/mariagorskikh/product-changelog ~/.claude/skills/product-changelog
pip install pyyaml
```

## Configure

```bash
cp ~/.claude/skills/product-changelog/config.example.yaml ./config.yaml
export RESEND_API_KEY=...            # never put keys in config.yaml
export UNSUBSCRIBE_SECRET=...        # only for unsubscribe.mode: own_endpoint
```

Fill in `config.yaml`: product name and URLs, sender name and address, test recipients, brand colors, voice notes, banned phrases, the Resend audience ID, and where screenshots are hosted. If you skip this, Claude asks for the missing values on first run. `config.yaml` is gitignored.

Two unsubscribe modes:

- `broadcast`: Resend hosts the unsubscribe page and handles suppression. Easiest.
- `own_endpoint`: you host the page; the scripts mint a signed, personal link per address and add one-click `List-Unsubscribe` headers.

## Example prompts

- "Write the next changelog email."
- "What shipped since the last changelog? Propose the items."
- "Send me a test of the changelog."
- "Looks good, send the changelog to everyone."
- "Draft the X thread and LinkedIn post for this changelog."
- "Make a changelog video from these screenshots."
- "How many people get the changelog, and how many unsubscribed last issue?"

## How it works

1. Claude reads your config and the last issue in your issues folder.
2. It proposes the items, you confirm, it drafts `subject.txt`, `email.html` and `email.txt`.
3. `lint_email.py` checks for banned phrases, dashes, leftover placeholders, missing alt text, a missing unsubscribe line and broken links.
4. **Draft gate:** you approve the copy.
5. `send_test.py --send` mails only your test recipients. **Test gate:** you check it in a real inbox.
6. Claude builds the audience fresh and filters opt-outs. The send scripts show counts in a dry run.
7. **Blast gate:** only on your explicit yes does it pass the send flag.
8. It verifies delivery, pulls opt-outs back, drafts the social posts, and archives the issue.

Every script is a dry run unless you pass an explicit flag.

## What's in the box

```
product-changelog/
  SKILL.md                    the workflow Claude follows
  config.example.yaml         every company-specific value, with placeholders
  templates/
    email.html                styled-minimal email layout
    email.txt                 plain text twin
  scripts/
    _common.py                config, Resend client, first-name cleaning, signed unsubscribe links
    lint_email.py             copy and link checks; exits 1 on failure
    send_test.py              test send to your own addresses (dry run by default)
    blast.py                  one-by-one send with opt-out filtering, resumable
    broadcast_sync.py         upsert contacts into a Resend audience, never resubscribes
    broadcast_create.py       create a broadcast draft; send only with an explicit flag
    broadcast_unsubs.py       pull opt-outs from Resend into a local list
    verify_delivery.py        spot-check delivery of a blast
  references/
    voice-and-format.md       picking items, subject lines, sentences, styling
    screenshots.md            staging, capture, hosting
    sending.md                audience, both send paths, subscriber math
    social.md                 X, LinkedIn and community templates
    video.md                  optional motion recap
```

## License

MIT. See [LICENSE](LICENSE).
