/* =========================================================
 * SECTION 11: Data Export / Clipboard
 * File: prototype/assets/js/drill/dataExporter.js
 * Session / QuestionResult raw export schema implemented in Phase 3.
 * ========================================================= */
function copyReport() {
    const txt = document.getElementById("report-text");
    txt.select();
    document.execCommand("copy");
    showToast("レポートをクリップボードにコピーしました。");
}

function downloadFile(content, fileName, mimeType) {
    const bom = new Uint8Array([0xEF, 0xBB, 0xBF]);
    const blob = new Blob([bom, content], { type: mimeType });

    if (navigator.msSaveBlob) {
        navigator.msSaveBlob(blob, fileName);
        return;
    }

    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.setAttribute("download", fileName);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(objectUrl);
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

function downloadExcelCSV() {
    if (!actualSummary.sessionId || rawLogArray.length === 0) return;

    let csvContent = "=== Session ===\r\n";
    csvContent += buildCsv([actualSummary], SESSION_CSV_COLUMNS);
    csvContent += "\r\n=== QuestionResult ===\r\n";
    csvContent += buildCsv(rawLogArray, QUESTION_RESULT_CSV_COLUMNS);

    downloadFile(
        csvContent,
        `CBT_RAW_${actualSummary.sessionId}.csv`,
        "text/csv;charset=utf-8;"
    );
    showToast("Session / QuestionResult の統合Raw CSVをダウンロードしました。");
}

function downloadQuestionResultCSV() {
    if (rawLogArray.length === 0) return;

    const csvContent = buildCsv(rawLogArray, QUESTION_RESULT_CSV_COLUMNS);
    downloadFile(
        csvContent,
        `QuestionResult_${actualSummary.sessionId}.csv`,
        "text/csv;charset=utf-8;"
    );
    showToast("QuestionResult.csv をダウンロードしました。");
}

function downloadSessionCSV() {
    if (!actualSummary.sessionId) return;

    const csvContent = buildCsv([actualSummary], SESSION_CSV_COLUMNS);
    downloadFile(
        csvContent,
        `Session_${actualSummary.sessionId}.csv`,
        "text/csv;charset=utf-8;"
    );
    showToast("Session.csv をダウンロードしました。");
}
