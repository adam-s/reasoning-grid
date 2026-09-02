import { chromium } from '@playwright/test';
const b = await chromium.launch();
for (const url of [
  'https://adamsohn.com/reasoning-grid/#walk-the-surface',
  'https://adamsohn.com/reasoning-grid#walk-the-surface',
]) {
  const p = await b.newPage({ viewport:{width:1440,height:900} });
  const errs = [];
  p.on('console', m => m.type()==='error' && errs.push(m.text()));
  p.on('pageerror', e => errs.push('PAGEERROR: ' + String(e)));
  await p.goto(url, { waitUntil:'load' });
  await p.waitForTimeout(3000);
  const r = await p.evaluate(() => ({
    href: location.href,
    scrollY: Math.round(window.scrollY),
    bodyText: document.body.innerText.length,
    appChildren: document.getElementById('app')?.children.length ?? -1,
    figs: document.querySelectorAll('[data-fig]').length,
    pending: document.querySelectorAll('[data-fig].pending').length,
    canvases: document.querySelectorAll('canvas').length,
    docH: document.documentElement.scrollHeight,
  }));
  console.log(url);
  console.log('  ', JSON.stringify(r));
  console.log('   errors:', errs.length ? errs.slice(0,4) : 'none');
  await p.close();
}
await b.close();
