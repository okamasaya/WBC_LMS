/* Canonical question bank IO / validation / conversion for the current runtime.
 * Legacy pages keep their original N2 loader. No CONFIG-dependent startup functions.
 */
function normalizeQuestionFilePaths(filePaths) {

    let normalizedPaths;


    /*
     * 単一ファイル文字列の場合
     */
    if (typeof filePaths === "string") {

        normalizedPaths = [filePaths];

    /*
     * 複数ファイル配列の場合
     */
    } else if (Array.isArray(filePaths)) {

        normalizedPaths = filePaths;

    } else {

        throw new Error(
            "問題ファイルの設定形式が正しくありません。"
            + " questionFilesには配列を設定してください。"
        );

    }


    if (normalizedPaths.length === 0) {

        throw new Error(
            "読み込む問題ファイルが設定されていません。"
        );

    }


    return normalizedPaths.map(
        (filePath, index) => {

            if (
                typeof filePath !== "string" ||
                filePath.trim() === ""
            ) {

                throw new Error(
                    `問題ファイル設定の${index + 1}件目が不正です。`
                );

            }


            return filePath.trim();

        }
    );

}


async function loadQuestionData(filePath) {

    console.log(
        "[QuestionLoader] Loading:",
        filePath
    );


    let response;


    /*
     * JSONファイル取得
     */
    try {

        response = await fetch(
            filePath,
            {
                cache: "no-store"
            }
        );

    } catch (error) {

        throw new Error(
            `${filePath}の取得に失敗しました。`
            + ` ${error.message}`
        );

    }


    /*
     * HTTPエラー確認
     */
    if (!response.ok) {

        throw new Error(
            `${filePath}を読み込めませんでした。`
            + ` HTTP Status: ${response.status}`
        );

    }


    let jsonData;


    /*
     * JSON解析
     */
    try {

        jsonData = await response.json();

    } catch (error) {

        throw new Error(
            `${filePath}のJSON解析に失敗しました。`
            + ` ${error.message}`
        );

    }


    let questionData;


    /*
     * pandas.to_json(
     *     orient="records"
     * )
     *
     * で作成された配列形式
     */
    if (Array.isArray(jsonData)) {

        questionData = jsonData;

    /*
     * {
     *     "questions": [...]
     * }
     *
     * 形式
     */
    } else if (
        jsonData &&
        Array.isArray(jsonData.questions)
    ) {

        questionData = jsonData.questions;

    } else {

        throw new Error(
            `${filePath}のJSON形式が正しくありません。`
            + " 配列、またはquestions配列が必要です。"
        );

    }


    console.log(
        `[QuestionLoader] ${filePath}: `
        + `${questionData.length}問を読み込みました。`
    );


    return questionData;

}


/**
 * --------------------------------------------------------
 * 複数JSONファイルを読み込み、1つの配列へ統合する
 * --------------------------------------------------------
 */
async function loadMultipleQuestionData(filePaths) {

    /*
     * filePathsが文字列だった場合も
     * 配列へ統一する
     */
    const normalizedPaths =
        normalizeQuestionFilePaths(filePaths);


    console.log(
        "[QuestionLoader] 読込対象:",
        normalizedPaths
    );


    try {

        /*
         * 全JSONファイルを並行して読み込む
         */
        const dataList = await Promise.all(

            normalizedPaths.map(

                filePath =>
                    loadQuestionData(filePath)

            )

        );


        /*
         * [
         *     [問題1, 問題2],
         *     [問題3, 問題4]
         * ]
         *
         * を
         *
         * [
         *     問題1,
         *     問題2,
         *     問題3,
         *     問題4
         * ]
         *
         * へ変換する
         */
        const allQuestions =
            dataList.flat();


        console.log(
            `[QuestionLoader] `
            + `${normalizedPaths.length}ファイル、`
            + `合計${allQuestions.length}問を統合しました。`
        );


        return allQuestions;

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
 * correct_answerを選択肢番号へ変換する
 *
 * 対応形式:
 *
 * 1 / 2 / 3 / 4
 * A / B / C / D
 * option_1 / option_2 / option_3 / option_4
 * 選択肢の文章そのもの
 * --------------------------------------------------------
 */
function getCorrectAnswerNumber(question) {

    const value =
        question.correct_answer;


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
     * 1～4
     */
    if (/^[1-4]$/.test(answer)) {

        return Number(answer);

    }


    /*
     * A～D
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
     * option_1～option_4
     */
    const optionMatch =
        answer.match(/^OPTION_([1-4])$/);


    if (optionMatch) {

        return Number(optionMatch[1]);

    }


    /*
     * 正解選択肢の文章そのものが
     * correct_answerへ設定されている場合
     */
    for (let i = 1; i <= 4; i++) {

        const optionText =
            question[`option_${i}`];


        if (
            optionText !== undefined &&
            optionText !== null &&
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
 * カテゴリ表示文字列を生成する
 *
 * 生成例:
 *
 * 【言語知識】語彙 > 用法
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
 * 問題データを検証する
 * --------------------------------------------------------
 */
function validateQuestion(question, index) {

    const rowNumber =
        index + 1;


    /*
     * 問題データがオブジェクトか確認
     */
    if (
        !question ||
        typeof question !== "object" ||
        Array.isArray(question)
    ) {

        throw new Error(
            `${rowNumber}件目: `
            + "問題データがオブジェクトではありません。"
        );

    }


    /*
     * question_id確認
     */
    if (!question.question_id) {

        throw new Error(
            `${rowNumber}件目: `
            + "question_idがありません。"
        );

    }


    /*
     * question_text確認
     */
    if (!question.question_text) {

        throw new Error(
            `${question.question_id}: `
            + "question_textがありません。"
        );

    }


    /*
     * option_1～option_4確認
     */
    for (let i = 1; i <= 4; i++) {

        if (
            question[`option_${i}`] === undefined ||
            question[`option_${i}`] === null ||
            String(question[`option_${i}`]).trim() === ""
        ) {

            throw new Error(
                `${question.question_id}: `
                + `option_${i}がありません。`
            );

        }

    }


    /*
     * correct_answer確認
     */
    const correctAnswerNumber =
        getCorrectAnswerNumber(question);


    if (!correctAnswerNumber) {

        throw new Error(
            `${question.question_id}: `
            + "correct_answerの値が不正です。"
            + ` value=${question.correct_answer}`
        );

    }


    return correctAnswerNumber;

}


/**
 * --------------------------------------------------------
 * School-LMS標準形式から
 * Quiz Engine形式へ変換する
 * --------------------------------------------------------
 */
function convertQuestionFormat(question, index) {

    const correctAnswerNumber =
        validateQuestion(
            question,
            index
        );


    const explanation =
        question.explanation
            ? String(question.explanation)
            : "";


    const options = [];


    /*
     * Quiz Engine用のoptions配列を作成する
     */
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
     * 既存Quiz Engine用カラムを維持しながら
     * School-LMS標準カラムも保持する
     */
    return {

        /* ===== Existing Quiz Engine ===== */

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
