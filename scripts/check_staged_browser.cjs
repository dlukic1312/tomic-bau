// Check all published HTML routes at two viewport widths against the staged artifact.
const { chromium } = require('playwright');
const fs = require('node:fs');
const manifest = JSON.parse(fs.readFileSync('publish-manifest.json','utf8'));
(async () => {
  const browser = await chromium.launch({headless:true});
  const failures = [];
  try {
    for (const width of [390,1280]) {
      const context = await browser.newContext({viewport:{width,height:900}});
      for (const route of manifest.filter(x => x.endsWith('.html'))) {
        const page = await context.newPage();
        const errors = [];
        page.on('pageerror', e => errors.push('JS: '+e.message));
        page.on('response', r => {if(r.url().startsWith('http://127.0.0.1:8765/') && r.status()>=400 && !r.url().endsWith('/favicon.ico')) errors.push('HTTP '+r.status()+': '+r.url());});
        page.on('requestfailed', r => {if(r.url().startsWith('http://127.0.0.1:8765/') && !r.url().endsWith('/favicon.ico') && r.failure()?.errorText!=='net::ERR_ABORTED') errors.push('Request: '+r.url());});
        try {
          const response = await page.goto('http://127.0.0.1:8765/'+route,{waitUntil:'load',timeout:30000});
          if(!response?.ok()) throw Error('Route unavailable');
          await page.locator('body').waitFor();
          await page.evaluate(async () => { for(const im of document.images) im.loading='eager'; await Promise.all([...document.images].map(im => im.decode().catch(()=>{}))); });
          const broken = await page.evaluate(() => [...document.images].filter(im=>im.complete && !im.naturalWidth && im.getAttribute('src')).map(im=>im.src));
          for (const img of broken) errors.push('Broken image: '+img);
        } catch(e) {errors.push(String(e));}
        await page.close();
        if(errors.length) failures.push(width+' '+route+': '+errors.join('; '));
        else console.log('PASS',width,route);
      }
      await context.close();
    }
  } finally {await browser.close();}
  if(failures.length) {console.error(failures.join('\n'));process.exit(1);}
  console.log('All staged HTML routes passed basic browser smoke checks');
})().catch(e=>{console.error(e);process.exit(1);});
