/* =========================================================
 * SECTION 01: Application State / Configuration
 * File: prototype/assets/js/drill/drillState.js
 * ========================================================= */
let originalQuizData = [];
let quizData = [];
let currentQuestionIndex = 0;
let userAnswers = {}; 
let flaggedQuestions = {};
let timerInterval = null;
let timeRemaining = 0;
let examStartTime = 0;
let examEndTime = 0;
let qStartTime = 0; 
let reportBaseText = "";

// Internal variable names are retained for compatibility with the current HTML.
// The data stored in them now follows Session / QuestionResult-oriented raw schemas.
let rawLogArray = [];
let actualSummary = {};

// Practice session options selected on the start screen.
let useConfidence = true;
let selectedDifficultyMode = "all";

