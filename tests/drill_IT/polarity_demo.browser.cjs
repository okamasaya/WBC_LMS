const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const base = process.env.CBT_TEST_BASE_URL || 'http://127.0.0.1:8000';
const url = `${base}/prototype/it/GenAI_Passport/Drill_GenAI-pp_polarity_demo.html`;
const bank = JSON.parse(fs.readFileSync(path.join(__dirname, '../../prototype/it/GenAI_Passport/data/polarity_demo_questions.json')));
const output = process.env.POLARITY_DEMO_TEST_DIR || '/tmp/genai-polarity-demo';
fs.mkdirSync(output, { recursive: true });

const optionIds = page => page.locator('.option-btn').evaluateAll(nodes => nodes.map(n => n.dataset.optionId));
function identify(stem) {
    for (const question of bank.questions) {
        for (const mode of ['appropriate', 'inappropriate']) {
            if (question.instructions[mode].some(text => question.question + text === stem)) return { question, mode };
        }
    }
    assert.fail(`unknown question: ${stem}`);
}
async function ready(page) {
    await page.goto(url);
    await page.waitForFunction(() => !document.getElementById('start-exam').disabled);
}
async function noOverflow(page) {
    for (const width of [320, 390, 768]) {
        await page.setViewportSize({ width, height: 900 });
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `overflow at ${width}px`);
    }
    await page.setViewportSize({ width: 1366, height: 1000 });
}

(async () => {
    const browser = await chromium.launch({ executablePath: process.env.CBT_TEST_CHROMIUM || '/usr/bin/chromium', headless: true, args: ['--no-sandbox'] });
    const context = await browser.newContext({ acceptDownloads: true });
    // Reproducible test draws; the shipped page uses the normal random source.
    await context.addInitScript(() => {
        let seed = 37;
        Math.random = () => ((seed = (Math.imul(1664525, seed) + 1013904223) >>> 0) / 2 ** 32);
    });
    const page = await context.newPage();
    page.setDefaultTimeout(15000);
    const errors = [], bad = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('response', response => { if (response.status() >= 400) bad.push(`${response.status()} ${response.url()}`); });
    try {
        await ready(page);
        assert.match(await page.locator('#bank-info').innerText(), /収録 5問/);
        assert.equal(await page.locator('#mode-select').inputValue(), 'mixed');
        assert.equal(await page.locator('#mode-select').isDisabled(), false);
        assert.equal(await page.locator('#use-confidence-checkbox').isChecked(), false);
        await noOverflow(page);
        await page.screenshot({ path: path.join(output, 'start-desktop.png'), fullPage: true });
        await page.setViewportSize({ width: 390, height: 844 });
        await page.screenshot({ path: path.join(output, 'start-mobile.png'), fullPage: true });
        await page.setViewportSize({ width: 1366, height: 1000 });

        for (const mode of ['appropriate', 'inappropriate', 'mixed']) {
            await ready(page);
            await page.selectOption('#mode-select', mode);
            await page.locator('#start-exam').click();
            const seen = new Map(), modes = new Set();
            for (let index = 0; index < 5; index++) {
                assert.equal(await page.locator('#progress').innerText(), `問題 ${index + 1} / 5`);
                const stem = await page.locator('#question-text').innerText();
                const { question, mode: questionMode } = identify(stem);
                if (mode !== 'mixed') assert.equal(questionMode, mode);
                modes.add(questionMode);
                assert.equal(seen.has(question.question_id), false);
                const ids = await optionIds(page);
                assert.equal(new Set(ids).size, 4);
                const target = new Set(question.pools[questionMode].map(o => o.option_id));
                assert.equal(ids.filter(id => target.has(id)).length, 1);
                const other = questionMode === 'appropriate' ? 'inappropriate' : 'appropriate';
                const distractors = new Set(question.pools[other].map(o => o.option_id));
                assert.equal(ids.filter(id => distractors.has(id)).length, 3);
                const shouldBeCorrect = mode !== 'mixed' || index !== 0;
                const answer = ids.findIndex(id => target.has(id) === shouldBeCorrect);
                seen.set(question.question_id, { ids, stem, questionMode, selected: ids[answer], shouldBeCorrect });
                if (index === 0 && mode === 'inappropriate') {
                    await page.screenshot({ path: path.join(output, 'question-inappropriate.png'), fullPage: true });
                }
                await page.locator('.option-btn').nth(answer).click();
                assert.equal(await page.locator('#feedback-title').innerText(), shouldBeCorrect ? '正解です' : '不正解です');
                assert.equal(await page.locator('#instant-feedback li').count(), 4);
                const labels = await page.locator('#instant-feedback li strong').allTextContents();
                assert.equal(labels.filter(label => label.includes('この回に選ぶ正解')).length, 1);
                assert.equal(labels.filter(label => label.startsWith('内容は適切')).length, questionMode === 'appropriate' ? 1 : 3);
                if (index === 0) {
                    await noOverflow(page);
                    if (mode === 'inappropriate') {
                        await page.screenshot({ path: path.join(output, 'feedback-inappropriate.png'), fullPage: true });
                        await page.setViewportSize({ width: 390, height: 844 });
                        await page.screenshot({ path: path.join(output, 'feedback-mobile.png'), fullPage: true });
                        await page.setViewportSize({ width: 1366, height: 1000 });
                    }
                    await page.locator('#next-question').click();
                    await page.locator('#previous-question').click();
                    assert.equal(await page.locator('#question-text').innerText(), stem);
                    assert.deepEqual(await optionIds(page), ids);
                    assert.equal(await page.locator('.option-btn:disabled').count(), 4);
                }
                if (index < 4) await page.locator('#next-question').click();
            }
            assert.equal(seen.size, 5);
            if (mode === 'mixed') assert.equal(modes.size, 2, 'fixed test seed exercises both directions');
            page.once('dialog', dialog => dialog.accept());
            await page.locator('#finish-exam').click();
            await page.locator('#score-container').waitFor({ state: 'visible' });
            const expected = mode === 'mixed' ? 4 : 5;
            assert.match(await page.locator('#final-score').innerText(), new RegExp(`${expected} / 5 問正解`));
            await noOverflow(page);
            page.once('dialog', dialog => dialog.accept());
            await page.locator('#generate-report').click();
            await page.locator('#output-section').waitFor({ state: 'visible' });
            const waiting = page.waitForEvent('download');
            await page.locator('[data-download="json"]').click();
            const file = await waiting, target = path.join(output, `${mode}-snapshot.json`);
            await file.saveAs(target);
            const snapshot = JSON.parse(fs.readFileSync(target));
            assert.equal(snapshot.summary.correctCount, expected);
            assert.equal(snapshot.summary.questionMode, mode);
            assert.deepEqual(snapshot.summary.questionTypeCounts, { polarity: 5 });
            for (const record of snapshot.records) {
                const displayed = seen.get(record.questionId);
                const source = bank.questions.find(q => q.question_id === record.questionId);
                assert.equal(record.questionText, displayed.stem);
                assert.equal(record.questionMode, displayed.questionMode);
                assert.equal(record.questionPrefix, source.question);
                assert.equal(record.questionText, source.question + record.selectedInstruction);
                assert.equal(record.selectedInstruction, source.instructions[record.questionMode][record.instructionPosition - 1]);
                assert.equal(record.selectedOptionId, displayed.selected);
                assert.equal(record.isCorrect, displayed.shouldBeCorrect);
                assert.deepEqual(record.displayedOptions.map(o => o.optionId), displayed.ids);
                assert.equal(record.displayedOptions.filter(o => o.isCorrect).length, 1);
                assert.equal(record.displayedOptions.find(o => o.isCorrect).pool, record.questionMode);
                for (const option of record.displayedOptions) {
                    const original = source.pools[option.pool].find(o => o.option_id === option.optionId);
                    assert.equal(option.text, original.text);
                    assert.equal(option.explanation, original.explanation);
                }
            }
            const report = await page.locator('#report-text').inputValue();
            const analysis = JSON.parse(report.split('=== AI_ANALYSIS_DATA_JSON ===\n').at(-1));
            assert.deepEqual(analysis.itSnapshot, snapshot);
            console.log(`PASS demo ${mode}: ${expected}/5, stem/pools/order/scoring/revisit/snapshot/report`);
        }

        // Optional confidence still defers confirmation, even on the demo page.
        await ready(page);
        await page.selectOption('#topic-select', bank.questions[0].question_id);
        await page.locator('#use-confidence-checkbox').check();
        await page.locator('#start-exam').click();
        await page.locator('.option-btn').first().click();
        assert.equal(await page.locator('#instant-feedback').isVisible(), false);
        await page.locator('[data-confidence="1"]').click();
        assert.equal(await page.locator('#instant-feedback').isVisible(), true);
        page.once('dialog', dialog => dialog.accept());
        await page.locator('#finish-exam').click();
        assert.deepEqual(errors, []);
        assert.deepEqual(bad, []);
        console.log('PASS demo confidence, 320/390/768px, no page errors or failed requests');
    } finally {
        await browser.close();
    }
})().catch(error => { console.error(error); process.exitCode = 1; });
