/* =========================================================
 * SECTION 06: Question Rendering / Navigation
 * File: prototype/assets/js/drill/questionView.js
 * ========================================================= */
function buildPalette() {
    const grid = document.getElementById('palette-grid');
    grid.innerHTML = '';
    quizData.forEach((_, index) => {
        const item = document.createElement('div');
        item.className = 'palette-item';
        item.id = `palette-${index}`;
        item.innerText = index + 1;
        item.onclick = () => jumpToQuestion(index);
        grid.appendChild(item);
    });
}

function updatePaletteStatus() {
    if (appConfig.mode !== "mock") return;
    quizData.forEach((_, index) => {
        const item = document.getElementById(`palette-${index}`);
        if (!item) return;
        item.className = 'palette-item';
        if (index === currentQuestionIndex) item.classList.add('current');
        if (userAnswers[index] !== undefined && userAnswers[index].selectedOption !== null) item.classList.add('answered');
        if (flaggedQuestions[index]) item.classList.add('flagged');
    });
}

function loadQuestion() {
    if (quizData.length === 0) return;
    const currentQuestion = quizData[currentQuestionIndex];
    document.getElementById('progress').innerText = `問題 ${currentQuestionIndex + 1} / ${quizData.length}`;
    document.getElementById('category-display').innerText = `${currentQuestion.category || "未分類"}`;
    document.getElementById('question-text').innerHTML = formatText(currentQuestion.question);
    
    const optionsContainer = document.getElementById('options-container');
    optionsContainer.innerHTML = '';
    optionsContainer.className = `options layout-${appConfig.layout || 'normal'}`;
    
    const confPanel = document.getElementById("confidence-panel");
    const feedbackPanel = document.getElementById("instant-feedback");
    
    confPanel.style.display = "none";
    feedbackPanel.style.display = "none";
    feedbackPanel.innerHTML = "";
    
    const ansObj = userAnswers[currentQuestionIndex] || { selectedOption: null, elapsedTimeMs: 0, confidence: "NULL", isConfirmed: false, answerTimestamp: null };
    const currentSelectedIdx = ansObj.selectedOption;
    const correctOption = currentQuestion.options.find(o => o.isCorrect);

    currentQuestion.options.forEach((option, index) => {
        const button = document.createElement('button');
        button.className = 'option-btn';
        button.innerHTML = `<span class="option-num">${index + 1}</span><div class="option-text">${formatText(option.text)}</div>`;
        
        if (appConfig.mode === "mock") {
            if (currentSelectedIdx === index) button.classList.add('selected');
            button.onclick = () => selectOption(index);
        } else {
            if (ansObj.isConfirmed) {
                if (option.isCorrect) button.classList.add('correct');
                if (currentSelectedIdx === index && !option.isCorrect) button.classList.add('incorrect');
                button.disabled = true;
            } else {
                if (currentSelectedIdx === index) button.classList.add('selected');
                button.onclick = () => selectOption(index);
            }
        }
        optionsContainer.appendChild(button);
    });

    if (appConfig.mode === "practice") {
        if (useConfidence && currentSelectedIdx !== null && !ansObj.isConfirmed) {
            confPanel.style.display = "block";
        } else if (ansObj.isConfirmed) {
            const selectedOption = currentQuestion.options[currentSelectedIdx];
            const isCorrect = selectedOption ? selectedOption.isCorrect : false;
            const sec = (ansObj.elapsedTimeMs / 1000).toFixed(1);
            const confidenceText =
                useConfidence && ansObj.confidence !== "NULL"
                    ? ` / 自信度: ${ansObj.confidence}`
                    : "";

            feedbackPanel.style.display = "block";
            feedbackPanel.innerHTML = `<strong>${isCorrect ? "◯ 正解！" : "✕ 不正解..."} (回答時間: ${sec}秒${confidenceText})</strong><br><br><strong>解説:</strong><br>${correctOption ? formatText(correctOption.rationale) : "解説はありません。"}`;
        }
    }

    const flagBtn = document.getElementById('flag-button');
    if (flagBtn) {
        if (flaggedQuestions[currentQuestionIndex]) {
            flagBtn.classList.add('flagged');
        } else {
            flagBtn.classList.remove('flagged');
        }
    }
    updatePaletteStatus();
}

