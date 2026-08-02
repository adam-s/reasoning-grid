import { chromium } from '@playwright/test';
const b = await chromium.launch();
for (const [w, h, label] of [[390,844,'iPhone 14'],[430,932,'iPhone Pro Max'],[768,1024,'iPad portrait'],[1024,768,'iPad landscape'],[1440,900,'desktop']]) {
  const p = await b.newPage({ viewport: { width: w, height: h } });
  await p.goto('http://localhost:5175/', { waitUntil: 'networkidle' });
  await p.waitForTimeout(300);
  const r = await p.evaluate(() => {
    const svgs = [...document.querySelectorAll('svg')].map(e => Math.round(e.getBoundingClientRect().width));
    return { docW: document.documentElement.scrollWidth, winW: window.innerWidth, svgs };
  });
  const over = r.docW > r.winW + 1;
  console.log(`  ${label.padEnd(17)} vp ${String(w).padStart(4)}  doc ${String(r.docW).padStart(4)}  ` +
              `charts [${r.svgs.join(', ')}]  ${over ? '*** OVERFLOW ***' : 'ok'}`);
  await p.close();
}
await b.close();
