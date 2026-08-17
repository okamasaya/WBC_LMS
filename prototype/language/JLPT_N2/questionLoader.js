/**
 * ========================================================
 * School LMS
 * Question Loader
 *
 * Version:
 * 0.2.0
 *
 * Role:
 * - Load question JSON
 * - Validate question data
 * - Convert School-LMS standard format
 *   to Quiz Engine format
 *
 * ========================================================
 */


/**
 * --------------------------------------------------------
 * Load JSON file
 * --------------------------------------------------------
 */
/*
async function loadQuestionData() {

    try {

        if (!CONFIG.questionFile) {
            throw new Error(
                "CONFIG.questionFile が設定されていません。"
            );
        }

        console.log(
            "[QuestionLoader] Loading:",
            CONFIG.questionFile
        );

        const response = await fetch(
            CONFIG.questionFile,
            {
                cache: "no-store"
            }
        );

        if (!response.ok) {

            throw new Error(
                `問題ファイルを読み込めませんでした。`
                + ` HTTP Status: ${response.status}`
            );

        }

        const jsonData = await response.json();



        let questionData;

        if (Array.isArray(jsonData)) {

            questionData = jsonData;

        } else if (
            jsonData &&
            Array.isArray(jsonData.questions)
        ) {

            questionData = jsonData.questions;

        } else {

            throw new Error(
                "JSONの形式が正しくありません。"
                + " 配列、または questions 配列が必要です。"
            );

        }


        console.log(
            `[QuestionLoader] ${questionData.length}問を読み込みました。`
        );

        return questionData;


    } catch (error) {

        console.error(
            "[QuestionLoader] JSON読込エラー:",
            error
        );

        alert(
            "問題データの読み込みに失敗しました。\n\n"
            + error.message
        );

        return [];

    }

}
*/

async function loadMultipleQuestionData(filePaths) {
    console.log("[QuestionLoader] filePaths =", filePaths);
    console.log("[QuestionLoader] CONFIG =", CONFIG);
    try {
        const dataList = await Promise.all(
            filePaths.map(filePath => loadQuestionData(filePath))
        );

        return dataList.flat();

    } catch (error) {
        console.error(
            "[QuestionLoader] 複数JSON読込エラー:",
            error
        );
        throw error;
    }

    
}

/**
 * --------------------------------------------------------
 * Convert correct_answer to option number
 *
 * Supported:
 *
 * 1 / 2 / 3 / 4
 * A / B / C / D
 * option_1 / option_2 / ...
 * option text itself
 *
 * --------------------------------------------------------
 */
function getCorrectAnswerNumber(question) {

    const value = question.correct_answer;

    if (
        value === null ||
        value === undefined
    ) {
        return null;
    }


    const answer = String(value)
        .trim()
        .toUpperCase();


    /*
     * 1 ～ 4
     */
    if (/^[1-4]$/.test(answer)) {

        return Number(answer);

    }


    /*
     * A ～ D
     */
    const alphabetMap = {

        "A": 1,
        "B": 2,
        "C": 3,
        "D": 4

    };

    if (alphabetMap[answer]) {

        return alphabetMap[answer];

    }


    /*
     * option_1 ～ option_4
     */
    const optionMatch =
        answer.match(/^OPTION_([1-4])$/);

    if (optionMatch) {

        return Number(optionMatch[1]);

    }


    /*
     * 正解選択肢の文章そのものが
     * correct_answer に入っている場合
     */
    for (let i = 1; i <= 4; i++) {

        const optionText =
            question[`option_${i}`];

        if (
            optionText !== undefined &&
            String(optionText).trim() ===
            String(value).trim()
        ) {

            return i;

        }

    }


    return null;

}


/**
 * --------------------------------------------------------
 * Generate category label
 *
 * Example:
 *
 * 【言語知識】語彙 > 用法
 *
 * --------------------------------------------------------
 */
function buildCategoryLabel(question) {

    const lv1 =
        question.category_lv1
            ? String(question.category_lv1).trim()
            : "";

    const lv2 =
        question.category_lv2
            ? String(question.category_lv2).trim()
            : "";

    const lv3 =
        question.category_lv3
            ? String(question.category_lv3).trim()
            : "";


    let label = "";


    if (lv1) {

        label += `【${lv1}】`;

    }


    if (lv2) {

        label += lv2;

    }


    if (lv3) {

        if (lv2) {

            label += " > ";

        }

        label += lv3;

    }


    if (!label) {

        label = "未分類";

    }


    return label;

}


/**
 * --------------------------------------------------------
 * Validate question
 * --------------------------------------------------------
 */
function validateQuestion(question, index) {

    const rowNumber = index + 1;

    if (!question.question_id) {

        throw new Error(
            `${rowNumber}件目: question_id がありません。`
        );

    }


    if (!question.question_text) {

        throw new Error(
            `${question.question_id}: question_text がありません。`
        );

    }


    for (let i = 1; i <= 4; i++) {

        if (
            question[`option_${i}`] === undefined ||
            question[`option_${i}`] === null ||
            String(question[`option_${i}`]).trim() === ""
        ) {

            throw new Error(
                `${question.question_id}: option_${i} がありません。`
            );

        }

    }


    const correctAnswerNumber =
        getCorrectAnswerNumber(question);


    if (!correctAnswerNumber) {

        throw new Error(
            `${question.question_id}: `
            + `correct_answer の値が不正です。`
            + ` value=${question.correct_answer}`
        );

    }


    return correctAnswerNumber;

}


/**
 * --------------------------------------------------------
 * Convert School-LMS standard format
 * to current Quiz Engine format
 * --------------------------------------------------------
 */
function convertQuestionFormat(question, index) {

    const correctAnswerNumber =
        validateQuestion(question, index);


    const explanation =
        question.explanation
            ? String(question.explanation)
            : "";


    const options = [];


    for (let i = 1; i <= 4; i++) {

        options.push({

            text:
                String(question[`option_${i}`]),

            isCorrect:
                i === correctAnswerNumber,

            rationale:
                explanation

        });

    }


    /*
     * 既存Quiz Engineが使用する形式
     *
     * id
     * category
     * question
     * options[]
     *
     * を維持する。
     *
     * 同時に標準カラムも保持しておく。
     */

    return {

        /* ===== Existing Engine ===== */

        id:
            String(question.question_id),

        category:
            buildCategoryLabel(question),

        question:
            String(question.question_text),

        options:
            options,


        /* ===== School-LMS Standard ===== */

        question_id:
            String(question.question_id),

        category_lv1:
            question.category_lv1 ?? "",

        category_lv2:
            question.category_lv2 ?? "",

        category_lv3:
            question.category_lv3 ?? "",

        difficulty:
            question.difficulty ?? "",

        question_text:
            String(question.question_text),

        correct_answer:
            String(question.correct_answer),

        explanation:
            explanation

    };

}


/**
 * --------------------------------------------------------
 * Create Question Set
 *
 * 現段階では
 *
 * JSON読込
 *      ↓
 * Validation
 *      ↓
 * Engine形式へ変換
 *
 * のみ。
 *
 * カテゴリフィルタ・問題数制限・ランダム抽選は
 * 現在のQuiz Engine側に任せる。
 *
 * --------------------------------------------------------
 */
async function createQuestionSet() {

    try {
        /// update 0818
        //const rawQuestions =
            //await loadQuestionData();
            const questions = await loadMultipleQuestionData(
                CONFIG.questionFiles
            );

        if (rawQuestions.length === 0) {

            console.warn(
                "[QuestionLoader] 問題が0件です。"
            );

            return [];

        }


        const convertedQuestions =
            rawQuestions.map(
                (question, index) =>
                    convertQuestionFormat(
                        question,
                        index
                    )
            );


        console.log(
            `[QuestionLoader] `
            + `${convertedQuestions.length}問の変換が完了しました。`
        );


        console.log(
            "[QuestionLoader] Sample:",
            convertedQuestions[0]
        );


        return convertedQuestions;


    } catch (error) {

        console.error(
            "[QuestionLoader] 問題変換エラー:",
            error
        );


        alert(
            "問題データの変換に失敗しました。\n\n"
            + error.message
        );


        return [];

    }

}
