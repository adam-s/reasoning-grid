import { chromium } from '@playwright/test';
const b = await chromium.launch();
for (const vw of [1440, 1180, 900, 800, 760, 740, 720, 700, 500, 390]) {
  const p = await b.newPage({ viewport: { width: vw, height: 900 } });
  await p.goto('http://localhost:5175/', { waitUntil: 'networkidle' });
  await p.waitForTimeout(400);
  const plot = await p.locator('.plot').first().boundingBox();
  const rail = await p.locator('.rail').first().boundingBox().catch(() => null);
  const ok = !rail || rail.height + 10 <= plot.height;
  console.log(`  vw ${String(vw).padStart(4)}  plot ${String(Math.round(plot.height)).padStart(3)}px  ` +
    (rail ? `rail ${Math.round(rail.height)}px  ${ok ? 'fits' : '*** OVERFLOWS ***'}` : 'rail hidden'));
  await p.close();
}
await b.close();
