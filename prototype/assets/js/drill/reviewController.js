/* Drill adapter: shared output UI, data and export workflow. */
let resultOutputController = null;
function getDrillResultData() {
    return { summary: actualSummary, records: rawLogArray, questions: quizData, reportBaseText };
}
function initializeResultOutput() {
    resultOutputController = ResultOutput.mount({
        container: document.getElementById('result-output'),
        getData: getDrillResultData,
        notify: showToast
    });
}
function syncReviewFlag(checkbox) {
    const idx = Number(checkbox.getAttribute('data-idx'));
    if (rawLogArray[idx]) {
        rawLogArray[idx].reviewFlag = checkbox.checked;
        resultOutputController?.invalidate();
    }
}
function setComprehension(idx, level) {
    if (!rawLogArray[idx]) return;
    ResultReview.toggleUnderstanding(rawLogArray[idx], idx, level);
    resultOutputController?.invalidate();
}
function finalizeAndGenerateReport() {
    return resultOutputController?.finalize();
}
