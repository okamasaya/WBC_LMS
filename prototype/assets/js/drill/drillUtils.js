/* =========================================================
 * SECTION 02: Common Utilities
 * File: prototype/assets/js/drill/drillUtils.js
 * ========================================================= */
function showToast(message) {
    const toast = document.getElementById("toast-message");
    toast.innerText = message;
    toast.style.display = "block";
    setTimeout(() => { toast.style.opacity = "1"; }, 10);
    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => { toast.style.display = "none"; }, 300);
    }, 2500);
}

function startExamTimer() {
    if (timerInterval) clearInterval(timerInterval);
    updateTimerDisplay();
    timerInterval = setInterval(() => {
        timeRemaining--;
        updateTimerDisplay();
        if (timeRemaining <= 0) {
            clearInterval(timerInterval);
            showToast("制限時間になりました。自動的に採点を行います。");
            setTimeout(() => { submitExam(true); }, 1500);
        }
    }, 1000);
}

function updateTimerDisplay() {
    const minutes = Math.floor(timeRemaining / 60);
    const seconds = timeRemaining % 60;
    document.getElementById("timer").innerText = 
        `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

function formatText(text) {
    if (text === null || text === undefined || text === "") return "";
    let escaped = String(text)
        .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;").replace(/'/g, "&#039;");
    
    escaped = escaped.replace(/&lt;br\s*\/?&gt;/gi, "<br>")
        .replace(/&lt;u&gt;/gi, "<u>").replace(/&lt;\/u&gt;/gi, "</u>")
        .replace(/&lt;b&gt;/gi, "<b>").replace(/&lt;\/b&gt;/gi, "</b>")
        .replace(/&lt;strong&gt;/gi, "<strong>").replace(/&lt;\/strong&gt;/gi, "</strong>")
        .replace(/\n/g, "<br>");
    return escaped;
}


function getDifficultyLabel(difficulty) {
    const value = Number(difficulty);
    if (value === 1 || value === 2) return "基礎";
    if (value === 3) return "標準";
    if (value === 4 || value === 5) return "発展";
    return "未設定";
}

function getDifficultyModeLabel(mode) {
    const labels = {
        all: "すべて",
        easy: "易しい",
        hard: "難しい"
    };
    return labels[mode] || "すべて";
}

function getConfidenceLabel(level) {
    const labels = {
        "1": "自信がある",
        "2": "少し自信がある",
        "3": "やや不安",
        "4": "直感に近い"
    };
    if (level === null || level === undefined || String(level) === "NULL") return "未入力";
    return labels[String(level)] || "未入力";
}

function getUnderstandingLabel(level) {
    const labels = {
        "3": "理解できた",
        "2": "だいたい理解できた",
        "1": "まだ少し分からない",
        "0": "全然分からない"
    };
    if (level === null || level === undefined || String(level) === "NULL") return "未入力";
    return labels[String(level)] || "未入力";
}

function resolveSkillDefinition(question) {
    const lv1 = String(question?.category_lv1 ?? "").trim();
    const lv2 = String(question?.category_lv2 ?? "").trim();
    const lv3 = String(question?.category_lv3 ?? "").trim();

    return SKILL_DEFINITIONS.find(skill =>
        skill.examLevel === EXAM_CONTEXT.examLevel
        && skill.categoryLv1 === lv1
        && skill.categoryLv2 === lv2
        && skill.categoryLv3 === lv3
    ) || null;
}

function getConfiguredQuestionSources() {
    if (typeof CONFIG === "undefined" || !CONFIG) return "";
    if (Array.isArray(CONFIG.questionFiles)) return CONFIG.questionFiles.join(" | ");
    if (typeof CONFIG.questionFile === "string") return CONFIG.questionFile;
    return "";
}

function buildCategoryLabelFromLevels(lv1, lv2, lv3) {
    const parts = [];
    if (lv1) parts.push(String(lv1));
    if (lv2) parts.push(String(lv2));
    if (lv3) parts.push(String(lv3));
    return parts.length > 0 ? parts.join(" > ") : "未分類";
}

function updatePracticeDescription() {
    const description = document.getElementById("description-display");
    const checkbox = document.getElementById("use-confidence-checkbox");
    if (!description || appConfig.mode !== "practice") return;

    const confidenceEnabled = checkbox ? checkbox.checked : true;
    const answerFlowText = confidenceEnabled
        ? "回答選択後に自信度を入力すると、その場で正解と解説が表示されます。"
        : "回答すると、その場で正解と解説が表示されます。";

    description.innerHTML =
        "一問一答（Drill）形式の演習です。"
        + answerFlowText
        + "<br>"
        + "カテゴリ・難易度・問題数を選んで演習できます。"
        + "<br>"
        + "（制限時間なし・解説を読む時間は回答時間に含みません）";
}

function filterQuestionsByDifficulty(questions, difficultyMode) {
    const ranges = {
        easy: { min: 1, max: 3 },
        hard: { min: 3, max: 5 }
    };

    const range = ranges[difficultyMode];
    if (!range) {
        return questions;
    }

    let missingDifficultyCount = 0;

    const filtered = questions.filter(question => {
        const difficulty = Number(question.difficulty);

        if (!Number.isFinite(difficulty)) {
            missingDifficultyCount++;
            return false;
        }

        return difficulty >= range.min
            && difficulty <= range.max;
    });

    if (missingDifficultyCount > 0) {
        console.warn(
            "[ExamController] difficulty が未設定または数値ではない問題を除外しました。",
            { missingDifficultyCount }
        );
    }

    if (filtered.length === 0 && questions.length > 0) {
        console.warn(
            "[ExamController] 難易度条件に一致する問題がありません。question.difficulty の値も確認してください。",
            { difficultyMode, sourceCount: questions.length }
        );
    }

    return filtered;
}


