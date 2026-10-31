import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { validateConfig, selectQuestions, scoreQuestions } from '../examCore.js';

const base = new URL('../../../../language/JLPT_N2/', import.meta.url);
const sourceConfig = JSON.parse(fs.readFileSync(new URL('conf_JLPT_N2_LK.json', base)));
const configContext = vm.createContext({window:{},structuredClone});
vm.runInContext(fs.readFileSync(new URL('../../shared/examConfig.js', import.meta.url), 'utf8'), configContext);
const config = configContext.window.ExamConfig.normalize(sourceConfig, 'actual');
const context = vm.createContext({ console });
vm.runInContext(fs.readFileSync(new URL('questionLoader.js', base), 'utf8'), context);
const bank = config.questionFiles.flatMap(path => JSON.parse(fs.readFileSync(new URL(path, base)))).map(context.convertQuestionFormat);

test('real bank: exact category quotas, unique IDs, no mutation', () => {
    const before = JSON.stringify(bank);
    const selected = selectQuestions(config, bank);
    assert.equal(selected.length, 30);
    assert.equal(new Set(selected.map(q => q.id)).size, 30);
    for (const c of config.categories) assert.equal(selected.filter(q => q.category_lv2 === c.categoryLv2 && q.category_lv3 === c.categoryLv3).length, c.count);
    assert.equal(JSON.stringify(bank), before);
});
test('validation blocks invalid configuration and insufficient banks', () => {
    for (const update of [{ timeLimitMinutes: 0 }, { timeLimitMinutes: '40' }, { recordConfidence: 'true' }, { questionFiles: [] }, { categories: [{ ...config.categories[0], count: -1 }] }, { categories: [config.categories[0], config.categories[0]] }]) {
        assert.throws(() => validateConfig({ ...config, ...update }));
    }
    assert.throws(() => selectQuestions(config, []), /しかありません/);
    assert.throws(() => selectQuestions(config, [...bank, bank[0]]), /重複/);
});
test('unanswered / wrong answers score zero and option shuffling preserves correct answer', () => {
    const selected = selectQuestions({ ...config, shuffleOptions: true }, bank, () => 0.2);
    assert.ok(selected.every(q => q.options.filter(o => o.isCorrect).length === 1));
    const answers = selected.map(q => ({ selected: q.options.findIndex(o => o.isCorrect) }));
    assert.equal(scoreQuestions(selected, answers).filter(r => r.correct).length, 30);
    answers[0].selected = null;
    answers[1].selected = selected[1].options.findIndex(o => !o.isCorrect);
    assert.equal(scoreQuestions(selected, answers).filter(r => r.correct).length, 28);
});
