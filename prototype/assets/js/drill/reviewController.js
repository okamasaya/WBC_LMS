/* =========================================================
 * SECTION 09: Review / Understanding
 * File: prototype/assets/js/drill/reviewController.js
 * ========================================================= */
function syncReviewFlag(checkbox) {
    const idx = parseInt(checkbox.getAttribute('data-idx'));
    if (rawLogArray[idx]) {
        rawLogArray[idx].reviewFlag = checkbox.checked;
    }
}

function setComprehension(idx, level) {
    if (!rawLogArray[idx]) return;

    ResultReview.toggleUnderstanding(rawLogArray[idx], idx, level);
}

async function finalizeAndGenerateReport() {
    
    const unenteredIndices = [];
    rawLogArray.forEach((item, idx) => {
        const reviewItem = document.getElementById(`review-item-${idx}`);
        const warnTag = document.getElementById(`comp-warn-${idx}`);
        
        if (item.understandingLevel === null) {
            unenteredIndices.push(idx + 1);
            if (reviewItem) reviewItem.classList.add('unentered-comprehension');
            if (warnTag) warnTag.style.display = "inline";
        } else {
            if (reviewItem) reviewItem.classList.remove('unentered-comprehension');
            if (warnTag) warnTag.style.display = "none";
        }
    });

    
    if (unenteredIndices.length > 0) {
        const qListStr = unenteredIndices.join(", ");
        const proceed = confirm(
            `【未入力の確認】\n以下の設問で「解説の理解度」が未選択です。\n\n対象: 問 ${qListStr}\n\nこのまま未入力の状態で確定・生成しますか？\n（[キャンセル] を押すと未入力の設問へ移動します）`
        );

        if (!proceed) {
            const firstUnenteredIdx = unenteredIndices[0] - 1;
            const targetElem = document.getElementById(`review-item-${firstUnenteredIdx}`);
            if (targetElem) {
                targetElem.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            showToast(`問 ${unenteredIndices[0]} の解説理解度を選択してください。`);
            return; 
        }
    }

    
    buildReportPayloadText();
    document.getElementById("output-section").style.display = "block";
    showToast("レポートとログデータを確定・生成しました。");

    document.getElementById("output-section").scrollIntoView({ behavior: 'smooth' });
}

