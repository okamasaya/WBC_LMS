/* =========================================================
 * SECTION 07: Answer / Confidence Control
 * File: prototype/assets/js/drill/answerController.js
 * ========================================================= */
function selectOption(selectedIndex) {
    if (!userAnswers[currentQuestionIndex]) {
        userAnswers[currentQuestionIndex] = { selectedOption: null, elapsedTimeMs: 0, confidence: "NULL", isConfirmed: false, answerTimestamp: null };
    }
    userAnswers[currentQuestionIndex].selectedOption = selectedIndex;
    userAnswers[currentQuestionIndex].answerTimestamp = new Date().toISOString();

    if (appConfig.mode === "practice" && !useConfidence) {
        const elapsedMs = Date.now() - qStartTime;
        userAnswers[currentQuestionIndex].elapsedTimeMs += elapsedMs;
        userAnswers[currentQuestionIndex].confidence = "NULL";
        userAnswers[currentQuestionIndex].isConfirmed = true;
        userAnswers[currentQuestionIndex].answerTimestamp = new Date().toISOString();
        qStartTime = Date.now();
    }

    if (appConfig.mode === "mock") {
        const buttons = document.querySelectorAll('.option-btn');
        buttons.forEach((btn, idx) => {
            if (idx === selectedIndex) btn.classList.add('selected');
            else btn.classList.remove('selected');
        });
        updatePaletteStatus();
    } else {
        loadQuestion();
    }
}

function selectConfidence(level) {
    if (!userAnswers[currentQuestionIndex]) {
        userAnswers[currentQuestionIndex] = { selectedOption: null, elapsedTimeMs: 0, confidence: "NULL", isConfirmed: false, answerTimestamp: null };
    }
    
    const elapsedMs = Date.now() - qStartTime;
    userAnswers[currentQuestionIndex].elapsedTimeMs += elapsedMs;
    userAnswers[currentQuestionIndex].confidence = level;
    userAnswers[currentQuestionIndex].isConfirmed = true;
    userAnswers[currentQuestionIndex].answerTimestamp = new Date().toISOString();
    
    loadQuestion();
}

function scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function nextQuestion() { 
    if (currentQuestionIndex < quizData.length - 1) { 
        updateElapsedTimeForCurrentQuestion();
        currentQuestionIndex++;
        qStartTime = Date.now();
        loadQuestion(); 
        scrollToTop();
    } 
}

function prevQuestion() { 
    if (currentQuestionIndex > 0) { 
        updateElapsedTimeForCurrentQuestion();
        currentQuestionIndex--;
        qStartTime = Date.now();
        loadQuestion(); 
        scrollToTop();
    } 
}

function jumpToQuestion(index) { 
    updateElapsedTimeForCurrentQuestion();
    currentQuestionIndex = index; 
    qStartTime = Date.now();
    loadQuestion(); 
    scrollToTop();
}

function toggleFlag() {
    flaggedQuestions[currentQuestionIndex] = !flaggedQuestions[currentQuestionIndex];
    loadQuestion();
}

