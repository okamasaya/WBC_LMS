import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const context = vm.createContext({ window: {} });
for (const file of ['resultData.js', 'resultReport.js']) vm.runInContext(fs.readFileSync(new URL(`../../prototype/assets/js/shared/${file}`, import.meta.url), 'utf8'), context);
const { ResultData, ResultReport } = context.window;
const start = Date.parse('2026-10-31T09:00:00Z');
const questions = [0, 1, 2].map(i => ({
    id: `Q${i}`, category_lv1: '言語知識', category_lv2: '文字', category_lv3: '漢字読み',
    category: '【言語知識】文字・漢字読み', question: `問${i} "確認",\n次の行`, difficulty: 3,
    options: [{ text: '正しい', isCorrect: true, rationale: '正解の解説' }, { text: '違う', isCorrect: false }]
}));
function build(mode = 'Actual', useConfidence = true) {
    return ResultData.build({ questions,
        answers: [
            { selected: 0, confidence: 2, elapsedTimeMs: 2000, answeredAt: new Date(start + 2000).toISOString(), flagged: true },
            { selected: 1, confidence: 4, elapsedTimeMs: 3000, answeredAt: new Date(start + 5000).toISOString() },
            { selected: null, confidence: null, elapsedTimeMs: 1000 }
        ], metadata: { examId: 'JLPT_N2_LK', examType: 'JLPT', examLevel: 'N2', examTitle: 'JLPT N2', mode, useConfidence, sourceQuestionFiles: './questions.json' },
        startedAt: start, endedAt: start + 6000,
        resolveSkill: () => ({ skillId: 'SK_TEST', skillName: '漢字読み' })
    });
}
test('Actual and Drill share scores and typed raw schema; unanswered timestamps stay empty', () => {
    for (const mode of ['Actual', 'Drill']) {
        const { summary, records } = build(mode);
        assert.equal(summary.totalQuestions, 3);
        assert.equal(summary.answeredQuestions, 2);
        assert.equal(summary.correctCount, 1);
        assert.equal(summary.incorrectCount, 1);
        assert.equal(summary.unansweredQuestions, 1);
        assert.equal(summary.wrongCount, 2);
        assert.equal(summary.totalTimeSec, 6);
        assert.equal(summary.studentId, null);
        assert.equal(records[0].mode, mode);
        assert.equal(records[0].confidenceLevel, 2);
        assert.equal(records[0].skillId, 'SK_TEST');
        assert.equal(records[0].duringExamReviewFlag, true);
        assert.equal(records[0].reviewFlag, false);
        assert.equal(records[0].answerTimeSec, 2);
        assert.equal(records[1].elapsedTimeSec, 5);
        assert.equal(records[2].answeredAt, null);
        assert.equal(records[2].elapsedTimeSec, null);
        assert.equal(records[2].userAnswerText, null);
        assert.equal(records[2].userAnswerDisplayedPosition, null);
    }
});
test('AI payload includes Actual confidence, zero understanding and review edits; skipped confidence is not fabricated', () => {
    const data = build();
    data.records[0].understandingLevel = 0;
    data.records[0].understandingLabel = '全然分からない';
    data.records[0].reviewFlag = true;
    const text = ResultReport.buildReport(data);
    assert.match(text, /自信度: 2 \(少し自信がある\)/);
    assert.match(text, /0 \(全然分からない\)/);
    assert.match(text, /要復習フラグ: TRUE/);
    assert.match(text, /\[問3\] 未回答/);
    const json = JSON.parse(text.split('=== AI_ANALYSIS_DATA_JSON ===\n')[1]);
    assert.equal(json.session.mode, 'Actual');
    assert.equal(json.questions[0].review, true);
    assert.equal(json.questions[0].explanationUnderstanding, '0 (全然分からない)');
    const disabled = build('Actual', false);
    assert.equal(disabled.records[0].confidenceLevel, null);
    assert.match(ResultReport.buildReport(disabled), /自信度: 記録なし/);
});
test('CSV schemas, raw sections and escaping are identical for both modes', () => {
    const actual = build(), drill = build('Drill');
    for (const type of ['session', 'questions', 'raw']) {
        const a = ResultReport.exportCsv(actual, type), d = ResultReport.exportCsv(drill, type);
        assert.equal(a.content.split('\r\n')[0], d.content.split('\r\n')[0]);
        assert.ok(a.name.endsWith('.csv'));
        assert.ok(a.content.endsWith('\r\n'));
    }
    assert.match(ResultReport.exportCsv(actual, 'raw').content, /=== Session ===\r\n/);
    assert.match(ResultReport.exportCsv(actual, 'raw').content, /=== QuestionResult ===\r\n/);
    const csv = ResultReport.exportCsv(actual, 'questions').content;
    assert.match(csv, /"問0 ""確認"",\n次の行"/);
    assert.match(csv, /"DuringExamReviewFlag"/);
    assert.throws(() => ResultReport.exportCsv(actual, 'invalid'));
});
