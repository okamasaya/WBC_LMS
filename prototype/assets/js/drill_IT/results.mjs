/* Keep IT snapshots separate from the existing fixed-choice CSV contract. */
import { MODE_LABELS } from './bank.mjs';
export const RESULT_VERSION = 'it-polarity-result/1.1.0';
export const UNDERSTANDING_LABELS = ['全然分からない', 'まだ少し分からない', 'だいたい理解できた', '理解できた'];

export function buildResults(session, title, { ResultData, sessionId }) {
    if (session.active) throw new Error('終了していない演習は出力できません');
    const exercise = session.exercise;
    const data = ResultData.build({
        questions: exercise.questions,
        answers: session.answers.map(a => ({ ...a, selected: a.confirmed ? a.selected : null })),
        metadata: { examId: exercise.examId, examType: 'IT', examLevel: null, examTitle: title,
            mode: 'Drill', studentId: null, useConfidence: session.useConfidence,
            selectedCategoryLevel1: exercise.chapter === 'all' ? 'all' : `第${exercise.chapter}章`,
            sourceQuestionFiles: exercise.bankSources.map(s => s.url).join(' | ') },
        startedAt: session.startedAt, endedAt: session.endedAt
    });
    Object.assign(data.summary, { dataSchemaVersion: RESULT_VERSION, sessionId,
        questionMode: exercise.requestedMode, selectedQuestionId: exercise.questionId, bankSources: exercise.bankSources,
        questionTypeCounts: exercise.questions.reduce((counts, q) => { counts[q.questionType] = (counts[q.questionType] || 0) + 1; return counts; }, {}) });
    data.records.forEach((record, index) => {
        const q = exercise.questions[index];
        const selected = record.isAnswered ? q.options[session.answers[index].selected] : null;
        Object.assign(record, { dataSchemaVersion: RESULT_VERSION, sessionId, resultId: `${sessionId}_${index + 1}`,
            questionType: q.questionType, questionMode: q.questionMode,
            questionPrefix: q.questionPrefix, selectedInstruction: q.selectedInstruction, instructionPosition: q.instructionPosition,
            bankSource: q.bankSource, bankFormat: q.bankFormat, bankSchemaVersion: q.bankSchemaVersion,
            chapter: q.chapter, topic: q.topic, commonExplanation: q.explanation,
            correctOptionId: q.options.find(o => o.isCorrect).optionId,
            selectedOptionId: selected?.optionId ?? null, selectedPool: selected?.pool ?? null,
            answerConfirmed: session.answers[index].confirmed,
            displayedOptions: q.options.map((o, i) => ({ displayedPosition: i + 1, optionId: o.optionId,
                text: o.text, pool: o.pool, explanation: o.rationale, isCorrect: o.isCorrect })) });
    });
    data.reportBaseText += `\n出題方式: ${MODE_LABELS[exercise.requestedMode]}\n通常型は完成した問題文に対する正解候補を選びます。切り替え型は内容の適否と、この回に選ぶ正解を区別してください。\n`;
    return data;
}

const columns = keys => keys.map(key => ({ header: key, key }));
export function exportFile(data, type, ResultReport) {
    const { summary, records } = data;
    if (type === 'json') return { name: `IT_Snapshot_${summary.sessionId}.json`, mime: 'application/json',
        content: JSON.stringify({ format: 'it-polarity-result', schema_version: '1.1.0', summary, records }, null, 2) + '\n' };
    const sessionColumns = [...ResultReport.SESSION_CSV_COLUMNS, ...columns(['questionMode', 'selectedQuestionId', 'bankSources', 'questionTypeCounts'])];
    const questionColumns = [...ResultReport.QUESTION_RESULT_CSV_COLUMNS, ...columns([
        'questionType', 'questionMode', 'questionPrefix', 'selectedInstruction', 'instructionPosition',
        'bankSource', 'bankFormat', 'bankSchemaVersion', 'chapter', 'topic', 'commonExplanation',
        'answerConfirmed', 'selectedOptionId', 'selectedPool', 'correctOptionId', 'displayedOptions'
    ])];
    const csvRows = rows => rows.map(row => Object.fromEntries(Object.entries(row).map(([key, value]) =>
        [key, value !== null && typeof value === 'object' ? JSON.stringify(value) : value])));
    const toCsv = (rows, cols) => ResultReport.buildCsv(csvRows(rows), cols);
    let content;
    if (type === 'session') content = toCsv([summary], sessionColumns);
    else if (type === 'questions') content = toCsv(records, questionColumns);
    else if (type === 'options') content = toCsv(records.flatMap(r => r.displayedOptions.map(o => ({
        dataSchemaVersion: RESULT_VERSION, sessionId: summary.sessionId, resultId: r.resultId, questionId: r.questionId,
        questionType: r.questionType, questionMode: r.questionMode, bankSource: r.bankSource, ...o, isSelected: r.selectedOptionId === o.optionId
    }))), columns(['dataSchemaVersion', 'sessionId', 'resultId', 'questionId', 'questionType', 'questionMode', 'bankSource',
        'displayedPosition', 'optionId', 'text', 'pool', 'explanation', 'isCorrect', 'isSelected']));
    else throw new Error('未対応の出力形式です');
    return { name: `IT_${({ session: 'Session', questions: 'QuestionResult', options: 'DisplayedOptions' })[type]}_${summary.sessionId}.csv`, mime: 'text/csv', content };
}

export function buildReport(data, ResultReport) {
    const report = ResultReport.buildReport(data);
    const marker = '=== AI_ANALYSIS_DATA_JSON ===\n';
    const position = report.lastIndexOf(marker) + marker.length;
    const analysis = JSON.parse(report.slice(position));
    analysis.itSnapshot = JSON.parse(exportFile(data, 'json', ResultReport).content);
    analysis.questions.forEach((q, i) => { q.questionMode = data.records[i].questionMode; q.questionType = data.records[i].questionType; });
    return report.slice(0, position) + JSON.stringify(analysis);
}
