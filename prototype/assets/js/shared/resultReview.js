/* Result cards shared by drill and Actual. Classic script for the existing drill engine. */
(() => {
    const understandingLabels = ['全然分からない', 'まだ少し分からない', 'だいたい理解できた', '理解できた'];
    function formatText(value) {
        return String(value ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#039;')
            .replace(/&lt;br\s*\/?&gt;/gi, '<br>')
            .replace(/&lt;(\/?)(u|b|strong)&gt;/gi, '<$1$2>').replace(/\n/g, '<br>');
    }

    function updateUnderstanding(index, level) {
        for (let value = 0; value <= 3; value++) {
            const button = document.getElementById(`comp-btn-${index}-${value}`);
            if (!button) continue;
            const selected = level !== null && Number(level) === value;
            button.classList.toggle('selected', selected);
            button.setAttribute('aria-pressed', String(selected));
        }
        if (level !== null) {
            document.getElementById(`review-item-${index}`)?.classList.remove('unentered-comprehension');
            const warning = document.getElementById(`comp-warn-${index}`);
            if (warning) warning.style.display = 'none';
        }
    }

    function toggleUnderstanding(record, index, level) {
        record.understandingLevel = record.understandingLevel === Number(level) ? null : Number(level);
        record.understandingLabel = record.understandingLevel === null ? '未入力' : understandingLabels[record.understandingLevel];
        updateUnderstanding(index, record.understandingLevel);
    }

    function createItem({ index, question, selectedIndex, responseTimeMs, confidence, showConfidence,
        reviewFlag = false, duringExamFlag = false, onReviewFlagChange, onUnderstandingChange }) {
        const selected = Number.isInteger(selectedIndex) ? question.options[selectedIndex] : null;
        const correct = question.options.find(option => option.isCorrect);
        const isCorrect = Boolean(selected?.isCorrect);
        const item = document.createElement('div');
        item.className = 'review-item';
        item.id = `review-item-${index}`;
        const statusClass = isCorrect ? 'review-status-correct' : 'review-status-incorrect';
        const status = isCorrect ? '【正解】' : selected ? '【不正解】' : '【未回答】';
        item.innerHTML = `
            <div class="review-q">Q${index + 1}. ${formatText(question.question)} <span class="${statusClass}">${status}</span></div>
            <div class="review-ans">あなたの回答: <strong>${selected ? formatText(selected.text) : '（未回答）'}</strong> (思考時間: ${(Number(responseTimeMs || 0) / 1000).toFixed(1)}秒) ${showConfidence ? `[自信度: ${formatText(confidence ?? '未記録')}]` : ''}</div>
            ${!isCorrect && correct ? `<div class="review-ans correct-answer">正しい解答: <strong>${formatText(correct.text)}</strong></div>` : ''}
            ${duringExamFlag ? '<div class="review-ans">⚑ 試験中に「あとで確認」を付けた問題</div>' : ''}
            <div class="review-flag-control"><label><input type="checkbox" class="review-flag-cb" data-idx="${index}"> 🚩 この問題を後でもう一度解く (Review Flag)</label></div>
            <div class="review-rationale"><strong>正解の解説:</strong><br>${correct ? formatText(correct.rationale) : '解説はありません。'}
                <div class="understanding-control"><span class="understanding-title">解説の理解度:</span>
                    ${[3, 2, 1, 0].map(level => `<button type="button" class="comp-btn" id="comp-btn-${index}-${level}" aria-pressed="false">${level}. ${understandingLabels[level]}</button>`).join('')}
                    <span class="comp-warning-tag" id="comp-warn-${index}">⚠️ 理解度が未選択です</span>
                </div>
            </div>`;
        const checkbox = item.querySelector('.review-flag-cb');
        checkbox.checked = reviewFlag;
        checkbox.addEventListener('change', () => onReviewFlagChange(checkbox));
        for (const level of [3, 2, 1, 0]) {
            item.querySelector(`#comp-btn-${index}-${level}`).addEventListener('click', () => onUnderstandingChange(level));
        }
        return item;
    }
    window.ResultReview = Object.freeze({ createItem, toggleUnderstanding, updateUnderstanding });
})();
