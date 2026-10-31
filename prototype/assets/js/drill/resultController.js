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
    document.getElementById('exam-container').style.display = 'none';
    document.getElementById('score-container').style.display = 'block';
    const isPractice = appConfig.mode === "practice";
    const data = ResultData.build({
        questions: quizData,
        answers: quizData.map((_, index) => ({
            selected: userAnswers[index]?.selectedOption ?? null,
            elapsedTimeMs: userAnswers[index]?.elapsedTimeMs || 0,
            confidence: userAnswers[index]?.confidence ?? null,
            answeredAt: userAnswers[index]?.answerTimestamp || null,
            flagged: Boolean(flaggedQuestions[index])
        })),
        metadata: {
            ...EXAM_CONTEXT, studentId: "STU-00123", mode: isPractice ? "Drill" : "Actual",
            useConfidence: isPractice ? useConfidence : null,
            difficultyMode: isPractice ? selectedDifficultyMode : "all",
            selectedCategoryLevel1: isPractice ? document.getElementById("category-lv1-select")?.value : "all",
            selectedCategoryLevel2: isPractice ? document.getElementById("category-lv2-select")?.value : "all",
            selectedCategoryLevel3: isPractice ? document.getElementById("category-lv3-select")?.value : "all",
            sourceQuestionFiles: getConfiguredQuestionSources()
        },
        startedAt: examStartTime, endedAt: examEndTime, resolveSkill: resolveSkillDefinition
    });
    rawLogArray = data.records;
    actualSummary = data.summary;
    reportBaseText = data.reportBaseText;
    const finalScore = actualSummary.correctCount;
    const mainCatStats = data.mainCatStats;
    const reviewList = document.getElementById('review-list');
    reviewList.replaceChildren();
    quizData.forEach((question, idx) => {
        const item = ResultReview.createItem({
            index: idx, question,
            selectedIndex: userAnswers[idx]?.selectedOption ?? null,
            responseTimeMs: rawLogArray[idx].responseTimeMs,
            confidence: userAnswers[idx]?.confidence,
            showConfidence: isPractice && useConfidence,
            onReviewFlagChange: checkbox => syncReviewFlag(checkbox),
            onUnderstandingChange: level => setComprehension(idx, level)
        });
        reviewList.appendChild(item);
    });

    document.getElementById('final-score').innerText = `${finalScore} / ${quizData.length} 問正解`;

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

    initializeResultOutput();
}
