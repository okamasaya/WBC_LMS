/* Shared, DOM-independent AI report and CSV schema. */
(() => {
function buildReport({ summary: actualSummary, records: rawLogArray, questions: quizData, reportBaseText }) {
    const difficultyLabelMap = {
        1: "基礎",
        2: "基礎",
        3: "標準",
        4: "発展",
        5: "発展"
    };

    const difficultyModeLabelMap = {
        all: "すべて",
        easy: "易しい問題を中心",
        hard: "難しい問題を中心"
    };

    const confidenceLabelMap = {
        "1": "自信がある",
        "2": "少し自信がある",
        "3": "やや不安",
        "4": "直感に近い",
        "NULL": "未入力"
    };

    const comprehensionLabelMap = {
        "3": "理解できた",
        "2": "だいたい理解できた",
        "1": "まだ少し分からない",
        "0": "全然分からない",
        "NULL": "未入力"
    };

    const formatDifficultyLabel = (difficulty) => {
        const value = Number(difficulty);
        return difficultyLabelMap[value] || "未設定";
    };

    const formatConfidenceLabel = (confidence) => {
        if (actualSummary.useConfidence !== true) {
            return "記録なし";
        }

        const key = String(confidence ?? "NULL");
        const label = confidenceLabelMap[key] || "未入力";
        return key === "NULL" ? label : `${key} (${label})`;
    };

    const difficultyModeLabel =
        difficultyModeLabelMap[actualSummary.difficultyMode] || "すべて";

    const confidenceModeLabel =
        actualSummary.useConfidence === true
            ? "あり"
            : actualSummary.useConfidence === false
                ? "なし"
                : "対象外";

    let finalPayload = "";

    finalPayload += `【AI学習レポート作成依頼】\n`;
    finalPayload += `あなたは、CBTの学習記録を分析するAI学習メンターです。\n`;
    finalPayload += `以下の演習結果をもとに、学習者の現在の理解状況と今後の学習方針を評価してください。\n\n`;

    finalPayload += `【分析ルール】\n`;
    finalPayload += `・正答率だけで判断せず、問題カテゴリ、難易度、回答時間、自信度、解説理解度、復習フラグを組み合わせて評価してください。\n`;
    finalPayload += `・「できなかったこと」だけでなく、「できたこと」「定着してきたこと」「次に伸ばせること」を具体的なデータを根拠に示してください。\n`;
    finalPayload += `・回答時間が長いことだけを悪い結果と判断しないでください。難易度や正誤、自信度と合わせて解釈してください。\n`;
    finalPayload += `・不正解でも、解説確認後の理解度が高い場合は、学習が進んだ結果として考慮してください。\n`;
    finalPayload += `・自信度が記録されていない場合は、自信度について推測しないでください。\n`;
    finalPayload += `・1回分の結果だけから「苦手」「能力不足」などと断定しないでください。\n`;
    finalPayload += `・追加問題の作成や出題は不要です。今回は学習結果の分析と次の学習方針の提案に専念してください。\n\n`;

    finalPayload += `【複数回の結果をまとめて渡した場合】\n`;
    finalPayload += `この形式のレポートが複数ある場合は、Session IDごとに1回の演習として扱い、実施日時順に比較してください。\n`;
    finalPayload += `正答率だけでなく、難易度、カテゴリ別成績、回答時間、自信度、解説理解度の変化も見てください。\n`;
    finalPayload += `前回より正答率が下がっていても、より難しい問題に取り組んでいる場合は、その挑戦を考慮して評価してください。\n`;
    finalPayload += `過去データが1回分しかない場合は、存在しない学習推移を推測しないでください。\n\n`;

    finalPayload += `【出力してほしい内容】\n`;
    finalPayload += `1. 今回の演習の要約\n`;
    finalPayload += `2. データから確認できる良かった点\n`;
    finalPayload += `3. 次に確認・復習すると効果がありそうな点\n`;
    finalPayload += `4. 複数回分がある場合は学習の変化・成長\n`;
    finalPayload += `5. 次回の学習への具体的なアドバイス\n\n`;
    finalPayload += `評価は前向きかつ具体的にし、根拠のない過度な称賛は避けてください。日本語学習者にも理解しやすい表現を使用してください。\n\n`;

    finalPayload += `=== CBT_SESSION_BEGIN ===\n`;
    finalPayload += `Session ID: ${actualSummary.sessionId || "未設定"}\n`;
    finalPayload += `実施日時: ${actualSummary.startAt || "未設定"}\n`;
    finalPayload += `演習モード: ${actualSummary.mode || "未設定"}\n`;
    finalPayload += `出題難易度設定: ${difficultyModeLabel}\n`;
    finalPayload += `自信度記録: ${confidenceModeLabel}\n\n`;

    finalPayload += `【演習サマリー】\n`;
    finalPayload += reportBaseText + `\n`;

    finalPayload += `【各問題の演習詳細】\n`;

    const aiQuestionResults = [];

    rawLogArray.forEach((item, idx) => {
        const q = quizData[idx];
        const difficultyLabel = item.difficultyLabel || formatDifficultyLabel(q?.difficulty);
        const confidenceLabel = formatConfidenceLabel(item.confidenceLevel);
        const comprehensionKey = item.understandingLevel == null ? "NULL" : String(item.understandingLevel);
        const comprehensionLabel =
            comprehensionLabelMap[comprehensionKey] || "未入力";

        let reportLine = `[問${idx + 1}] ${item.isCorrect ? "○ 正解" : item.isAnswered ? "× 不正解" : "未回答"}\n`;
        reportLine += `・カテゴリ: ${item.categoryLabel}\n`;
        if (item.skillName) reportLine += `・学習スキル: ${item.skillName}\n`;
        reportLine += `・難易度: ${difficultyLabel}\n`;
        reportLine += `・問題文: ${q?.question || ""}\n`;
        reportLine += `・回答時間: ${item.answerTimeSec}秒\n`;
        reportLine += `・自信度: ${confidenceLabel}\n`;
        reportLine += `・解説理解度: ${comprehensionKey === "NULL" ? "未入力" : `${comprehensionKey} (${comprehensionLabel})`}\n`;
        reportLine += `・要復習フラグ: ${item.reviewFlag ? "TRUE" : "FALSE"}\n\n`;

        finalPayload += reportLine;

        aiQuestionResults.push({
            questionNumber: idx + 1,
            correct: item.isCorrect,
            category: item.categoryLabel,
            skillId: item.skillId,
            skillName: item.skillName,
            difficulty: difficultyLabel,
            answerTimeSec: item.answerTimeSec,
            confidence: confidenceLabel,
            explanationUnderstanding:
                comprehensionKey === "NULL"
                    ? "未入力"
                    : `${comprehensionKey} (${comprehensionLabel})`,
            review: item.reviewFlag
        });
    });

    finalPayload += `=== CBT_SESSION_END ===\n`;

    finalPayload += `\n=== AI_ANALYSIS_DATA_JSON ===\n`;
    finalPayload += JSON.stringify({
        session: {
            sessionId: actualSummary.sessionId,
            startTime: actualSummary.startAt,
            mode: actualSummary.mode,
            difficultySetting: difficultyModeLabel,
            confidenceRecorded: confidenceModeLabel,
            totalTimeSec: actualSummary.totalTimeSec,
            questionCount: actualSummary.totalQuestions,
            correctCount: actualSummary.correctCount,
            wrongCount: actualSummary.wrongCount,
            accuracy: actualSummary.scoreRate
        },
        questions: aiQuestionResults
    });

    return finalPayload;
}


function csvEscape(value) {
    if (value === null || value === undefined) return "";
    const normalized = typeof value === "boolean"
        ? (value ? "TRUE" : "FALSE")
        : String(value);
    return `"${normalized.replace(/"/g, '""')}"`;
}

function buildCsv(records, columns) {
    const header = columns.map(column => csvEscape(column.header)).join(",");
    const rows = records.map(record =>
        columns.map(column => csvEscape(record[column.key])).join(",")
    );
    return [header, ...rows].join("\r\n") + "\r\n";
}

const SESSION_CSV_COLUMNS = Object.freeze([
    { header: "DataSchemaVersion", key: "dataSchemaVersion" },
    { header: "SessionID", key: "sessionId" },
    { header: "StudentID", key: "studentId" },
    { header: "ExamID", key: "examId" },
    { header: "ExamType", key: "examType" },
    { header: "ExamLevel", key: "examLevel" },
    { header: "ExamTitle", key: "examTitle" },
    { header: "Mode", key: "mode" },
    { header: "UseConfidence", key: "useConfidence" },
    { header: "DifficultyMode", key: "difficultyMode" },
    { header: "DifficultyModeLabel", key: "difficultyModeLabel" },
    { header: "SelectedCategoryLevel1", key: "selectedCategoryLevel1" },
    { header: "SelectedCategoryLevel2", key: "selectedCategoryLevel2" },
    { header: "SelectedCategoryLevel3", key: "selectedCategoryLevel3" },
    { header: "StartAt", key: "startAt" },
    { header: "EndAt", key: "endAt" },
    { header: "TotalTimeSec", key: "totalTimeSec" },
    { header: "TotalQuestions", key: "totalQuestions" },
    { header: "AnsweredQuestions", key: "answeredQuestions" },
    { header: "UnansweredQuestions", key: "unansweredQuestions" },
    { header: "CorrectCount", key: "correctCount" },
    { header: "IncorrectCount", key: "incorrectCount" },
    { header: "WrongCount", key: "wrongCount" },
    { header: "ScoreRate", key: "scoreRate" },
    { header: "SourceQuestionFiles", key: "sourceQuestionFiles" },
    { header: "CreatedAt", key: "createdAt" }
]);

const QUESTION_RESULT_CSV_COLUMNS = Object.freeze([
    { header: "DataSchemaVersion", key: "dataSchemaVersion" },
    { header: "ResultID", key: "resultId" },
    { header: "SessionID", key: "sessionId" },
    { header: "StudentID", key: "studentId" },
    { header: "ExamID", key: "examId" },
    { header: "ExamType", key: "examType" },
    { header: "ExamLevel", key: "examLevel" },
    { header: "ExamTitle", key: "examTitle" },
    { header: "Mode", key: "mode" },
    { header: "UseConfidence", key: "useConfidence" },
    { header: "DifficultyMode", key: "difficultyMode" },
    { header: "QuestionSequence", key: "questionSequence" },
    { header: "QuestionID", key: "questionId" },
    { header: "SkillID", key: "skillId" },
    { header: "SkillName", key: "skillName" },
    { header: "CategoryLevel1", key: "categoryLevel1" },
    { header: "CategoryLevel2", key: "categoryLevel2" },
    { header: "CategoryLevel3", key: "categoryLevel3" },
    { header: "CategoryLabel", key: "categoryLabel" },
    { header: "Difficulty", key: "difficulty" },
    { header: "DifficultyLabel", key: "difficultyLabel" },
    { header: "QuestionText", key: "questionText" },
    { header: "UserAnswerDisplayedPosition", key: "userAnswerDisplayedPosition" },
    { header: "UserAnswerText", key: "userAnswerText" },
    { header: "CorrectAnswerDisplayedPosition", key: "correctAnswerDisplayedPosition" },
    { header: "CorrectAnswerText", key: "correctAnswerText" },
    { header: "CorrectAnswerSource", key: "correctAnswerSource" },
    { header: "IsAnswered", key: "isAnswered" },
    { header: "IsCorrect", key: "isCorrect" },
    { header: "ResponseTimeMs", key: "responseTimeMs" },
    { header: "AnswerTimeSec", key: "answerTimeSec" },
    { header: "ElapsedTimeSec", key: "elapsedTimeSec" },
    { header: "AnsweredAt", key: "answeredAt" },
    { header: "ConfidenceLevel", key: "confidenceLevel" },
    { header: "ConfidenceLabel", key: "confidenceLabel" },
    { header: "UnderstandingLevel", key: "understandingLevel" },
    { header: "UnderstandingLabel", key: "understandingLabel" },
    { header: "ReviewFlag", key: "reviewFlag" },
    { header: "DuringExamReviewFlag", key: "duringExamReviewFlag" },
    { header: "Explanation", key: "explanation" },
    { header: "CreatedAt", key: "createdAt" }
]);


    function exportCsv(data, type) {
        const { summary, records } = data;
        if (type === 'session') return { name: `Session_${summary.sessionId}.csv`, content: buildCsv([summary], SESSION_CSV_COLUMNS) };
        if (type === 'questions') return { name: `QuestionResult_${summary.sessionId}.csv`, content: buildCsv(records, QUESTION_RESULT_CSV_COLUMNS) };
        if (type === 'raw') return { name: `CBT_RAW_${summary.sessionId}.csv`, content: '=== Session ===\r\n' + buildCsv([summary], SESSION_CSV_COLUMNS) + '\r\n=== QuestionResult ===\r\n' + buildCsv(records, QUESTION_RESULT_CSV_COLUMNS) };
        throw new Error('不明なCSV形式です。');
    }
    window.ResultReport = Object.freeze({ buildReport, buildCsv, csvEscape, exportCsv, SESSION_CSV_COLUMNS, QUESTION_RESULT_CSV_COLUMNS });
})();
