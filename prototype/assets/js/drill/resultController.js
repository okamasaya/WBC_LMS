/* =========================================================
 * SECTION 08: Exam Finalization / Result Construction
 * File: prototype/assets/js/drill/resultController.js
 * ========================================================= */
function submitExam(isAuto = false) {
    updateElapsedTimeForCurrentQuestion();

    if (!isAuto) {
        const unansweredCount = quizData.filter((_, idx) =>
            !userAnswers[idx]
            || userAnswers[idx].selectedOption === null
            || (appConfig.mode === "practice" && !userAnswers[idx].isConfirmed)
        ).length;

        let confirmMessage = "演習を終了して採点を行いますか？";
        if (unansweredCount > 0) {
            confirmMessage = `まだ未完了（未選択または回答未確定）の問題が ${unansweredCount} 問あります。\n本当に演習を終了して採点を行いますか？`;
        }
        if (!confirm(confirmMessage)) return;
    }

    if (timerInterval) clearInterval(timerInterval);

    examEndTime = Date.now();
    const totalElapsedMs = examEndTime - examStartTime;
    const totalSeconds = Math.floor(totalElapsedMs / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    const totalTimeStr = `${minutes}分${seconds}秒`;

    document.getElementById('exam-container').style.display = 'none';
    document.getElementById('score-container').style.display = 'block';

    let finalScore = 0;
    let answeredCount = 0;
    let mainCatStats = {};

    rawLogArray = [];
    const sessionId = "SESS_" + Date.now();
    const createdAt = new Date().toISOString();
    const dateTimeStr = new Date().toLocaleString();

    const selectedCategoryLevel1 =
        appConfig.mode === "practice"
            ? (document.getElementById("category-lv1-select")?.value || "all")
            : "all";
    const selectedCategoryLevel2 =
        appConfig.mode === "practice"
            ? (document.getElementById("category-lv2-select")?.value || "all")
            : "all";
    const selectedCategoryLevel3 =
        appConfig.mode === "practice"
            ? (document.getElementById("category-lv3-select")?.value || "all")
            : "all";

    const reviewList = document.getElementById('review-list');
    reviewList.innerHTML = '';

    quizData.forEach((question, idx) => {
        const categoryLevel1 = String(question.category_lv1 ?? "");
        const categoryLevel2 = String(question.category_lv2 ?? "");
        const categoryLevel3 = String(question.category_lv3 ?? "");
        const rawCategory = question.category
            ? question.category.toString()
            : buildCategoryLabelFromLevels(categoryLevel1, categoryLevel2, categoryLevel3);

        const catMatch = rawCategory.match(/【(.*?)】/);
        const mainCat = catMatch ? catMatch[1] : (categoryLevel1 || rawCategory);

        if (!mainCatStats[mainCat]) mainCatStats[mainCat] = { total: 0, correct: 0 };
        mainCatStats[mainCat].total++;

        // Unanswered questions must not receive a fabricated answer timestamp.
        const ansObj = userAnswers[idx] || {
            selectedOption: null,
            elapsedTimeMs: 0,
            confidence: "NULL",
            isConfirmed: false,
            answerTimestamp: null
        };

        const selectedIdx = ansObj.selectedOption;
        const selectedOption = selectedIdx !== null ? question.options[selectedIdx] : null;
        const correctOptionIndex = question.options.findIndex(o => o.isCorrect);
        const correctOption = correctOptionIndex >= 0 ? question.options[correctOptionIndex] : null;
        const isAnswered = selectedOption !== null;
        const isCorrect = isAnswered ? Boolean(selectedOption.isCorrect) : false;
        const answerTimeSec = Number((ansObj.elapsedTimeMs / 1000).toFixed(1));
        const answeredAt = isAnswered && ansObj.answerTimestamp ? ansObj.answerTimestamp : null;

        let elapsedTimeSec = null;
        if (answeredAt) {
            const answeredMs = new Date(answeredAt).getTime();
            if (Number.isFinite(answeredMs) && examStartTime > 0) {
                elapsedTimeSec = Number(Math.max(0, (answeredMs - examStartTime) / 1000).toFixed(1));
            }
        }

        if (isAnswered) answeredCount++;
        if (isCorrect) {
            finalScore++;
            mainCatStats[mainCat].correct++;
        }

        const skill = resolveSkillDefinition(question);
        if (!skill) {
            console.warn(
                "[ResultController] Skill_ID を解決できませんでした。",
                {
                    questionId: question.question_id || question.id,
                    examLevel: EXAM_CONTEXT.examLevel,
                    categoryLevel1,
                    categoryLevel2,
                    categoryLevel3
                }
            );
        }

        const numericDifficulty = Number(question.difficulty);
        const difficulty = Number.isFinite(numericDifficulty) ? numericDifficulty : null;
        const confidenceLevel =
            appConfig.mode === "practice"
            && useConfidence
            && ansObj.confidence !== "NULL"
                ? Number(ansObj.confidence)
                : null;

        rawLogArray.push({
            dataSchemaVersion: RAW_DATA_SCHEMA_VERSION,
            resultId: "RESULT_" + Date.now() + "_" + (idx + 1),
            sessionId,
            studentId: "STU-00123",

            examId: EXAM_CONTEXT.examId,
            examType: EXAM_CONTEXT.examType,
            examLevel: EXAM_CONTEXT.examLevel,
            examTitle: EXAM_CONTEXT.examTitle,
            mode: appConfig.mode === "practice" ? "Drill" : "Actual",
            useConfidence: appConfig.mode === "practice" ? useConfidence : null,
            difficultyMode: appConfig.mode === "practice" ? selectedDifficultyMode : "all",

            questionSequence: idx + 1,
            questionId: String(question.question_id || question.id || ""),
            skillId: skill?.skillId || null,
            skillName: skill?.skillName || null,

            categoryLevel1,
            categoryLevel2,
            categoryLevel3,
            categoryLabel: rawCategory,

            difficulty,
            difficultyLabel: getDifficultyLabel(difficulty),
            questionText: String(question.question_text || question.question || ""),

            userAnswerDisplayedPosition: isAnswered ? selectedIdx + 1 : null,
            userAnswerText: selectedOption ? String(selectedOption.text) : null,
            correctAnswerDisplayedPosition: correctOptionIndex >= 0 ? correctOptionIndex + 1 : null,
            correctAnswerText: correctOption ? String(correctOption.text) : null,
            correctAnswerSource: question.correct_answer ?? null,

            isAnswered,
            isCorrect,
            responseTimeMs: Number(ansObj.elapsedTimeMs || 0),
            answerTimeSec,
            elapsedTimeSec,
            answeredAt,

            confidenceLevel,
            confidenceLabel:
                appConfig.mode === "practice" && useConfidence
                    ? getConfidenceLabel(confidenceLevel)
                    : "記録なし",
            understandingLevel: null,
            understandingLabel: "未入力",
            reviewFlag: false,
            duringExamReviewFlag: Boolean(flaggedQuestions[idx]),

            explanation: String(question.explanation || correctOption?.rationale || ""),
            createdAt
        });

        const secStr = answerTimeSec.toFixed(1);
        const item = document.createElement('div');
        item.className = 'review-item';
        item.id = `review-item-${idx}`;
        const statusClass = isCorrect ? 'review-status-correct' : 'review-status-incorrect';
        const statusText = isCorrect ? '【正解】' : (selectedIdx === null ? '【未回答】' : '【不正解】');

        item.innerHTML = `
            <div class="review-q">Q${idx + 1}. ${formatText(question.question)} <span class="${statusClass}">${statusText}</span></div>
            <div class="review-ans">あなたの回答: <strong>${selectedOption ? formatText(selectedOption.text) : '（未回答）'}</strong> (思考時間: ${secStr}秒) ${appConfig.mode === "practice" && useConfidence ? `[自信度: ${ansObj.confidence}]` : ''}</div>
            ${!isCorrect && correctOption ? `<div class="review-ans" style="color: #2b6cb0;">正しい解答: <strong>${formatText(correctOption.text)}</strong></div>` : ''}
            <div style="margin: 10px 0; padding: 6px; background: #f0fdf4; border-radius: 4px; display: inline-block;">
                <label style="cursor: pointer; font-size: 14px; color: #166534; font-weight: bold;">
                    <input type="checkbox" class="review-flag-cb" data-idx="${idx}" onchange="syncReviewFlag(this)"> 🚩 この問題を後でもう一度解く (Review Flag)
                </label>
            </div>
            <div class="review-rationale">
                <strong>正解の解説:</strong><br>${correctOption ? formatText(correctOption.rationale) : '解説はありません。'}

                <div style="margin-top: 12px; padding-top: 8px; border-top: 1px dashed #cbd5e1; font-size: 13px;">
                    <span style="font-weight: bold; color: #475569; margin-right: 8px;">解説の理解度:</span>
                    <button type="button" class="comp-btn" id="comp-btn-${idx}-3" onclick="setComprehension(${idx}, '3')">3. 理解できた</button>
                    <button type="button" class="comp-btn" id="comp-btn-${idx}-2" onclick="setComprehension(${idx}, '2')">2. だいたい理解できた</button>
                    <button type="button" class="comp-btn" id="comp-btn-${idx}-1" onclick="setComprehension(${idx}, '1')">1. まだ少し分からない</button>
                    <button type="button" class="comp-btn" id="comp-btn-${idx}-0" onclick="setComprehension(${idx}, '0')">0. 全然分からない</button>
                    <span class="comp-warning-tag" id="comp-warn-${idx}">⚠️ 理解度が未選択です</span>
                </div>
            </div>
        `;
        reviewList.appendChild(item);
    });

    document.getElementById('final-score').innerText = `${finalScore} / ${quizData.length} 問正解`;
    const scorePercent = quizData.length > 0 ? Math.round((finalScore / quizData.length) * 100) : 0;
    const modeLabel = appConfig.mode === "mock" ? "模擬試験" : "練習ドリル";

    const catSection = document.getElementById('category-score-section');
    const catList = document.getElementById('category-score-list');

    if (appConfig.showCategoryScore !== false && catSection && catList) {
        catList.innerHTML = '';
        for (let cat in mainCatStats) {
            const data = mainCatStats[cat];
            if (data.total === 0) continue;

            const rate = Math.round((data.correct / data.total) * 100);
            const isPass = (data.correct / data.total) >= 0.3;

            const cardClass = isPass ? 'pass' : 'warn';
            const badgeHtml = isPass
                ? '<span class="badge-pass">基準達成</span>'
                : '<span class="badge-warn">足切り注意 (30%未満)</span>';

            const cardHtml = `
                <div class="category-score-card ${cardClass}">
                    <div class="category-name">${formatText(cat)}</div>
                    <div class="category-detail">
                        ${data.correct} / ${data.total} 問 (${rate}%)
                        ${badgeHtml}
                    </div>
                </div>
            `;
            catList.insertAdjacentHTML('beforeend', cardHtml);
        }
        catSection.style.display = 'block';
    } else if (catSection) {
        catSection.style.display = 'none';
    }

    reportBaseText = `演習モード: ${modeLabel}\n実施日時: ${dateTimeStr}\n総実施時間: ${totalTimeStr}\n総合スコア: ${scorePercent}点\n\n■ 分野別正解率\n`;
    for (let cat in mainCatStats) {
        let rate = mainCatStats[cat].total > 0 ? Math.round((mainCatStats[cat].correct / mainCatStats[cat].total) * 100) : 0;
        reportBaseText += `· ${cat}: ${rate}% (${mainCatStats[cat].correct}/${mainCatStats[cat].total})\n`;
    }

    const unansweredQuestions = quizData.length - answeredCount;
    const incorrectCount = answeredCount - finalScore;

    actualSummary = {
        dataSchemaVersion: RAW_DATA_SCHEMA_VERSION,
        sessionId,
        studentId: "STU-00123",

        examId: EXAM_CONTEXT.examId,
        examType: EXAM_CONTEXT.examType,
        examLevel: EXAM_CONTEXT.examLevel,
        examTitle: EXAM_CONTEXT.examTitle,
        mode: appConfig.mode === "practice" ? "Drill" : "Actual",

        useConfidence: appConfig.mode === "practice" ? useConfidence : null,
        difficultyMode: appConfig.mode === "practice" ? selectedDifficultyMode : "all",
        difficultyModeLabel: getDifficultyModeLabel(
            appConfig.mode === "practice" ? selectedDifficultyMode : "all"
        ),
        selectedCategoryLevel1,
        selectedCategoryLevel2,
        selectedCategoryLevel3,

        startAt: new Date(examStartTime).toISOString(),
        endAt: new Date(examEndTime).toISOString(),
        totalTimeSec: Math.floor(totalElapsedMs / 1000),

        totalQuestions: quizData.length,
        answeredQuestions: answeredCount,
        unansweredQuestions,
        correctCount: finalScore,
        incorrectCount,
        wrongCount: quizData.length - finalScore,
        scoreRate: scorePercent,

        sourceQuestionFiles: getConfiguredQuestionSources(),
        createdAt
    };
}

