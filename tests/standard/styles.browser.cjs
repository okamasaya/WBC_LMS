const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const base = `${process.env.CBT_TEST_BASE_URL || 'http://127.0.0.1:8000'}/prototype/language/JLPT_N2/`;
const screenshotDir = process.env.CBT_TEST_SCREENSHOT_DIR;
async function style(page, selector, properties) {
    return page.locator(selector).first().evaluate((element, keys) => {
        const computed = getComputedStyle(element);
        return Object.fromEntries(keys.map(key => [key, computed[key]]));
    }, properties);
}
async function snapshot(page, name) {
    if (!screenshotDir) return;
    fs.mkdirSync(screenshotDir, { recursive: true });
    await page.screenshot({ path: path.join(screenshotDir, `${name}.png`), fullPage: true });
}
(async () => {
    const browser = await chromium.launch({ executablePath: process.env.CBT_TEST_CHROMIUM || '/usr/bin/chromium', headless: true, args: ['--no-sandbox'] });
    try {
        const actual = await browser.newPage({ viewport: { width: 1280, height: 900 } });
        const drill = await browser.newPage({ viewport: { width: 1280, height: 900 } });
        const errors = [];
        for (const page of [actual, drill]) {
            page.on('pageerror', error => errors.push(error.message));
            page.on('dialog', dialog => dialog.accept());
        }
        await actual.goto(base + 'Actual_N2_261030.html');
        await drill.goto(base + 'Drill_N2_261031.html');
        await actual.locator('#start').waitFor({ state: 'visible' });
        await drill.waitForFunction(() => !document.getElementById('start-exam').disabled);
        assert.deepEqual(await style(actual, '.learning-start', ['maxWidth', 'padding', 'borderRadius']), await style(drill, '.learning-start', ['maxWidth', 'padding', 'borderRadius']));
        await drill.locator('#question-count-select').focus();
        await drill.keyboard.press('Tab');
        assert.equal(await drill.evaluate(() => document.activeElement.id), 'category-lv1-select');
        assert.equal((await style(drill, '#category-lv1-select', ['outlineWidth'])).outlineWidth, '3px');
        await actual.locator('#start').click();
        await drill.locator('#start-exam').click();
        await actual.locator('input[name=answer]').first().check();
        await drill.locator('.option-btn').first().click();
        const questionProperties = ['fontSize', 'fontFamily', 'marginTop', 'marginBottom'];
        assert.deepEqual(await style(actual, '.learning-question', questionProperties), await style(drill, '.learning-question', questionProperties));
        const selectedProperties = ['backgroundColor', 'borderTopColor', 'borderRadius', 'fontWeight', 'padding'];
        assert.deepEqual(await style(actual, '.choice:has(input:checked)', selectedProperties), await style(drill, '.option-btn.selected', selectedProperties));
        await snapshot(actual, 'actual-question-desktop');
        await snapshot(drill, 'drill-question-desktop');
        for (const width of [320, 390, 768]) {
            for (const page of [actual, drill]) {
                await page.setViewportSize({ width, height: 900 });
                assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
                assert.equal((await style(page, '.card', ['padding'])).padding, '20px');
                assert.equal((await style(page, '.learning-confidence-grid', ['gridTemplateColumns'])).gridTemplateColumns.includes(' '), false);
            }
        }
        await snapshot(actual, 'actual-question-tablet');
        await snapshot(drill, 'drill-question-tablet');
        for (const page of [actual, drill]) {
            await page.setViewportSize({ width: 1280, height: 900 });
            // Public theme contract: one override changes both modes and their result panels.
            await page.evaluate(() => {
                document.body.style.setProperty('--learning-color-primary', '#6b3fa0');
                document.body.style.setProperty('--learning-color-primary-soft', '#f3eaff');
            });
        }
        for (const [page, selector] of [[actual, '.choice:has(input:checked)'], [drill, '.option-btn.selected']]) {
            const selected = await style(page, selector, ['backgroundColor', 'borderTopColor']);
            assert.equal(selected.backgroundColor, 'rgb(243, 234, 255)');
            assert.equal(selected.borderTopColor, 'rgb(107, 63, 160)');
        }
        await drill.locator('.conf-btn').first().click();
        assert.equal((await style(drill, '.option-btn:disabled', ['opacity'])).opacity, '1');
        await actual.locator('#finish').click();
        assert.equal(await actual.locator('#finish-dialog').isVisible(), true);
        await actual.locator('#confirm-finish').click();
        await drill.getByRole('button', { name: '演習を終了して採点', exact: true }).click();
        for (const page of [actual, drill]) {
            await page.locator('#comp-btn-0-3').click();
            await page.mouse.move(0, 0);
            await page.waitForFunction(() => getComputedStyle(document.getElementById('comp-btn-0-3')).backgroundColor === 'rgb(107, 63, 160)');
            assert.equal((await style(page, '#comp-btn-0-3', ['backgroundColor'])).backgroundColor, 'rgb(107, 63, 160)');
            const before = await style(page, '#generate-report', ['backgroundColor', 'color']);
            await page.locator('#generate-report').hover();
            assert.deepEqual(await style(page, '#generate-report', ['backgroundColor', 'color']), before);
            assert.equal(before.backgroundColor, 'rgb(107, 63, 160)');
            await page.locator('#generate-report').click();
            for (const action of ['copy', 'raw', 'questions', 'session']) {
                const button = `[data-action=${action}]`;
                const color = await style(page, button, ['backgroundColor', 'color']);
                await page.locator(button).hover();
                assert.deepEqual(await style(page, button, ['backgroundColor', 'color']), color);
            }
            await page.locator('[data-action=session]').focus();
            await page.keyboard.press('Tab');
            assert.equal(await page.evaluate(() => document.activeElement.id), 'report-text');
            assert.equal((await style(page, '#report-text', ['outlineWidth'])).outlineWidth, '3px');
            for (const width of [320, 390, 768]) {
                await page.setViewportSize({ width, height: 900 });
                assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
                assert.equal(await page.locator('#report-text').isVisible(), true);
            }
        }
        // The old page does not load learning.css; shared result styles must still work.
        const legacy = await browser.newPage();
        legacy.on('pageerror', error => errors.push(error.message));
        legacy.on('dialog', dialog => dialog.accept());
        await legacy.goto(base + 'separete_drill_261026.html');
        await legacy.waitForFunction(() => typeof originalQuizData !== 'undefined' && originalQuizData.length > 0);
        await legacy.evaluate(() => { startExam(); submitExam(true); });
        await legacy.locator('#comp-btn-0-3').click();
        await legacy.mouse.move(0, 0);
        await legacy.waitForFunction(() => getComputedStyle(document.getElementById('comp-btn-0-3')).backgroundColor === 'rgb(37, 99, 235)');
        const legacySelected = await style(legacy, '#comp-btn-0-3', ['backgroundColor', 'color']);
        assert.equal(legacySelected.backgroundColor, 'rgb(37, 99, 235)');
        assert.equal(legacySelected.color, 'rgb(255, 255, 255)');
        assert.equal((await style(legacy, '#generate-report', ['backgroundColor'])).backgroundColor, 'rgb(30, 58, 138)');
        assert.deepEqual(errors, []);
        console.log('PASS shared styles: aligned question/selection/start layout, 320/390/768px screens, theme overrides, keyboard focus, export hover colors and legacy fallbacks');
    } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
