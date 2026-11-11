const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const base = process.env.CBT_TEST_BASE_URL || 'http://127.0.0.1:8000';
const url = `${base}/prototype/it/GenAI_Passport/Drill_GenAI-pp_261111.html`;
const root = path.join(__dirname, '../../prototype/it/GenAI_Passport');
const bank = JSON.parse(fs.readFileSync(path.join(root, 'data/GenAI_pp_1-2-4.json')));
const examples = JSON.parse(fs.readFileSync(path.join(root, 'examples/question-bank.v0.2.0.json')));
const output = process.env.GENAI_DRILL_TEST_DIR || '/tmp/genai-drill-261111';
fs.mkdirSync(output, { recursive: true });
async function download(page, type) {
    const promise = page.waitForEvent('download');
    await page.locator(`[data-download="${type}"]`).click();
    const file = await promise, target = path.join(output, file.suggestedFilename());
    await file.saveAs(target);
    return fs.readFileSync(target, 'utf8').replace(/^\uFEFF/, '');
}
function csv(text) {
    const rows = [], row = []; let cell = '', quoted = false;
    for (let i = 0; i < text.length; i++) {
        const c = text[i];
        if (c === '"') {
            if (quoted && text[i + 1] === '"') { cell += '"'; i++; }
            else quoted = !quoted;
        } else if (!quoted && [',', '\r', '\n'].includes(c)) {
            row.push(cell); cell = '';
            if (c !== ',') { rows.push([...row]); row.length = 0; if (c === '\r' && text[i + 1] === '\n') i++; }
        } else cell += c;
    }
    assert.equal(quoted, false);
    const header = rows.shift();
    return rows.map(values => Object.fromEntries(header.map((name, i) => [name, values[i]])));
}
async function ready(page, target = url) {
    await page.goto(target);
    await page.waitForFunction(() => !document.getElementById('start-exam').disabled);
}
async function finish(page) {
    page.once('dialog', d => d.accept()); await page.locator('#finish-exam').click();
    await page.locator('#score-container').waitFor({ state: 'visible' });
}
async function generate(page) {
    page.once('dialog', d => d.accept()); await page.locator('#generate-report').click();
    await page.locator('#output-section').waitFor({ state: 'visible' });
}
const snapshot = async page => JSON.parse(await download(page, 'json'));
const optionIds = page => page.locator('.option-btn').evaluateAll(nodes => nodes.map(n => n.dataset.optionId));
async function noOverflow(page, widths) {
    for (const width of widths) {
        await page.setViewportSize({ width, height: 900 });
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `overflow at ${width}px`);
    }
}

(async () => {
    const browser = await chromium.launch({ executablePath: process.env.CBT_TEST_CHROMIUM || '/usr/bin/chromium', headless: true, args: ['--no-sandbox'] });
    const context = await browser.newContext({ acceptDownloads: true });
    const page = await context.newPage(); page.setDefaultTimeout(15000);
    const errors = [], bad = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('response', r => { if (r.status() >= 400 && !r.url().includes('fixture-v02')) bad.push(`${r.status()} ${r.url()}`); });
    try {
        await ready(page);
        assert.match(await page.locator('#bank-info').innerText(), /収録 59問.*あと1問/);
        assert.equal(await page.locator('#mode-select').inputValue(), 'standard');
        assert.equal(await page.locator('#mode-select').isDisabled(), true);
        assert.equal(await page.locator('#topic-select option').count(), 60);
        assert.deepEqual(await page.locator('#question-count-select option').evaluateAll(nodes => nodes.map(n => n.value)), ['all', '5', '10', '20', '30', '40', '50']);
        await page.selectOption('#chapter-select', '1');
        assert.equal(await page.locator('#topic-select option').count(), 20);
        await page.selectOption('#topic-select', 'TMP-Q001');
        assert.equal(await page.locator('#question-count-select option').count(), 1);
        await page.selectOption('#chapter-select', 'all');
        await noOverflow(page, [320, 390, 768]);
        await page.setViewportSize({ width: 390, height: 844 });
        await page.screenshot({ path: path.join(output, 'start-mobile.png'), fullPage: true });
        await page.setViewportSize({ width: 1366, height: 1000 });
        await page.screenshot({ path: path.join(output, 'start-desktop.png'), fullPage: true });
        await page.locator('#start-exam').click();
        const seen = new Map();
        for (let index = 0; index < bank.questions.length; index++) {
            assert.equal(await page.locator('#progress').innerText(), `問題 ${index + 1} / 59`);
            const stem = await page.locator('#question-text').innerText();
            const q = bank.questions.find(q => q.question === stem); assert.ok(q, stem);
            assert.equal(seen.has(q.question_id), false);
            const ids = await optionIds(page); seen.set(q.question_id, ids);
            assert.equal(new Set(ids).size, 4);
            const correctIds = new Set(q.pools.correct.map(o => o.option_id));
            const target = ids.findIndex(id => correctIds.has(id));
            assert.equal(ids.filter(id => correctIds.has(id)).length, 1);
            await page.locator('.option-btn').nth(target).click();
            assert.equal(await page.locator('#instant-feedback').isVisible(), false);
            await page.locator('[data-confidence="1"]').click();
            assert.equal(await page.locator('#feedback-title').innerText(), '正解です');
            assert.equal(await page.locator('#instant-feedback li').count(), 4);
            assert.equal(await page.locator('#instant-feedback li strong').filter({ hasText: 'この問いに対する正解候補' }).count(), 1);
            assert.equal((await page.locator('#instant-feedback').innerText()).includes('内容は適切'), false);
            if (index === 0) {
                await noOverflow(page, [320, 390]);
                await page.screenshot({ path: path.join(output, 'question-mobile.png'), fullPage: true });
                await page.setViewportSize({ width: 1366, height: 1000 });
                await page.locator('#next-question').click(); await page.locator('#previous-question').click();
                assert.deepEqual(await optionIds(page), ids);
                assert.equal(await page.locator('.option-btn:disabled').count(), 4);
            }
            if (index < bank.questions.length - 1) await page.locator('#next-question').click();
        }
        assert.equal(seen.size, 59);
        assert.match(await page.locator('#answered-count').innerText(), /59 \/ 59/);
        await page.locator('.it-question-navigation summary').click();
        assert.equal(await page.locator('#question-palette button').count(), 59);
        await page.locator('#question-palette button').first().click();
        assert.equal(await page.locator('#progress').innerText(), '問題 1 / 59');
        // Compare by the displayed question, without relying on ID numbering.
        const firstStem = await page.locator('#question-text').innerText();
        const firstSource = bank.questions.find(q => q.question === firstStem);
        assert.deepEqual(await optionIds(page), seen.get(firstSource.question_id));
        await page.locator('#question-palette button').last().click();
        await finish(page);
        assert.match(await page.locator('#final-score').innerText(), /59 \/ 59.*未回答 0/);
        assert.equal(await page.locator('#review-list .review-item').count(), 59);
        await page.locator('#review-item-0 .comp-btn').last().click();
        await page.locator('#review-item-0 .review-flag-cb').check();
        await generate(page);
        const data = await snapshot(page);
        assert.equal(data.schema_version, '1.1.0');
        assert.equal(data.summary.correctCount, 59);
        assert.deepEqual(data.summary.questionTypeCounts, { standard: 59 });
        assert.equal(data.records[0].understandingLevel, 0);
        assert.equal(data.records[0].reviewFlag, true);
        for (const r of data.records) {
            const q = bank.questions.find(q => q.question_id === r.questionId);
            assert.equal(r.questionType, 'standard'); assert.equal(r.questionMode, 'standard');
            assert.equal(r.bankSchemaVersion, '0.2.0');
            assert.equal(r.questionText, q.question); assert.equal(r.selectedInstruction, null);
            assert.equal(r.selectedPool, 'correct'); assert.equal(r.selectedOptionId, r.correctOptionId);
            assert.deepEqual(r.displayedOptions.map(o => o.optionId), seen.get(r.questionId));
        }
        const questionRows = csv(await download(page, 'questions'));
        assert.equal(questionRows.length, 59);
        assert.deepEqual(JSON.parse(questionRows[0].displayedOptions), data.records[0].displayedOptions);
        assert.equal(questionRows[0].questionType, 'standard');
        assert.equal(csv(await download(page, 'options')).length, 236);
        const sessionRows = csv(await download(page, 'session'));
        assert.equal(sessionRows[0].TotalQuestions, '59');
        assert.equal(sessionRows[0].CorrectCount, '59');
        const analysis = JSON.parse((await page.locator('#report-text').inputValue()).split('=== AI_ANALYSIS_DATA_JSON ===\n')[1]);
        assert.deepEqual(analysis.itSnapshot, data);
        await noOverflow(page, [320, 390, 768]);
        await page.screenshot({ path: path.join(output, 'result-mobile.png') });
        await page.setViewportSize({ width: 1366, height: 1000 });
        await page.screenshot({ path: path.join(output, 'result-desktop.png') });
        await page.locator('#review-item-0 .review-flag-cb').uncheck();
        assert.equal(await page.locator('#output-section').isVisible(), false);
        await generate(page);
        assert.equal((await snapshot(page)).records[0].reviewFlag, false);
        console.log('PASS real 59-question drill: all answered with confidence, exact stems/options, revisits/palette, 59/59 scoring, JSON/CSV/AI parity, 320/390/768px layouts');

        await ready(page); await page.selectOption('#topic-select', 'TMP-Q007');
        await page.locator('#use-confidence-checkbox').uncheck(); await page.locator('#start-exam').click();
        const negative = bank.questions.find(q => q.question_id === 'TMP-Q007');
        const ids = await optionIds(page);
        const wrong = ids.findIndex(id => negative.pools.incorrect.some(o => o.option_id === id));
        await page.locator('.option-btn').nth(wrong).click();
        assert.equal(await page.locator('#feedback-title').innerText(), '不正解です');
        await finish(page); await generate(page);
        const failed = (await snapshot(page)).records[0];
        assert.equal(failed.isAnswered, true); assert.equal(failed.isCorrect, false);
        assert.equal(failed.selectedPool, 'incorrect'); assert.equal(failed.confidenceLevel, null);
        await ready(page); await page.selectOption('#topic-select', 'TMP-Q001');
        await page.locator('#start-exam').click(); await page.locator('.option-btn').first().click();
        await finish(page); await generate(page);
        const pending = (await snapshot(page)).records[0];
        assert.equal(pending.isAnswered, false); assert.equal(pending.answerConfirmed, false);
        assert.equal(pending.selectedOptionId, null); assert.equal(pending.answeredAt, null);
        console.log('PASS negative standard grading, confidence-off, and unconfirmed selections exported as unanswered');

        let fixture = structuredClone(examples), status = 200;
        await page.route('**/fixture-v02/config.json', r => r.fulfill({ json: { version: 1, title: '混合テスト教材', examId: examples.exam_id, bankFiles: ['bank.json'] } }));
        await page.route('**/fixture-v02/bank.json', r => r.fulfill(status === 200 ? { json: fixture } : { status, body: 'missing fixture' }));
        const fixtureURL = `${url}?conf=fixture-v02/config.json`;
        await ready(page, fixtureURL);
        assert.equal(await page.locator('#mode-select').isEnabled(), true);
        await page.selectOption('#chapter-select', '4');
        assert.equal(await page.locator('#mode-select').isDisabled(), true);
        await page.selectOption('#chapter-select', 'all');
        assert.equal(await page.locator('#mode-select').isEnabled(), true);
        await page.selectOption('#mode-select', 'inappropriate');
        await page.locator('#use-confidence-checkbox').uncheck(); await page.locator('#start-exam').click();
        const displays = [];
        for (let i = 0; i < 2; i++) {
            const stem = await page.locator('#question-text').innerText();
            const q = examples.questions.find(q => q.question_type === 'standard' ? q.question === stem : q.instructions.inappropriate.some(suffix => q.question + suffix === stem));
            assert.ok(q); displays.push({ stem, q, ids: await optionIds(page) });
            const pool = q.pools[q.question_type === 'standard' ? 'correct' : 'inappropriate'];
            const target = displays[i].ids.findIndex(id => pool.some(o => o.option_id === id));
            await page.locator('.option-btn').nth(target).click();
            assert.equal(await page.locator('#feedback-title').innerText(), '正解です');
            if (i === 0) await page.locator('#next-question').click();
        }
        await page.locator('#previous-question').click();
        assert.equal(await page.locator('#question-text').innerText(), displays[0].stem);
        assert.deepEqual(await optionIds(page), displays[0].ids);
        await finish(page); await generate(page);
        const mixed = await snapshot(page);
        assert.equal(mixed.summary.correctCount, 2);
        for (const r of mixed.records) {
            const q = examples.questions.find(q => q.question_id === r.questionId);
            if (q.question_type === 'polarity') {
                assert.equal(r.questionMode, 'inappropriate');
                assert.equal(r.selectedInstruction, q.instructions.inappropriate[r.instructionPosition - 1]);
                assert.equal(r.questionText, r.questionPrefix + r.selectedInstruction);
            } else { assert.equal(r.questionText, q.question); assert.equal(r.selectedInstruction, null); }
        }
        console.log('PASS mixed v0.2 types, direct suffix construction, standard-only filter controls and immutable revisits');

        const failures = [
            b => { b.questions[1].pools.correct = []; },
            b => { b.questions[1].instructions = {}; },
            b => { b.questions[0].instructions.inappropriate = []; },
            b => { b.questions[0].question_type = 'unknown'; },
            b => { b.questions[1].question_id = b.questions[0].question_id; },
        ];
        for (const mutate of failures) {
            fixture = structuredClone(examples); mutate(fixture);
            await page.goto(fixtureURL); await page.locator('#description-display[role="alert"]').waitFor();
            assert.equal(await page.locator('#start-exam').isDisabled(), true);
        }
        status = 404;
        await page.goto(fixtureURL); await page.locator('#description-display[role="alert"]').waitFor();
        assert.match(await page.locator('#description-display').innerText(), /HTTP 404/);
        console.log('PASS typed validation failures and missing banks block start');

        // Test-only 60th theme: never saved to the real question bank.
        const extended = structuredClone(bank), extra = structuredClone(bank.questions[0]);
        extra.question_id = 'TEST_Q060';
        extra.topic = '60問構成の検証用テーマ';
        extra.question = '60問構成の検証用問題です。候補を一つ選んでください。';
        for (const [pool, options] of Object.entries(extra.pools)) options.forEach((o, i) => { o.option_id = `TEST_Q060_${pool}_${i}`; });
        extended.questions.push(extra);
        await page.route('**/data/GenAI_pp_1-2-4.json', r => r.fulfill({ json: extended }));
        await ready(page);
        assert.match(await page.locator('#bank-info').innerText(), /収録 60問/);
        assert.equal((await page.locator('#bank-info').innerText()).includes('あと'), false);
        await page.selectOption('#question-count-select', '60');
        await page.locator('#start-exam').click();
        assert.equal(await page.locator('#progress').innerText(), '問題 1 / 60');
        await finish(page); await generate(page);
        const sixty = await snapshot(page);
        assert.equal(sixty.records.length, 60);
        assert.equal(new Set(sixty.records.map(r => r.questionId)).size, 60);
        assert.equal(sixty.summary.unansweredQuestions, 60);
        assert.deepEqual(errors, []); assert.deepEqual(bad, []);
        console.log('PASS 60 unique themes when supplied, no actual bank mutation, no missing assets or uncaught errors');
    } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
