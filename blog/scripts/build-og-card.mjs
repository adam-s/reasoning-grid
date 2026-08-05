// The card that shows when the post is pasted into Facebook, iMessage, Slack
// or anywhere else that reads Open Graph tags.
//   node scripts/build-og-card.mjs
//
// 1200x630, which is what every scraper expects and what iMessage crops least.
// GENERATED so the card cannot drift from the page: the type comes out of the
// same tokens as app.css and the figure is a committed source image, so
// rebuilding after a design change gives a card that still matches the post.
//
// The image is INLINED as a data URI rather than linked, because the page this
// renders is served from a temp file and a relative <img src> would resolve
// against the wrong directory. It also means one screenshot, one output, no
// intermediate server.
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '@playwright/test';

const here = dirname(fileURLToPath(import.meta.url));
const SOURCE = join(here, '../assets/og-source-surface.png');
const OUT = join(here, '../public/og.png');

const TITLE = 'Model Reasoning Mapped to an OODA Loop';
const DEK =
  "Reasoning models map cleanly onto Boyd's law of iteration. This measures where LLMs stop being reliable.";

const img = `data:image/png;base64,${readFileSync(SOURCE).toString('base64')}`;

// Tokens copied from app.css. Kept literal here rather than parsed, because a
// card is rendered in a bare browser with no stylesheet to inherit from.
const html = `<!doctype html><meta charset="utf-8">
<style>
  @import url('data:,');
  html, body { margin: 0; padding: 0; }
  body {
    width: 1200px; height: 630px;
    background: #fdfcf9;
    font-family: "Source Serif Pro", Charter, "Iowan Old Style", Georgia, serif;
    color: #1a1a1a;
    display: flex; flex-direction: column;
    box-sizing: border-box;
    padding: 44px 56px 0;
    overflow: hidden;
  }
  h1 {
    margin: 0;
    font-size: 46px; line-height: 1.12; font-weight: 700; letter-spacing: -0.02em;
  }
  p {
    margin: 14px 0 0;
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 21px; line-height: 1.4; color: #5a5a5a; max-width: 72ch;
  }
  /* The figure fills what is left. \`cover\` with the focus left of centre keeps
     the cliff -- the thing the post is about -- and lets the right-hand rail
     crop rather than shrinking the whole plot to fit a shape it was not drawn
     for. */
  .fig {
    flex: 1; min-height: 0; margin-top: 26px;
    border-top: 1px solid #e8e4dc;
  }
  .fig img {
    width: 100%; height: 100%;
    object-fit: cover; object-position: 34% 42%;
    display: block;
  }
  .mark {
    position: absolute; right: 56px; top: 52px;
    font-family: "JetBrains Mono", "SF Mono", ui-monospace, monospace;
    font-size: 15px; color: #9a9a9a;
  }
</style>
<div class="mark">adamsohn.com</div>
<h1>${TITLE}</h1>
<p>${DEK}</p>
<div class="fig"><img src="${img}"></div>
`;

const b = await chromium.launch();
const page = await b.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 2 });
await page.setContent(html, { waitUntil: 'load' });
await page.waitForTimeout(300);
await page.screenshot({ path: OUT });
await b.close();
console.log(`wrote ${OUT}  1200x630 @2x`);
