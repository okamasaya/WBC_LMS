const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const rootURL = process.env.CBT_TEST_BASE_URL || 'http://127.0.0.1:8000';
const indexURL = `${rootURL}/prototype/language/JLPT_N2/index.html`;
(async () => {
    const { auditRuntime } = await import('../../scripts/audit-standard-runtime.mjs');
    const allowed = new Set(auditRuntime().files);
    const browser = await chromium.launch({ executablePath: process.env.CBT_TEST_CHROMIUM || '/usr/bin/chromium', headless: true, args: ['--no-sandbox'] });
    try {
        const errors = [], denied = [];
        const context = await browser.newContext();
        await context.route('**/*', route => {
            const url = new URL(route.request().url());
            const prefix = '/prototype/';
            const relative = decodeURIComponent(url.pathname.slice(prefix.length));
            if (url.origin === new URL(rootURL).origin && url.pathname.startsWith(prefix) && allowed.has(relative)) return route.continue();
            if (url.pathname.endsWith('/favicon.ico')) return route.fulfill({ status: 204 });
            denied.push(url.pathname);
            return route.abort();
        });
        const page = await context.newPage();
        page.on('pageerror', error => errors.push(error.message));
        page.on('response', response => { if (response.status() >= 400) errors.push(`${response.status()} ${new URL(response.url()).pathname}`); });
        await page.goto(indexURL);
        assert.equal(await page.locator('.mode-card').count(), 2);
        await page.getByRole('link', { name: /練習ドリル/ }).click();
        await page.waitForFunction(() => !document.getElementById('start-exam').disabled);
        await page.locator('#start-exam').click();
        await page.locator('.option-btn').first().click();
        await page.locator('.conf-btn').first().click();
        assert.equal(await page.locator('#instant-feedback').isVisible(), true);
        await page.goto(indexURL);
        await page.getByRole('link', { name: /CBT模擬試験/ }).click();
        await page.locator('#start').click();
        assert.equal(await page.locator('#palette button').count(), 30);
        // This page warns on leaving an active exam; accept only our own navigation.
        page.on('dialog', dialog => dialog.accept());
        await page.setViewportSize({ width: 390, height: 844 });
        await page.goto(indexURL);
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
        assert.equal(await page.getByRole('link', { name: /練習ドリル/ }).isVisible(), true);
        assert.equal(await page.getByRole('link', { name: /CBT模擬試験/ }).isVisible(), true);
        assert.deepEqual(denied, []);
        assert.deepEqual(errors, []);
        console.log('PASS current entry: both modes run using only the declared runtime files; mobile entry and no missing assets');
    } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
