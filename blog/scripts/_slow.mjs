import { chromium } from '@playwright/test';
const T = process.argv[2] || 'http://localhost:4173/';
const b = await chromium.launch();
const ctx = await b.newContext({ viewport:{width:1440,height:900} });
const p = await ctx.newPage();
const cdp = await ctx.newCDPSession(p);
await cdp.send('Network.enable');
await cdp.send('Network.emulateNetworkConditions', {
  offline:false, latency:150, downloadThroughput: 400*1024/8, uploadThroughput: 400*1024/8 });
await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 });
p.goto(T + '#walk-the-surface', { waitUntil:'commit' }).catch(()=>{});
let last = 0;
for (const t of [500, 1000, 2000, 4000, 8000]) {
  await p.waitForTimeout(t - last); last = t;
  const r = await p.evaluate(() => {
    const el = document.getElementById('walk-the-surface');
    return {
      y: Math.round(window.scrollY),
      docH: document.documentElement.scrollHeight,
      btnTop: el ? Math.round(el.getBoundingClientRect().top) : null,
      canv: document.querySelectorAll('canvas').length,
    };
  }).catch(()=>({}));
  console.log(`t=${String(t).padStart(4)}ms  ${JSON.stringify(r)}`);
}
await b.close();
