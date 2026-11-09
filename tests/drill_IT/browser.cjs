const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const base = process.env.CBT_TEST_BASE_URL || 'http://127.0.0.1:8000';
const entry = `${base}/prototype/it/GenAI_Passport/index.html`;
const bank = JSON.parse(fs.readFileSync(path.join(__dirname, '../../prototype/it/GenAI_Passport/data/sample_questions.json')));
const artifacts = process.env.IT_DRILL_TEST_DIR || '/tmp/it-drill-browser';
fs.mkdirSync(artifacts, { recursive: true });
async function save(page, type) {
    const event = page.waitForEvent('download');
    await page.locator(`[data-download="${type}"]`).click();
    const file = await event;
    const target = path.join(artifacts, file.suggestedFilename());
    await file.saveAs(target);
    return fs.readFileSync(target, 'utf8').replace(/^\uFEFF/, '');
}
function csvRows(text) {
    const rows = [], row = []; let cell = '', quoted = false;
    for (let i = 0; i < text.length; i++) {
        const c = text[i];
        if (c === '"') {
            if (quoted && text[i + 1] === '"') { cell += '"'; i++; }
            else quoted = !quoted;
        } else if (!quoted && (c === ',' || c === '\r' || c === '\n')) {
            row.push(cell); cell = '';
            if (c !== ',') { rows.push([...row]); row.length = 0; if (c === '\r' && text[i + 1] === '\n') i++; }
        } else cell += c;
    }
    assert.equal(quoted, false);
    const headers = rows.shift();
    return rows.map(values => Object.fromEntries(headers.map((key, i) => [key, values[i]])));
}
async function ready(page, url = entry) {
    await page.goto(url);
    await page.locator('#start-exam').waitFor({ state: 'visible' });
    await page.waitForFunction(() => !document.getElementById('start-exam').disabled);
}
async function begin(page, mode, topic, confidence = true) {
    await ready(page);
    await page.selectOption('#mode-select', mode);
    if (topic) await page.selectOption('#topic-select', topic);
    await page.locator('#use-confidence-checkbox').setChecked(confidence);
    await page.locator('#start-exam').click();
}
async function finish(page) {
    page.once('dialog', dialog => dialog.accept());
    await page.locator('#finish-exam').click();
    await page.locator('#score-container').waitFor({ state: 'visible' });
}
async function generate(page) {
    page.once('dialog', dialog => dialog.accept());
    await page.locator('#generate-report').click();
    await page.locator('#output-section').waitFor({ state: 'visible' });
}
(async () => {
    const browser = await chromium.launch({ executablePath: process.env.CBT_TEST_CHROMIUM || '/usr/bin/chromium', headless: true, args: ['--no-sandbox'] });
    const context = await browser.newContext({ acceptDownloads: true });
    const page = await context.newPage();
    page.setDefaultTimeout(10000);
    const errors = [], badResponses = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('response', r => { if (r.status() >= 400 && !r.url().includes('fixture')) badResponses.push(`${r.status()} ${r.url()}`); });
    try {
        // Both directions: choose from the target pool without interpreting option IDs.
        for (const mode of ['appropriate', 'inappropriate']) {
            await ready(page);
            if (mode === 'appropriate') {
                await page.setViewportSize({ width: 320, height: 844 });
                assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
                await page.screenshot({ path: path.join(artifacts, 'sample-start-mobile.png'), fullPage: true });
                await page.setViewportSize({ width: 1280, height: 900 });
            }
            await page.selectOption('#mode-select', mode);
            await page.selectOption('#chapter-select', '4');
            assert.equal(await page.locator('#topic-select option').count(), 3);
            await page.locator('#start-exam').click();
            const stem = await page.locator('#question-text').innerText();
            const q = bank.questions.find(q => q.stems[mode] === stem);
            assert.ok(q);
            const optionTexts = await page.locator('.option-text').allTextContents();
            const target = optionTexts.findIndex(text => q.pools[mode].some(o => o.text === text));
            const wrong = optionTexts.findIndex((_, i) => i !== target);
            assert.equal(optionTexts.filter(text => q.pools[mode].some(o => o.text === text)).length, 1);
            assert.equal(await page.locator('#instant-feedback').isVisible(), false);
            await page.locator('.option-btn').nth(wrong).click();
            assert.equal(await page.locator('#instant-feedback').isVisible(), false);
            await page.locator('.option-btn').nth(target).click();
            await page.locator('[data-confidence="2"]').click();
            assert.equal(await page.locator('#feedback-title').innerText(), '正解です');
            assert.equal(await page.locator('#instant-feedback li').count(), 4);
            assert.equal(await page.locator('.option-btn:disabled').count(), 4);
            await page.locator('#next-question').click();
            await page.locator('.option-btn').first().click(); // pending, not confirmed
            await page.locator('#previous-question').click();
            assert.deepEqual(await page.locator('.option-text').allTextContents(), optionTexts);
            assert.equal(await page.locator('.option-btn.selected').count(), 1);
            await page.locator('#next-question').click();
            assert.equal(await page.locator('.option-btn.selected').count(), 1);
            assert.equal(await page.locator('#confidence-panel').isVisible(), true);
            await finish(page);
            assert.match(await page.locator('#final-score').innerText(), /1 \/ 2.*未回答 1/);
            // Cancel finalization, then set real zero understanding before accepting missing values.
            page.once('dialog', d => d.dismiss());
            await page.locator('#generate-report').click();
            assert.equal(await page.locator('#output-section').isVisible(), false);
            await page.locator('#review-item-0 .comp-btn').last().click();
            await generate(page);
            const snapshot = JSON.parse(await save(page, 'json'));
            const r = snapshot.records[0];
            assert.equal(r.questionMode, mode);
            assert.equal(r.understandingLevel, 0);
            assert.equal(r.confidenceLevel, 2);
            assert.deepEqual(r.displayedOptions.map(o => o.text), optionTexts);
            assert.equal(r.selectedOptionId, r.correctOptionId);
            assert.equal(r.displayedOptions.filter(o => o.pool === mode).length, 1);
            assert.equal(snapshot.records[1].selectedOptionId, null);
            assert.equal(snapshot.records[1].answeredAt, null);
            assert.equal(snapshot.records[1].isAnswered, false);
            await page.setViewportSize({ width: 320, height: 844 });
            assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
            await page.setViewportSize({ width: 1280, height: 900 });
            const questions = csvRows(await save(page, 'questions'));
            assert.deepEqual(JSON.parse(questions[0].displayedOptions), r.displayedOptions);
            const options = csvRows(await save(page, 'options'));
            assert.equal(options.length, 8);
            assert.equal(options.filter(o => o.isSelected === 'TRUE').length, 1);
            assert.equal(csvRows(await save(page, 'session'))[0].CorrectCount, '1');
            const analysis = JSON.parse((await page.locator('#report-text').inputValue()).split('=== AI_ANALYSIS_DATA_JSON ===\n')[1]);
            assert.deepEqual(analysis.itSnapshot, snapshot);
            if (mode === 'appropriate') await page.screenshot({ path: path.join(artifacts, 'sample-desktop.png'), fullPage: true });
            await page.locator('#review-item-0 .review-flag-cb').check();
            assert.equal(await page.locator('#output-section').isVisible(), false);
            assert.equal(await page.locator('#report-text').inputValue(), '');
            await generate(page);
            assert.equal(JSON.parse(await save(page, 'json')).records[0].reviewFlag, true);
        }
        console.log('PASS both polarities, confidence gating, fixed revisits, pending/unanswered semantics, all downloads, zero understanding and output invalidation');

        await begin(page, 'inappropriate', 'GAIP-CH01-Q007', false);
        const q = bank.questions.find(q => q.question_id === 'GAIP-CH01-Q007');
        const texts = await page.locator('.option-text').allTextContents();
        const wrong = texts.findIndex(t => q.pools.appropriate.some(o => o.text === t));
        await page.locator('.option-btn').nth(wrong).click();
        assert.equal(await page.locator('#feedback-title').innerText(), '不正解です');
        assert.equal(await page.locator('#confidence-panel').isVisible(), false);
        await finish(page); await generate(page);
        const incorrect = JSON.parse(await save(page, 'json')).records[0];
        assert.equal(incorrect.isAnswered, true); assert.equal(incorrect.isCorrect, false);
        assert.equal(incorrect.selectedPool, 'appropriate'); assert.equal(incorrect.confidenceLevel, null);
        console.log('PASS appropriate content is a wrong answer when the stem asks for inappropriate content; confidence-off confirmation');

        await page.addInitScript(() => { let seed = 42; Math.random = () => ((seed = (Math.imul(1664525, seed) + 1013904223) >>> 0) / 2 ** 32); });
        await begin(page, 'mixed', null, false);
        await finish(page); await generate(page);
        const mixed = JSON.parse(await save(page, 'json'));
        assert.equal(mixed.records.length, 6);
        assert.equal(new Set(mixed.records.map(r => r.questionId)).size, 6);
        assert.deepEqual(new Set(mixed.records.map(r => r.questionMode)), new Set(['appropriate', 'inappropriate']));
        assert.equal(mixed.summary.unansweredQuestions, 6);
        console.log('PASS mixed mode, no duplicate themes and all-unanswered output');

        // A config in a subdirectory resolves its data relative to itself, not to the HTML.
        const custom = structuredClone(bank); custom.questions = [custom.questions[0]];
        custom.questions[0].stems.appropriate += '\n<b>文字列として表示</b>';
        custom.questions[0].explanation += '\n<img src=x onerror=alert(1)>';
        custom.questions[0].pools.appropriate[0].text += '\n<img src=x onerror=alert(1)>';
        custom.questions[0].pools.appropriate.push({ option_id: 'CUSTOM_A04', text: '構造・描画テスト用の追加候補', explanation: '内容を校正するテストではありません' });
        const config = { version: 1, title: '別教材 <b>タイトル</b>', examId: custom.exam_id, bankFiles: ['../fixture-data/bank.json'] };
        await page.route('**/fixture-config/conf.json', r => r.fulfill({ json: config }));
        await page.route('**/fixture-data/bank.json', r => r.fulfill({ json: custom }));
        await ready(page, `${entry}?conf=fixture-config/conf.json`);
        assert.equal(await page.locator('#title-display b').count(), 0);
        await page.locator('#use-confidence-checkbox').uncheck();
        await page.locator('#start-exam').click();
        assert.match(await page.locator('#question-text').innerText(), /<b>文字列/);
        assert.equal(await page.locator('#question-text b').count(), 0);
        await page.locator('.option-btn').first().click();
        assert.match(await page.locator('#instant-feedback').innerText(), /<img src=x/);
        assert.equal(await page.locator('#instant-feedback img').count(), 0);
        for (const width of [320, 390, 768]) {
            await page.setViewportSize({ width, height: 844 });
            assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
        }
        await page.screenshot({ path: path.join(artifacts, 'mobile.png'), fullPage: true });
        await finish(page);
        await page.setViewportSize({ width: 1366, height: 900 });
        await page.screenshot({ path: path.join(artifacts, 'review-desktop.png'), fullPage: true });
        console.log('PASS custom relative config, unequal pools, plain-text rendering and 320/390/768px layouts');

        const cases = [
            { status: 404, message: /HTTP 404/ },
            { bank: (() => { const b = structuredClone(bank); b.questions[0].pools.inappropriate.pop(); return b; })(), message: /GAIP-CH01-Q011.*3件未満/ },
            { bank: (() => { const b = structuredClone(bank); delete b.questions[0].stems.inappropriate; return b; })(), message: /inappropriate がありません/ },
            { bank: (() => { const b = structuredClone(bank); b.questions[0].question_id = b.questions[1].question_id; return b; })(), message: /IDが重複/ }
        ];
        for (const c of cases) {
            await page.unroute('**/fixture-data/bank.json');
            await page.route('**/fixture-data/bank.json', r => r.fulfill(c.status ? { status: c.status, body: 'not found' } : { json: c.bank }));
            await page.goto(`${entry}?conf=fixture-config/conf.json`);
            await page.locator('#description-display[role="alert"]').waitFor();
            assert.match(await page.locator('#description-display').innerText(), c.message);
            assert.equal(await page.locator('#start-exam').isDisabled(), true);
        }
        assert.deepEqual(errors, []);
        assert.deepEqual(badResponses, []);
        console.log('PASS missing data and invalid banks block start with useful errors; no uncaught errors or missing runtime assets');
    } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
