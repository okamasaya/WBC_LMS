/* Compatibility entry point; report generation is shared with Actual. */
function buildReportPayloadText() {
    document.getElementById('report-text').value = ResultReport.buildReport(getDrillResultData());
}
