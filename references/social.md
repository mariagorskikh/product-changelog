# Social posts: X thread, LinkedIn, community announcement

Written after the email copy is final, from the same items in the same order. In autonomous mode, Claude self-reviews each post and publishes it with the tool named in `social.post_via` for that channel; channels with no tool get the final text and images handed over. In review mode, every draft is shown first and goes out only on the user's okay of the exact text.

Self-review before posting: banned phrases and dashes (`lint_email.py` checks `social.md`), every claim against the live site, every link returns 200, item count, images attached natively. If a platform shows a login prompt, CAPTCHA, warning or rate-limit notice, stop posting on that channel and report it.

## Rules for every channel

- 4 to 5 items max. Skip billing deadlines, deletion warnings and anything ops-flavored: social is a marketing surface, not a policy notice.
- Claims must match the live page, not the email. If the email simplified something, the post uses the precise version.
- Upload images natively. Never paste an image link. Reuse the issue screenshots.
- No emoji unless the brand uses them. Same banned phrases as the email. No em or en dashes when `voice.no_dashes` is on.
- Casual, benefit-first, tighter than the email. Start from the email's sentences and compress.

## X thread

- **Tweet 1 (the hook)** summarizes every item in one line, starting with `social.hook_prefix` ("Latest changelog:"). No link in it: X shows fewer people posts with external links. Attach the strongest screenshot.
- **One tweet per item**, numbered `1/`, `2/`, ... Each under 280 characters, with its own screenshot (replies are often seen out of context, so repeat or recrop the hero if needed).
- **Links only in the item tweets**, plain form (`yourproduct.example/docs/x`), no UTM.
- The company account posts the thread. A founder or team member quote-posts it with one informal line about their favorite item. The personal quote-post usually carries more reach than the thread, so do not skip it.

Template:

```
Tweet 1 (no link) + hero screenshot
Latest changelog: [item 1 in five words], [item 2], [item 3], and [item 4].

Tweet 2 + screenshot
1/ [Item 1 as a short headline].

[One or two sentences: what you can do now and why it is useful.]

[link]

Tweet 3 + screenshot
2/ [Item 2 headline].

[One sentence.]

[link]

...

Quote-post from a personal account
[One informal line: which item is my favorite and why, in plain speech.]
```

## LinkedIn

One post, not a thread.

- First line is the hook, because it is all that shows before "see more": `Latest [PRODUCT] changelog. Here's what shipped this [week/month]:`
- Then one short paragraph per item, each opening with the item phrase as a sentence ("Export to Sheets. ...").
- Close with one call to action and one link.
- Plain text only. LinkedIn does not render markdown bold.
- Attach screenshots as a multi-image post; a gallery usually beats a single image for product updates.
- One or two links in the body is fine at this length.
- Post from a founder's or team member's personal account; the company page reposts it.

## Community announcement (Discord, Slack, forum)

Way shorter than you think. People skim.

```
[social.community_opener, e.g. "Hey everyone, changelog #NNN is out:"]

**[Item 1 name]**: a few words. [bare link]
**[Item 2 name]**: a few words. [bare link]
**[Item 3 name]**: a few words. [bare link]

Full thread on X: [link, once the thread is live]
[Optional event or P.S. line]
```

- One line per item, no blank lines between items. Cut every explanation the link can carry.
- Do not ping everyone (`@everyone`, `@channel`) unless config or the user says this community expects it.
- Attach the changelog video as a native mp4 when one exists; Discord and Slack play small mp4s inline and the moving thumbnail carries the post.

## Save it

Put the final copy of every channel in the issue folder as `social.md`, so the next issue can copy the format.
