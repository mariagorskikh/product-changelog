# Screenshot pipeline

One good screenshot per item does more than a paragraph. The hero item always gets one.

## Stage real product state

- Use a dedicated demo or test account, never a real customer's account, and never show real customer names, emails or data.
- Stage the state that tells the story: the feature in use with believable sample data, not an empty state. Keep the staged account around so you can re-shoot later issues.
- Pick one theme (light or dark) per issue and stay with it, unless the item is about a theme.

## Capture

Playwright works well because it captures at retina scale and clips precisely. A minimal Node script:

```js
// npm i -D playwright   (once)
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,          // crisp on retina screens
    colorScheme: 'light',          // or 'dark'
    storageState: 'auth.json',     // a saved login for the demo account
  });
  await page.goto(process.env.URL);
  await page.waitForLoadState('networkidle');
  const box = await page.locator(process.env.SELECTOR).boundingBox();
  const pad = 14;                  // a little breathing room around the panel
  await page.screenshot({
    path: process.env.OUT,
    clip: { x: box.x - pad, y: box.y - pad, width: box.width + pad * 2, height: box.height + pad * 2 },
  });
  await browser.close();
})();
```

Rules of thumb:

- Clip to the relevant panel plus a small pad. A full-page screenshot shrunk to 600px is unreadable.
- Name files `<issue>-<slug>.png` (for example `014-export.png`) so they never collide across issues.
- Keep each PNG under about 400 KB. Run it through an optimizer if needed.
- Write descriptive `alt` text for every image: what it shows, in plain words. Many clients block images by default.

## Host before you send

Mail clients fetch images when the email is opened (Gmail proxies and caches them), so the URL must work at send time and keep working.

1. Put the PNGs where `paths.image_base_url` points (a public folder of your website, a CDN bucket, or object storage).
2. Deploy.
3. Confirm every image URL returns 200 **before** the blast: `python3 scripts/lint_email.py ISSUE_DIR --check-links`.

`scripts/send_test.py` embeds images inline from the issue folder when the hosted file is not deployed yet, so you can review a test before deploying. The real send never does that.

## Reuse

The same PNGs feed the social posts (upload them natively) and the video. Keep the originals in the issue folder.
