/* =========================================================
 * SECTION 05: Exam Start / Question Set Construction
 * File: prototype/assets/js/drill/examController.js
 * ========================================================= */
function shuffle(array) {
    for (let i = array.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [array[i], array[j]] = [array[j], array[i]];
    }
    return array;
}

function startExam() {

    /*
     * ==========================================
     * 元問題データをコピー
     * ==========================================
     */

    let allQuestions =
        JSON.parse(
            JSON.stringify(
                originalQuizData
            )
        );


    /*
     * ==========================================
     * Practice Mode
     * Category Filter
     * ==========================================
     */

    if (appConfig.mode === "practice") {

        useConfidence =
            document.getElementById("use-confidence-checkbox")?.checked
            ?? true;

        selectedDifficultyMode =
            document.getElementById("difficulty-select")?.value
            ?? "all";

        const selectedLv1 =
            document.getElementById(
                "category-lv1-select"
            ).value;


        const selectedLv2 =
            document.getElementById(
                "category-lv2-select"
            ).value;


        const selectedLv3 =
            document.getElementById(
                "category-lv3-select"
            ).value;


        /*
         * Lv1
         */
        if (selectedLv1 !== "all") {

            allQuestions =
                allQuestions.filter(
                    q =>
                        String(
                            q.category_lv1 || ""
                        ) === selectedLv1
                );

        }


        /*
         * Lv2
         */
        if (selectedLv2 !== "all") {

            allQuestions =
                allQuestions.filter(
                    q =>
                        String(
                            q.category_lv2 || ""
                        ) === selectedLv2
                );

        }


        /*
         * Lv3
         */
        if (selectedLv3 !== "all") {

            allQuestions =
                allQuestions.filter(
                    q =>
                        String(
                            q.category_lv3 || ""
                        ) === selectedLv3
                );

        }

    }


    /*
     * ==========================================
     * Difficulty Filter
     * all  : 1-5
     * easy : 1-3
     * hard : 3-5
     * ==========================================
     */
    if (appConfig.mode === "practice") {
        allQuestions = filterQuestionsByDifficulty(
            allQuestions,
            selectedDifficultyMode
        );
    }


    /*
     * ==========================================
     * 0問チェック
     * ==========================================
     */

    if (allQuestions.length === 0) {

        alert(
            "指定したカテゴリ・難易度に該当する問題がありません。\n"
            + "条件を変更してもう一度お試しください。"
        );

        return;

    }


    /*
     * ==========================================
     * Random Shuffle
     * ==========================================
     */

    shuffle(allQuestions);


    /*
     * ==========================================
     * Question Count
     * ==========================================
     */

    const countSelect =
        document.getElementById(
            "question-count-select"
        ).value;


    let targetCount =
        allQuestions.length;


    if (countSelect !== "all") {

        targetCount =
            Math.min(
                parseInt(countSelect),
                allQuestions.length
            );

    }


    /*
     * ==========================================
     * Question Set
     * ==========================================
     */

    quizData =
        allQuestions.slice(
            0,
            targetCount
        );


    /*
     * 選択肢もランダム化
     */
    quizData.forEach(
        q => {

            shuffle(q.options);

        }
    );


    /*
     * ==========================================
     * ここから試験画面
     * ==========================================
     */

    document.getElementById(
        "start-container"
    ).style.display = "none";


    document.getElementById(
        "exam-container"
    ).style.display = "flex";


    examStartTime =
        Date.now();

    console.log(
        "[ExamController] 演習開始",
        {
            mode: appConfig.mode,
            questionCount: quizData.length,
            difficultyMode: selectedDifficultyMode,
            useConfidence
        }
    );


    /*
     * Mock Mode
     */
    if (appConfig.mode === "mock") {

        buildPalette();


        timeRemaining =
            appConfig.timeLimit * 60;


        startExamTimer();

    }


    qStartTime =
        Date.now();


    loadQuestion();

}

	



