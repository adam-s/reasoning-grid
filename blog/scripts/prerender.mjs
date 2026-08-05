// Render the page to HTML at build time and write it into dist/index.html.
//
//   node scripts/prerender.mjs
//
// Runs after both Vite builds: the client build produces dist/, the --ssr build
// produces dist-ssr/entry-server.js. This joins them.
//
// Why: the site is a static SPA on S3 behind CloudFront, so without this the
// shipped HTML is an empty <div id="app"> and every word of the essay lives
// inside 219KB of gzipped JavaScript. Anything that reads the page without
// running JS — a fair number of crawlers, archive.org, reader-mode tools, curl
// — gets nothing at all, and a reader on a slow connection watches a blank
// screen until the bundle executes.
//
// The figures are NOT prerendered. They are canvas, rAF and matchMedia, so they
// mount on the client; see lib/components/Figure.svelte and the generated
// figure-heights.css that holds their boxes open in the meantime.
import { readFileSync, writeFileSync } from 'node:fs';

const DIST = new URL('../dist/index.html', import.meta.url);
const SSR = new URL('../dist-ssr/entry-server.js', import.meta.url);

// Any sentence that must survive the round trip. If the prerender silently
// produces nothing, this is what catches it — an empty <div id="app"> still
// renders a working page in a browser, so nothing else would.
const CANARY = 'Speed of iteration beats';

const { renderApp } = await import(SSR.href);
const { head, body } = renderApp();

if (!body.includes(CANARY)) {
  console.error(`prerender produced no prose: expected to find ${JSON.stringify(CANARY)}`);
  process.exit(1);
}

const html = readFileSync(DIST, 'utf8');
const marker = '<div id="app"></div>';
if (!html.includes(marker)) {
  console.error(`dist/index.html has no ${marker} to fill. Did index.html change?`);
  process.exit(1);
}

const out = html
  .replace('</head>', `${head}\n  </head>`)
  .replace(marker, `<div id="app">${body}</div>`);

writeFileSync(DIST, out);

const kb = (s) => `${(Buffer.byteLength(s) / 1024).toFixed(1)}KB`;
console.log(`prerendered dist/index.html: ${kb(html)} -> ${kb(out)}`);
