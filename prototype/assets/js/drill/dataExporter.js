/* Compatibility entry points; all exports use the shared finalized snapshot. */
function copyReport() { return resultOutputController?.copy(); }
function downloadExcelCSV() { return resultOutputController?.download('raw'); }
function downloadQuestionResultCSV() { return resultOutputController?.download('questions'); }
function downloadSessionCSV() { return resultOutputController?.download('session'); }
