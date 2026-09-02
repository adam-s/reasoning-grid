import { chromium } from '@playwright/test';
const SP='/private/tmp/claude-501/-Users-adamsohn-Projects-carrychain/3b38d141-b33e-445e-8f2a-2411030a6a3f/scratchpad';
const b = await chromium.launch();
const ctx = await b.newContext({ viewport:{width:1440,height:900} });
const p = await ctx.newPage();
const cdp = await ctx.newCDPSession(p);
await cdp.send('Network.enable');
await cdp.send('Network.emulateNetworkConditions', {
  offline:false, latency:150, downloadThroughput: 400*1024/8, uploadThroughput: 400*1024/8 });
await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 });
p.goto('https://adamsohn.com/reasoning-grid/#walk-the-surface', { waitUntil:'commit' }).catch(()=>{});
for (const t of [800, 2000, 4000, 8000]) {
  await p.waitForTimeout(t === 800 ? 800 : t - (t===2000?800:t===4000?2000:4000));
  const r = await p.evaluate(() => ({
    y: Math.round(window.scrollY),
    docH: document.documentElement.scrollHeight,
    canv: document.querySelectorAll('canvas').length,
  })).catch(()=>({}));
  await p.screenshot({ path:`${SP}/bug-${t}.png` }).catch(()=>{});
  console.log(`t=${t}ms  ${JSON.stringify(r)}`);
}
await b.close();
