# Voice and formatting

Rules for the changelog email itself. They come from many rounds of real edits on a recurring product email. Defaults are opinionated on purpose. If the user's config `voice.notes` says otherwise, the config wins.

## Picking what goes in

- Source the candidates: `git log --since=<last issue date> --no-merges --oneline`, merged pull requests, release notes, the public roadmap, support threads that got resolved. Optionally ask the user what shipped that is not in git (pricing, partnerships, docs); if they are not around, go ahead with git and release notes.
- Keep only **user-visible** changes. Refactors, infra moves, dependency bumps and internal tools are out unless a user would notice the result (faster, cheaper, fewer errors). Then write about the result, not the work.
- **3 to 5 items.** Fewer, better items beat a long list. If 8 things shipped, the bottom 3 wait or go into one closing sentence.
- **Rank by usefulness to the reader**, not by effort or by what the team is proudest of. Lead with the change that most readers can use today.
- Things requested by customers go high. Say so plainly: "A lot of you asked for X."
- Policy notices (billing deadlines, deprecations, deletions) go in the email when users must act, but low and short, and never in the social posts.
- Every claim must match the live product and the live website. If the pricing page says "up to", the email says "up to". Check before you write it.
- Describe features modestly and concretely. A new view is "a new view for your projects", not "an operating system". Do not inflate a UI change into a platform claim.

## Subject line

- Benefit-led and product-first: what the reader can now do. "You can now export reports to Sheets" beats "Changelog #12" and beats "Product update: October".
- Never "Changelog #N" in the subject. The number belongs in the archive, not the inbox.
- Under about 60 characters so it does not truncate on phones.
- No emoji, no clickbait, no ALL CAPS.

## Structure

1. `Hi {{NAME}},` (falls back to `Hi there,` when there is no usable first name).
2. One plain opener line from config, for example "Here's what's new on Acme this week." Not "Welcome to this week's changelog". Do not reuse a first-issue welcome line after issue one.
3. The lead item, with the hero screenshot.
4. The remaining items, each one short paragraph, screenshots only where they help.
5. Optional personal P.S. in a casual register: "BTW, ..." or "Oh and one last thing, ...".
6. Sign-off from config: `Best,` / sender name / sender title.
7. Last line, small and muted (about 12px, muted color): `If you'd rather not receive these, unsubscribe here.` It goes at the very end, not in the intro.

## Sentences

- **Flowing sentences, not labeled bullets.** "We released the SDK for TypeScript and Python, so you can..." and not "* SDK: released for TS and Python". Readers spot labeled feature bullets as machine-written.
- Explain the **why** for each item, not just the what. One sentence of what, one of why it matters.
- Short sentences. Plain words. Second person ("you can now") over first person ("we have built").
- Write like the sender talks. A real person signs the email, so it should read like that person wrote it to a customer they like.
- **Bolding: one accent per paragraph at most** (the feature name, the call to action, or the punchline). Not more.

## Phrases to avoid

These read as marketing filler or as AI-written. The linter flags the ones in `voice.banned_phrases`.

- "We're excited to announce", "thrilled to share", "we're proud to"
- "game-changer", "revolutionize", "seamless", "unlock", "leverage", "supercharge", "delve"
- "In today's fast-paced world", "Look no further"
- "Join us here", "Don't miss out"
- Any internal or retired product term. Keep a list of those in `voice.banned_phrases` too.

Optional house style, on by default (`voice.no_dashes: true`): no em dashes or en dashes anywhere. Use a comma, a colon, a period or a plain hyphen. Also sweep the HTML entity forms (`mdash` and `ndash`, named or numeric). Many readers now treat the em dash as an AI tell.

## HTML styling: styled-minimal

Fully plain text looks broken in modern clients, and heavy templates look like marketing. The middle works best:

- One 600px centered wrapper, the system font stack, 15px at 1.65 line height.
- Links in the brand link color from config.
- Screenshots full width (max 600px), `border-radius:8px`, a 1px hairline border, always with descriptive `alt` text.
- The hero screenshot is clickable and deep-links to the feature.
- No buttons, no columns, no header banner, no footer art, no tracking-pixel tricks. Inline styles only (many clients strip `<style>` blocks).
- Always send a matching plain text part (`email.txt`) with the same words and bare URLs.

## Links

- Every link is a real, working URL that returns 200. Never a redirect wrapper (some mail tools rewrite links into `google.com/url?q=...`; strip those).
- Plain, readable URLs. Deep links to the exact page or setting, not the homepage.
- No UTM clutter unless the user wants it; if they do, keep it consistent.

## Self-review before anything goes out

Read it once as a busy customer would, top to bottom, and fix anything that fails:

- Would a reader know in 5 seconds what the most useful change is?
- Is every item something they can see or use?
- Does any sentence sound like a press release? Rewrite it as speech.
- Do all claims match the live site?
- Does `scripts/lint_email.py ISSUE_DIR --check-links` pass?
