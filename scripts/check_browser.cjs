const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const errors = [];
  for (const width of [375, 390, 768, 1280, 1440]) {
    const page = await browser.newPage({ viewport: { width, height: 900 }, deviceScaleFactor: 1 });
    page.on('pageerror', e => errors.push(width + 'px JS: ' + e.message));
    await page.goto((process.env.GOVERNANCE_BROWSER_ROOT || 'http://127.0.0.1:8765/'), { waitUntil: 'load' });
    await page.locator('h1').waitFor();
    const result = await page.evaluate(() => ({
      documentWidth: document.documentElement.scrollWidth,
      images: [...document.images].filter(i => i.complete && !i.naturalWidth).map(i => i.src)
    }));
    if (result.documentWidth > width + 3) errors.push(width + 'px horizontal overflow: ' + result.documentWidth);
    if (result.images.length) errors.push(width + 'px broken images: ' + result.images.join(', '));
    if (width <= 390) {
      await page.locator('.menu').click();
      if (await page.locator('.menu').getAttribute('aria-expanded') !== 'true') errors.push(width + 'px menu not expanded');
      await page.locator('#navlinks a[href="#leistungen"]').click();
      if (await page.locator('.menu').getAttribute('aria-expanded') !== 'false') errors.push(width + 'px menu not collapsed');
    }
    if (width === 1280) {
      await page.locator('.filter[data-filter="Asphalt"]').click();
      if (await page.locator('.project:visible').count() < 1) errors.push('Filter shows no asphalt references');
      await page.locator('.filter[data-filter="Alle"]').click();
      await page.locator('.open-photo').first().click();
      if (!(await page.locator('#lightbox').evaluate(e => e.open))) errors.push('Reference image modal did not open');
      await page.locator('#close').click();
      if (await page.locator('#lightbox').evaluate(e => e.open)) errors.push('Reference image modal did not close');
    }
    console.log('Viewport ' + width + 'px: document ' + result.documentWidth + 'px, broken images ' + result.images.length);
    await page.close();
  }
  await browser.close();
  if (errors.length) { console.error(errors.join('\n')); process.exit(1); }
  console.log('PASS: browser responsive, navigation, gallery and asset checks');
})().catch(e => { console.error(e); process.exit(1); });