# Changelog video (optional)

A 15 to 25 second animated recap of the issue, built from the same screenshots. It is for social and community posts, not the email (most mail clients do not play video). Make it only when the user asks, and only after the email is sent.

## Approach

[Remotion](https://www.remotion.dev) renders React components to mp4 and works well for this. Check its license for your company size before you use it commercially (it is free for small teams; larger companies need a paid company license). Any tool that can animate a headline over a screenshot works too (After Effects, Motion, Canva, ffmpeg with drawtext).

## Style that works

- **No title slide.** Open directly on the first item's headline. The first frame should already be the product.
- **Motion reel, not slides.** Static text-left, image-right slides with fades look like a slide deck. Instead, per item:
  1. A big headline pops in word by word.
  2. It glides up and shrinks while the screenshot sweeps in from below with a slight 3D settle.
  3. A slow push-in runs the whole beat so no frame is static.
  4. The beat ends with a zoom-through transition (scale up, blur, fade) into the next.
- **Plain dark background** (a flat near-black), no grid or glow decoration. Use the product's own font.
- **Minimal text**: a short headline and at most one short muted sub-line per item. Cut the email paragraphs down hard. No "1 / 5" counters.
- **Visuals dominate**: screenshots fill most of the frame (about 70 percent of the height) with a slow continuous zoom drift.
- **Fast**: about 3 to 3.5 seconds per item (90 to 110 frames at 30 fps), around 20 seconds total.
- End on a simple outro card: a thank-you line and the product URL.
- Same copy rules as the email: banned phrases, no dashes if that style is on.
- 1920x1080 at 30 fps for X and LinkedIn; also render a 1080x1920 cut if the user posts vertical video.

## Minimal Remotion outline

```bash
npx create-video@latest changelog-video   # pick the blank template
cd changelog-video
mkdir -p public/shots                     # copy the issue PNGs here
```

Structure `src/Video.tsx` as a list of beats in the same order as the email:

```tsx
const BEATS = [
  { headline: 'Export to Sheets', sub: 'Any report, one click', shot: 'shots/014-export.png' },
  { headline: 'Faster search', sub: 'Results as you type', shot: 'shots/014-search.png' },
];
const BEAT = 100; // frames per beat at 30 fps

export const Video = () => (
  <AbsoluteFill style={{ background: '#0a0a0a' }}>
    {BEATS.map((b, i) => (
      <Sequence key={i} from={i * BEAT} durationInFrames={BEAT}>
        <FeatureBeat {...b} />
      </Sequence>
    ))}
    <Sequence from={BEATS.length * BEAT} durationInFrames={60}>
      <Outro />
    </Sequence>
  </AbsoluteFill>
);
```

Inside `FeatureBeat`, drive everything from `useCurrentFrame()` with `spring()` and `interpolate()`: word-by-word headline entrance, headline translate and scale after about 25 frames, screenshot translateY plus a small rotateX settle, a slow overall scale from 1.0 to 1.05, and scale plus blur plus opacity out in the last 10 frames.

Before the full render, spot-check a few frames with `npx remotion still` and fix layout. Then `npx remotion render`. Hand the user the local mp4, and attach it to the community post if that channel has a posting tool in `social.post_via`. If the team needs a paid Remotion license, ask the user before using it commercially: that is money.
