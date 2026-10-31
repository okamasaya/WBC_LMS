/* Normalized Session / QuestionResult data for both drill and Actual. No DOM dependency. */
(() => {
    const confidenceLabels = ['自信がある', '少し自信がある', 'やや不安', '直感に近い'];
    const difficultyLabel = value => value === 1 || value === 2 ? '基礎' : value === 3 ? '標準' : value === 4 || value === 5 ? '発展' : '未設定';
    function build({ questions, answers, metadata, startedAt, endedAt, resolveSkill = () => null }) {
        const createdAt = new Date(endedAt).toISOString();
        const sessionId = `SESS_${endedAt}`;
        const identity = {
            dataSchemaVersion: '2.0.0', sessionId, studentId: metadata.studentId ?? null,
            examId: metadata.examId, examType: metadata.examType, examLevel: metadata.examLevel,
            examTitle: metadata.examTitle, mode: metadata.mode,
            useConfidence: metadata.useConfidence, difficultyMode: metadata.difficultyMode || 'all'
        };
        const mainCatStats = {};
        const records = questions.map((question, index) => {
            const answer = answers[index] || {};
            const selectedIndex = Number.isInteger(answer.selected) ? answer.selected : null;
            const selected = selectedIndex !== null ? question.options[selectedIndex] : null;
            const correctIndex = question.options.findIndex(option => option.isCorrect);
            const correct = question.options[correctIndex];
            const isAnswered = Boolean(selected), isCorrect = Boolean(selected?.isCorrect);
            const categoryLevel1 = String(question.category_lv1 ?? '');
            const categoryLevel2 = String(question.category_lv2 ?? '');
            const categoryLevel3 = String(question.category_lv3 ?? '');
            const categoryLabel = String(question.category || [categoryLevel1, categoryLevel2, categoryLevel3].filter(Boolean).join(' > ') || '未分類');
            const mainCat = categoryLabel.match(/【(.*?)】/)?.[1] || categoryLevel1 || categoryLabel;
            mainCatStats[mainCat] ||= { total: 0, correct: 0 };
            mainCatStats[mainCat].total++;
            if (isCorrect) mainCatStats[mainCat].correct++;
            const difficulty = question.difficulty == null || question.difficulty === '' ? null : Number(question.difficulty);
            const confidenceLevel = metadata.useConfidence === true && isAnswered && [1, 2, 3, 4].includes(Number(answer.confidence)) ? Number(answer.confidence) : null;
            const answeredAt = isAnswered ? answer.answeredAt || null : null;
            const timestamp = answeredAt ? Date.parse(answeredAt) : NaN;
            const skill = resolveSkill(question);
            return {
                ...identity, resultId: `RESULT_${endedAt}_${index + 1}`,
                questionSequence: index + 1, questionId: String(question.question_id || question.id || ''),
                skillId: skill?.skillId || null, skillName: skill?.skillName || null,
                categoryLevel1, categoryLevel2, categoryLevel3, categoryLabel,
                difficulty: Number.isFinite(difficulty) ? difficulty : null, difficultyLabel: difficultyLabel(difficulty),
                questionText: String(question.question_text || question.question || ''),
                userAnswerDisplayedPosition: isAnswered ? selectedIndex + 1 : null,
                userAnswerText: selected ? String(selected.text) : null,
                correctAnswerDisplayedPosition: correctIndex >= 0 ? correctIndex + 1 : null,
                correctAnswerText: correct ? String(correct.text) : null,
                correctAnswerSource: question.correct_answer ?? null,
                isAnswered, isCorrect, responseTimeMs: Number(answer.elapsedTimeMs || 0),
                answerTimeSec: Number((Number(answer.elapsedTimeMs || 0) / 1000).toFixed(1)),
                elapsedTimeSec: Number.isFinite(timestamp) ? Number(Math.max(0, (timestamp - startedAt) / 1000).toFixed(1)) : null,
                answeredAt, confidenceLevel,
                confidenceLabel: metadata.useConfidence === true ? confidenceLabels[confidenceLevel - 1] || '未入力' : '記録なし',
                understandingLevel: null, understandingLabel: '未入力', reviewFlag: false,
                duringExamReviewFlag: Boolean(answer.flagged),
                explanation: String(question.explanation || correct?.rationale || ''), createdAt
            };
        });
        const correctCount = records.filter(record => record.isCorrect).length;
        const answeredQuestions = records.filter(record => record.isAnswered).length;
        const totalTimeSec = Math.floor(Math.max(0, endedAt - startedAt) / 1000);
        const summary = {
            ...identity, difficultyModeLabel: ({ all: 'すべて', easy: '易しい', hard: '難しい' })[identity.difficultyMode] || 'すべて',
            selectedCategoryLevel1: metadata.selectedCategoryLevel1 || 'all',
            selectedCategoryLevel2: metadata.selectedCategoryLevel2 || 'all',
            selectedCategoryLevel3: metadata.selectedCategoryLevel3 || 'all',
            startAt: new Date(startedAt).toISOString(), endAt: createdAt, totalTimeSec,
            totalQuestions: questions.length, answeredQuestions,
            unansweredQuestions: questions.length - answeredQuestions,
            correctCount, incorrectCount: answeredQuestions - correctCount, wrongCount: questions.length - correctCount,
            scoreRate: questions.length ? Math.round(correctCount / questions.length * 100) : 0,
            sourceQuestionFiles: metadata.sourceQuestionFiles || '', createdAt
        };
        const modeLabel = metadata.mode === 'Actual' ? '模擬試験' : '練習ドリル';
        let reportBaseText = `演習モード: ${modeLabel}\n実施日時: ${new Date(endedAt).toLocaleString()}\n総実施時間: ${Math.floor(totalTimeSec / 60)}分${totalTimeSec % 60}秒\n総合スコア: ${summary.scoreRate}点\n\n■ 分野別正解率\n`;
        for (const [category, stats] of Object.entries(mainCatStats)) {
            reportBaseText += `· ${category}: ${Math.round(stats.correct / stats.total * 100)}% (${stats.correct}/${stats.total})\n`;
        }
        return { summary, records, questions, reportBaseText, mainCatStats };
    }
    window.ResultData = Object.freeze({ build });
})();
