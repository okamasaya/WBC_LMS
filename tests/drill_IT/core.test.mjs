import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { createExercise, validateBanks, loadBanks, parseConfig } from '../../prototype/assets/js/drill_IT/bank.mjs';
import { DrillSession } from '../../prototype/assets/js/drill_IT/session.mjs';
import { buildResults, exportFile, buildReport, RESULT_VERSION } from '../../prototype/assets/js/drill_IT/results.mjs';

const bank = JSON.parse(fs.readFileSync(new URL('../../prototype/it/GenAI_Passport/data/sample_questions.json', import.meta.url)));
const entry = () => [{ bank: structuredClone(bank), url: 'https://local.test/data/sample.json' }];
const context = vm.createContext({ window: {} });
for (const file of ['resultData.js', 'resultReport.js']) vm.runInContext(fs.readFileSync(new URL(`../../prototype/assets/js/shared/${file}`, import.meta.url), 'utf8'), context);
const { ResultData, ResultReport } = context.window;
function rng(seed = 1) { return () => ((seed = (Math.imul(1664525, seed) + 1013904223) >>> 0) / 2 ** 32); }
function fixture(mode = 'appropriate', useConfidence = true) {
    let now = Date.parse('2026-11-10T01:00:00Z');
    const exercise = createExercise(entry(), { mode, random: rng() });
    const session = new DrillSession(exercise, { useConfidence, clock: () => now });
    return { session, advance(ms) { now += ms; } };
}

test('both polarities select four distinct options, with one target; source banks are unchanged', () => {
    const entries = entry(), before = JSON.stringify(entries);
    for (const mode of ['appropriate', 'inappropriate']) {
        for (let seed = 1; seed <= 100; seed++) {
            const e = createExercise(entries, { mode, random: rng(seed) });
            assert.equal(e.questions.length, 6);
            assert.equal(new Set(e.questions.map(q => q.id)).size, 6);
            for (const q of e.questions) {
                assert.equal(q.options.length, 4);
                assert.equal(new Set(q.options.map(o => o.optionId)).size, 4);
                assert.equal(q.options.filter(o => o.pool === mode).length, 1);
                assert.equal(q.options.filter(o => o.isCorrect).length, 1);
                assert.equal(q.options.find(o => o.isCorrect).pool, mode);
                assert.equal(q.question, bank.questions.find(source => source.question_id === q.id).stems[mode]);
            }
        }
    }
    assert.equal(JSON.stringify(entries), before);
});
test('pool membership determines correctness even when IDs suggest the opposite', () => {
    const entries = entry();
    for (const q of entries[0].bank.questions) for (const pool of Object.values(q.pools)) for (const o of pool) o.option_id = o.option_id.replace('-A', '-TEMP').replace('-I', '-A').replace('-TEMP', '-I');
    const e = createExercise(entries, { mode: 'inappropriate', random: rng() });
    assert.ok(e.questions.every(q => q.options.find(o => o.isCorrect).optionId.includes('-A')));
});
test('larger unequal pools sample without replacement and do not force equal counts', () => {
    const entries = entry(), pool = entries[0].bank.questions[0].pools.appropriate;
    pool.push({ option_id: 'TEST_EXTRA', text: '構造検証用の追加候補', explanation: '教材ではない検証用' });
    const selections = new Set();
    const random = rng(54321);
    for (let trial = 0; trial < 100; trial++) {
        const q = createExercise(entries, { mode: 'inappropriate', questionId: bank.questions[0].question_id, random }).questions[0];
        assert.equal(new Set(q.options.map(o => o.optionId)).size, 4);
        selections.add(q.options.filter(o => o.pool === 'appropriate').map(o => o.optionId).sort().join(','));
    }
    assert.equal(selections.size, 4);
});
test('mixed mode assigns and freezes each theme once; chapter/topic/count filters are applied', () => {
    const e = createExercise(entry(), { mode: 'mixed', random: rng(42) });
    assert.deepEqual(new Set(e.questions.map(q => q.questionMode)), new Set(['appropriate', 'inappropriate']));
    assert.throws(() => { e.questions[0].options.reverse(); }, TypeError);
    const filtered = createExercise(entry(), { chapter: 2, count: 1, random: rng() });
    assert.equal(filtered.questions.length, 1);
    assert.equal(filtered.questions[0].chapter, 2);
    assert.equal(createExercise(entry(), { questionId: 'GAIP-CH04-Q010' }).questions[0].topic, 'APIキーの管理');
    assert.throws(() => createExercise(entry(), { chapter: 3 }), /条件に合う/);
    assert.throws(() => createExercise(entry(), { count: 100 }), /対象は6/);
    assert.throws(() => createExercise(entry(), { count: 0 }), /問題数/);
    assert.throws(() => createExercise(entry(), { mode: 'bad' }), /方式/);
});
test('invalid banks stop the whole exercise even when the invalid theme is filtered out', () => {
    const mutations = [
        b => b.questions[0].pools.appropriate.pop(),
        b => delete b.questions[0].stems.inappropriate,
        b => { b.questions[0].pools.appropriate[0].explanation = '　\n'; },
        b => { b.questions[0].pools.appropriate[0].isCorrect = true; },
        b => { b.questions[0].correct_answer = 1; },
        b => { b.questions[0].chapter = 0; },
        b => { b.questions[0].chapter = 1.5; },
        b => { b.schema_version = 0.1; },
        b => { b.questions[0].pools.appropriate[0].option_id = 'bad id'; },
        b => { b.questions[0].pools.appropriate[0].text = ''; },
        b => { b.questions[0].question_id = b.questions[1].question_id; },
        b => { b.questions[0].pools.appropriate[0].option_id = b.questions[1].pools.appropriate[0].option_id; },
        b => { b.questions[0].pools.inappropriate[0].text = ' ' + b.questions[0].pools.appropriate[0].text + '　'; },
        b => { b.questions[0].pools.appropriate[0].text = 'ＡＢＣ'; b.questions[0].pools.inappropriate[0].text = 'ABC'; },
    ];
    for (const mutate of mutations) {
        const entries = entry(); mutate(entries[0].bank);
        assert.throws(() => createExercise(entries, { chapter: 4 }), /sample.json/);
    }
});
test('IDs are unique across banks and sources cannot be listed twice', () => {
    assert.throws(() => validateBanks([...entry(), ...entry()]), /同じファイル/);
    assert.throws(() => validateBanks([...entry(), { ...entry()[0], url: 'https://local.test/other.json' }]), /重複/);
    const other = entry()[0]; other.url += 'other'; other.bank.exam_id = 'OTHER';
    assert.throws(() => validateBanks([...entry(), other]), /exam_id/);
});
test('loader resolves bank paths from config URL; failures and foreign origins fail closed', async () => {
    const config = { version: 1, title: '別教材', examId: bank.exam_id, bankFiles: ['../data/q.json'] };
    const urls = [];
    const fetcher = async url => { urls.push(url); return { ok: true, json: async () => urls.length === 1 ? config : bank }; };
    const result = await loadBanks('./config/test.json', 'https://local.test/entry/index.html', fetcher);
    assert.deepEqual(urls, ['https://local.test/entry/config/test.json', 'https://local.test/entry/data/q.json']);
    assert.equal(result.config.title, '別教材');
    await assert.rejects(loadBanks('./missing.json', 'https://local.test/', async () => ({ ok: false, status: 404 })), /HTTP 404/);
    await assert.rejects(loadBanks('./bad.json', 'https://local.test/', async () => ({ ok: true, json() { throw new Error(); } })), /JSONを解析/);
    await assert.rejects(loadBanks('https://other.test/config.json', 'https://local.test/'), /同じHTTP/);
    assert.throws(() => parseConfig({ ...config, unknown: true }), /未対応/);
    await assert.rejects(loadBanks('./config.json', 'https://local.test/', async url => ({ ok: true, json: async () => url.endsWith('config.json') ? { ...config, examId: 'OTHER' } : bank })), /exam_id/);
});
test('confidence gates confirmation, pending selections can change, confirmed answers are locked', () => {
    const { session, advance } = fixture();
    assert.equal(session.confirm(1), false);
    advance(1200); session.select(0);
    advance(500); session.select(1);
    assert.equal(session.currentAnswer.confirmed, false);
    assert.equal(session.currentAnswer.answeredAt, null);
    assert.throws(() => session.confirm(0), /自信度/);
    advance(300); session.confirm(2);
    assert.equal(session.currentAnswer.elapsedTimeMs, 2000);
    assert.equal(session.currentAnswer.confidence, 2);
    assert.equal(session.select(2), false);
    assert.equal(session.currentAnswer.selected, 1);
    assert.equal(session.confirm(3), false);
});
test('navigation preserves choices/order; response time excludes confirmed review and accumulates revisits', () => {
    const { session, advance } = fixture();
    const before = JSON.stringify(session.exercise);
    advance(1000); session.select(0);
    advance(500); session.move(1);
    advance(2000); session.move(0);
    assert.equal(session.currentAnswer.selected, 0);
    advance(500); session.confirm(1);
    advance(9000); session.move(1);
    advance(1000); session.finish();
    assert.equal(session.answers[0].elapsedTimeMs, 2000);
    assert.equal(session.answers[1].elapsedTimeMs, 3000);
    assert.equal(JSON.stringify(session.exercise), before);
    const endedAt = session.endedAt; advance(100); session.finish();
    assert.equal(session.endedAt, endedAt);
    assert.equal(session.select(1), false);
});
test('confidence-off confirms immediately and records no confidence', () => {
    const { session, advance } = fixture('inappropriate', false);
    advance(500); session.select(0); advance(8000); session.finish();
    assert.equal(session.answers[0].confirmed, true);
    assert.equal(session.answers[0].elapsedTimeMs, 500);
    assert.equal(session.answers[0].confidence, null);
});
test('IT result snapshots preserve stem, ordered pools/IDs, confirmed selection and unanswered semantics', () => {
    for (const mode of ['appropriate', 'inappropriate']) {
        const { session, advance } = fixture(mode);
        const q = session.exercise.questions[0];
        session.select(q.options.findIndex(o => o.isCorrect)); advance(300); session.confirm(4);
        session.move(1); session.select(0); advance(400); session.finish();
        const data = buildResults(session, 'テスト', { ResultData, sessionId: 'IT_TEST' });
        assert.equal(data.summary.correctCount, 1);
        assert.equal(data.summary.answeredQuestions, 1);
        assert.equal(data.summary.unansweredQuestions, 5);
        assert.equal(data.summary.dataSchemaVersion, RESULT_VERSION);
        assert.equal(data.records[0].questionText, q.question);
        assert.equal(data.records[0].selectedOptionId, q.options.find(o => o.isCorrect).optionId);
        assert.deepEqual(data.records[0].displayedOptions.map(o => o.optionId), q.options.map(o => o.optionId));
        assert.equal(data.records[0].questionMode, mode);
        assert.equal(data.records[0].bankSchemaVersion, '0.1.0');
        assert.equal(data.records[0].confidenceLevel, 4);
        const pending = data.records[1];
        assert.equal(pending.isAnswered, false);
        assert.equal(pending.answerConfirmed, false);
        assert.equal(pending.selectedOptionId, null);
        assert.equal(pending.answeredAt, null);
        assert.equal(pending.userAnswerDisplayedPosition, null);
        assert.equal(pending.confidenceLevel, null);
        assert.equal(data.records[0].skillId, null);
        assert.equal(data.records[0].difficulty, null);
    }
});
test('JSON/CSV/report share snapshots, handle quotes/newlines, and retain zero understanding', () => {
    const entries = entry();
    entries[0].bank.questions[0].pools.appropriate[0].text = '改行\n"引用",カンマ';
    const session = new DrillSession(createExercise(entries, { questionId: bank.questions[0].question_id, random: () => 0.99 }), { useConfidence: false });
    session.select(session.exercise.questions[0].options.findIndex(o => o.isCorrect)); session.finish();
    const data = buildResults(session, 'テスト', { ResultData, sessionId: 'IT_QUOTES' });
    data.records[0].understandingLevel = 0; data.records[0].understandingLabel = '全然分からない'; data.records[0].reviewFlag = true;
    const saved = structuredClone(data);
    const snapshot = JSON.parse(exportFile(saved, 'json', ResultReport).content);
    assert.equal(snapshot.records[0].understandingLevel, 0);
    assert.equal(snapshot.records[0].reviewFlag, true);
    assert.equal(snapshot.records[0].displayedOptions.length, 4);
    for (const type of ['session', 'questions', 'options']) assert.match(exportFile(saved, type, ResultReport).content, /questionMode/);
    assert.match(exportFile(saved, 'questions', ResultReport).content, /displayedOptions/);
    assert.match(exportFile(saved, 'options', ResultReport).content, /改行\n""引用"",カンマ/);
    const report = buildReport(saved, ResultReport);
    const json = JSON.parse(report.split('=== AI_ANALYSIS_DATA_JSON ===\n')[1]);
    assert.deepEqual(json.itSnapshot, snapshot);
    assert.equal(json.questions[0].questionMode, 'appropriate');
    data.records[0].understandingLevel = 3;
    assert.equal(snapshot.records[0].understandingLevel, 0);
    assert.throws(() => exportFile(saved, 'invalid', ResultReport), /未対応/);
});
