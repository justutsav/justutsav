import puppeteer from 'puppeteer-core';
const b = await puppeteer.launch({ headless: 'new', executablePath: '/usr/bin/google-chrome', args: ['--no-sandbox'] });
const p = await b.newPage();
await p.setViewport({ width: 1080, height: 260 });
await p.goto('file:///tmp/card-test.html');
await new Promise(r => setTimeout(r, 1200));
await p.screenshot({ path: '/tmp/card-shot.png' });
await b.close();
