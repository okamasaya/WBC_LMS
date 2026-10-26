/* =========================================================
 * SECTION 04: Timing / Initialization
 * File: prototype/assets/js/drill/app.js
 * ========================================================= */
function updateElapsedTimeForCurrentQuestion() {
    if (quizData.length === 0 || currentQuestionIndex < 0 || qStartTime === 0) return;
    
    if (appConfig.mode === "mock" || (appConfig.mode === "practice" && !userAnswers[currentQuestionIndex]?.isConfirmed)) {
        const elapsedMs = Date.now() - qStartTime;
        
        if (!userAnswers[currentQuestionIndex]) {
            userAnswers[currentQuestionIndex] = { selectedOption: null, elapsedTimeMs: 0, confidence: "NULL", isConfirmed: false, answerTimestamp: null };
        }
        userAnswers[currentQuestionIndex].elapsedTimeMs += elapsedMs;
    }
    qStartTime = Date.now();
}

window.onload = async function() {

    /*
     * ==========================================
     * Ver.2
     * 問題JSONを起動時に読み込む
     * ==========================================
     */

    originalQuizData =
        await createQuestionSet();


    console.log(
        "[QuizEngine] 読込問題数:",
        originalQuizData.length
    );


    /*
     * 問題が読み込めなかった場合
     */
    if (originalQuizData.length === 0) {

        document.getElementById(
            "description-display"
        ).innerHTML =
            "<strong style='color:#dc2626;'>"
            + "問題データを読み込めませんでした。"
            + "</strong>";

        return;

    }


    /*
     * ==========================================
     * Practice Mode
     * ==========================================
     */

    if (appConfig.mode === "practice") {
        updatePracticeDescription();

        const confidenceCheckbox =
            document.getElementById("use-confidence-checkbox");

        if (confidenceCheckbox) {
            confidenceCheckbox.addEventListener(
                "change",
                updatePracticeDescription
            );
        }


        document.getElementById(
            "timer"
        ).style.display = "none";


        document.getElementById(
            "sidebar-panel"
        ).style.display = "none";


        document.getElementById(
            "flag-button"
        ).style.display = "none";


        document.getElementById(
            "category-select-container"
        ).style.display = "inline-block";


        /*
         * Ver.2
         * Lv1 / Lv2 / Lv3
         */
        initializeCategorySelectors();


        /*
         * 「演習終了」ボタン追加
         */
        const ctrlBox =
            document.querySelector(
                ".control-box"
            );


        const pBtn =
            document.createElement(
                "button"
            );


        pBtn.className =
            "nav-btn submit-btn";


        pBtn.innerText =
            "演習を終了して採点";


        pBtn.onclick =
            function() {

                submitExam(false);

            };


        ctrlBox.appendChild(pBtn);

    }


    /*
     * ==========================================
     * Mock Mode
     * ==========================================
     */

    else {

        document.getElementById(
            "description-display"
        ).innerHTML =
            `本番模擬（Actual）形式で一括採点を行います。`
            + `<br>`
            + `制限時間（${appConfig.timeLimit}分）内に`
            + `全問解答してください。`;

    }

};


