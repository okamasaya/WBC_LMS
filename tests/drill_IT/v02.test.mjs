import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { createExercise, validateBanks } from '../../prototype/assets/js/drill_IT/bank.mjs';
import { DrillSession } from '../../prototype/assets/js/drill_IT/session.mjs';
import { buildResults, exportFile, buildReport, RESULT_VERSION } from '../../prototype/assets/js/drill_IT/results.mjs';

const read = name => JSON.parse(fs.readFileSync(new URL(`../../prototype/it/GenAI_Passport/${name}`, import.meta.url)));
const real = read('data/GenAI_pp_1-2-4.json');
const examples = read('examples/question-bank.v0.2.0.json');
const legacy = read('data/sample_questions.json');
const entries = bank => [{ bank: structuredClone(bank), url: 'https://local.test/bank.json' }];
const context = vm.createContext({ window: {} });
for (const file of ['resultData.js', 'resultReport.js']) vm.runInContext(fs.readFileSync(new URL(`../../prototype/assets/js/shared/${file}`, import.meta.url), 'utf8'), context);
const { ResultData, ResultReport } = context.window;
function rng(seed = 1) { return () => ((seed = (Math.imul(1664525, seed) + 1013904223) >>> 0) / 2 ** 32); }

test('real 59-question bank loads in every mode without reversing standard questions', () => {
    const source = entries(real), before = JSON.stringify(source);
    for (const mode of ['appropriate', 'inappropriate', 'mixed', 'standard']) {
        const exercise = createExercise(source, { mode, random: rng(20) });
        assert.equal(exercise.questions.length, 59);
        assert.equal(exercise.requestedMode, 'standard');
        assert.equal(new Set(exercise.questions.map(q => q.id)).size, 59);
        for (const q of exercise.questions) {
            const original = real.questions.find(s => s.question_id === q.id);
            assert.equal(q.question, original.question);
            assert.equal(q.questionType, 'standard');
            assert.equal(q.questionMode, 'standard');
            assert.equal(q.selectedInstruction, null);
            assert.equal(q.instructionPosition, null);
            assert.equal(new Set(q.options.map(o => o.optionId)).size, 4);
            assert.equal(q.options.filter(o => o.pool === 'correct').length, 1);
            assert.equal(q.options.filter(o => o.isCorrect).length, 1);
            assert.equal(q.options.find(o => o.isCorrect).pool, 'correct');
            assert.ok(original.pools.correct.some(o => o.option_id === q.options.find(o => o.isCorrect).optionId));
        }
    }
    assert.equal(JSON.stringify(source), before);
});

test('60 unique questions are supported when supplied; 59 are never duplicated to make 60', () => {
    assert.throws(() => createExercise(entries(real), { count: 60 }), /対象は59/);
    const extended = structuredClone(real), extra = structuredClone(real.questions[0]);
    extra.question_id = 'TEST_Q060';
    extra.topic = '60問構成の検証用テーマ';
    extra.question = '60問構成の検証用問題です。候補を一つ選んでください。';
    for (const [pool, options] of Object.entries(extra.pools)) options.forEach((o, i) => { o.option_id = `TEST_Q060_${pool}_${i}`; });
    extended.questions.push(extra);
    const exercise = createExercise(entries(extended), { count: 60 });
    assert.equal(exercise.questions.length, 60);
    assert.equal(new Set(exercise.questions.map(q => q.id)).size, 60);
});

test('real chapter/topic/count filters retain the supplied scope', () => {
    for (const [chapter, count] of [[1, 19], [2, 20], [4, 20]]) {
        const exercise = createExercise(entries(real), { chapter });
        assert.equal(exercise.questions.length, count);
        assert.ok(exercise.questions.every(q => q.chapter === chapter));
    }
    assert.equal(createExercise(entries(real), { count: 50 }).questions.length, 50);
    assert.equal(createExercise(entries(real), { questionId: 'TMP-Q007' }).questions[0].question, real.questions[6].question);
});

test('v0.2 polarity appends one allowed instruction exactly once; standard stays unchanged', () => {
    const seen = new Set(), random = rng(3245);
    for (const mode of ['appropriate', 'inappropriate', 'mixed']) {
        for (let trial = 0; trial < 30; trial++) {
            const exercise = createExercise(entries(examples), { mode, random });
            const polarity = exercise.questions.find(q => q.questionType === 'polarity');
            const standard = exercise.questions.find(q => q.questionType === 'standard');
            const source = examples.questions[0];
            const instructions = source.instructions[polarity.questionMode];
            assert.equal(polarity.selectedInstruction, instructions[polarity.instructionPosition - 1]);
            assert.equal(polarity.question, source.question + polarity.selectedInstruction);
            assert.equal(polarity.questionPrefix, source.question);
            assert.equal(polarity.options.filter(o => o.pool === polarity.questionMode).length, 1);
            assert.equal(polarity.options.filter(o => o.isCorrect).length, 1);
            assert.equal(standard.question, examples.questions[1].question);
            assert.equal(standard.questionMode, 'standard');
            seen.add(`${polarity.questionMode}:${polarity.instructionPosition}`);
        }
    }
    assert.equal(seen.size, 4);
    assert.throws(() => createExercise(entries(examples), { mode: 'standard' }), /切り替え型/);
    assert.equal(createExercise(entries(examples), { mode: 'standard', questionId: examples.questions[1].question_id }).requestedMode, 'standard');
});

test('v0.1 and v0.2 can coexist, and duplicate IDs still fail across versions', () => {
    const combined = [entries(legacy)[0], { bank: structuredClone(real), url: 'https://local.test/new.json' }];
    assert.equal(createExercise(combined, { mode: 'mixed' }).questions.length, 65);
    const collision = structuredClone(combined);
    collision[1].bank.questions[0].question_id = collision[0].bank.questions[0].question_id;
    assert.throws(() => validateBanks(collision), /重複/);
});

test('v0.2 typed structure, instructions and minimum pools are validated before filtering', () => {
    const mutations = [
        b => { b.questions[1].pools.correct = []; },
        b => b.questions[1].pools.incorrect.pop(),
        b => { b.questions[1].instructions = {}; },
        b => { b.questions[1].stems = {}; },
        b => { b.questions[1].correct_answer = 1; },
        b => { b.questions[1].question_type = 'unknown'; },
        b => { b.questions[1].question = '　'; },
        b => { delete b.questions[0].instructions; },
        b => { b.questions[0].instructions.appropriate = []; },
        b => { b.questions[0].instructions.inappropriate = '文字列'; },
        b => { b.questions[0].instructions.inappropriate = ['　']; },
        b => { b.questions[0].instructions.appropriate.push('　' + b.questions[0].instructions.appropriate[0] + ' '); },
        b => { b.questions[0].pools.appropriate.pop(); },
        b => { b.questions[1].pools.correct[0].isCorrect = true; },
    ];
    for (const mutate of mutations) {
        const source = structuredClone(examples); mutate(source);
        assert.throws(() => createExercise(entries(source), { chapter: 4 }), /bank.json/);
    }
});

test('single instruction and unequal standard pools are accepted; source and frozen display remain stable', () => {
    const bank = structuredClone(examples);
    bank.questions[0].instructions.appropriate = ['適切な説明を一つ選んでください。'];
    const source = entries(bank), before = JSON.stringify(source);
    const exercise = createExercise(source, { random: rng(22) });
    const session = new DrillSession(exercise);
    const display = JSON.stringify(exercise);
    session.select(0); session.move(1); session.move(0); session.confirm(1); session.finish();
    assert.equal(JSON.stringify(exercise), display);
    assert.equal(JSON.stringify(source), before);
    assert.throws(() => { exercise.questions[0].question = '変更'; }, TypeError);
});

test('negative standard stems use correct-pool membership, not whether content sounds appropriate', () => {
    const exercise = createExercise(entries(real), { questionId: 'TMP-Q007', mode: 'inappropriate' });
    const session = new DrillSession(exercise, { useConfidence: false });
    session.select(exercise.questions[0].options.findIndex(o => o.pool === 'correct'));
    session.finish();
    const result = buildResults(session, '本教材', { ResultData, sessionId: 'IT_NEGATIVE' });
    assert.equal(result.summary.correctCount, 1);
    assert.equal(result.records[0].selectedPool, 'correct');
    assert.match(result.records[0].userAnswerText, /回帰/);
    assert.equal(result.records[0].questionText, real.questions[6].question);
});

test('v1.1 snapshots/CSV/report retain types, final stem and chosen instruction', () => {
    const exercise = createExercise(entries(examples), { mode: 'inappropriate', random: rng(3) });
    const session = new DrillSession(exercise, { useConfidence: false });
    session.select(0); session.finish();
    const data = buildResults(session, '混合教材', { ResultData, sessionId: 'IT_V02' });
    assert.equal(data.summary.dataSchemaVersion, RESULT_VERSION);
    assert.deepEqual(data.summary.questionTypeCounts, { standard: 1, polarity: 1 });
    for (const record of data.records) {
        const q = exercise.questions.find(q => q.id === record.questionId);
        assert.equal(record.questionText, q.question);
        assert.equal(record.selectedInstruction, q.selectedInstruction);
        assert.equal(record.instructionPosition, q.instructionPosition);
        assert.equal(record.questionPrefix, q.questionPrefix);
        assert.equal(record.questionType, q.questionType);
        assert.equal(record.bankSchemaVersion, '0.2.0');
    }
    const json = JSON.parse(exportFile(data, 'json', ResultReport).content);
    assert.equal(json.schema_version, '1.1.0');
    assert.deepEqual(json.records.map(r => r.selectedInstruction), data.records.map(r => r.selectedInstruction));
    const csv = exportFile(data, 'questions', ResultReport).content;
    assert.match(csv, /"questionType","questionMode","questionPrefix","selectedInstruction","instructionPosition"/);
    const ai = JSON.parse(buildReport(data, ResultReport).split('=== AI_ANALYSIS_DATA_JSON ===\n')[1]);
    assert.deepEqual(ai.itSnapshot, json);
    assert.equal(ai.questions[0].questionType, data.records[0].questionType);
});
