/* Shared final review -> report / CSV / clipboard workflow. */
(() => {
    function mount({ container, getData, notify }) {
        container.innerHTML = `
            <section class="result-output-panel" aria-label="演習ログの確定とレポート出力">
                <h3>演習ログの確定とレポート出力</h3>
                <p>解説の理解度選択が完了したら、以下のボタンを押して分析レポートおよび各種ログデータを確定生成してください。</p>
                <button type="button" id="generate-report" class="result-generate">📊 レポート・ログデータを確定して生成</button>
                <p class="result-output-status" role="status"></p>
                <div id="output-section" style="display: none;">
                    <div class="result-output-actions">
                        <button type="button" data-action="copy">AIレポートをコピー</button>
                        <button type="button" data-action="raw">統合Raw CSV (GAS/Excel用)</button>
                        <button type="button" data-action="questions">QuestionResult.csv</button>
                        <button type="button" data-action="session">Session.csv</button>
                    </div>
                    <label for="report-text">生成AIに渡すレポート</label>
                    <textarea id="report-text" class="report-area" readonly></textarea>
                </div>
            </section>`;
        let snapshot = null;
        const output = container.querySelector('#output-section');
        const text = container.querySelector('#report-text');
        const status = container.querySelector('.result-output-status');
        const announce = message => { status.textContent = message; notify?.(message); };
        function invalidate() {
            if (!snapshot) return;
            snapshot = null;
            output.style.display = 'none';
            text.value = '';
            announce('理解度・復習フラグが変更されました。レポート・ログデータを再生成してください。');
        }
        function finalize() {
            const data = getData();
            if (!data?.summary?.sessionId || !data.records.length) return false;
            const missing = [];
            data.records.forEach((record, index) => {
                const isMissing = record.understandingLevel == null;
                document.getElementById(`review-item-${index}`)?.classList.toggle('unentered-comprehension', isMissing);
                const warning = document.getElementById(`comp-warn-${index}`);
                if (warning) warning.style.display = isMissing ? 'inline' : 'none';
                if (isMissing) missing.push(index + 1);
            });
            if (missing.length && !window.confirm(`【未入力の確認】\n以下の設問で「解説の理解度」が未選択です。\n\n対象: 問 ${missing.join(', ')}\n\nこのまま未入力の状態で確定・生成しますか？\n（[キャンセル] を押すと未入力の設問へ移動します）`)) {
                document.getElementById(`review-item-${missing[0] - 1}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                announce(`問 ${missing[0]} の解説理解度を選択してください。`);
                return false;
            }
            snapshot = structuredClone(data);
            text.value = window.ResultReport.buildReport(snapshot);
            output.style.display = 'block';
            announce('レポートとログデータを確定・生成しました。');
            output.scrollIntoView({ behavior: 'smooth', block: 'start' });
            return true;
        }
        function download(type) {
            if (!snapshot) { announce('先にレポート・ログデータを確定して生成してください。'); return; }
            const file = window.ResultReport.exportCsv(snapshot, type);
            const blob = new Blob([new Uint8Array([0xEF, 0xBB, 0xBF]), file.content], { type: 'text/csv;charset=utf-8;' });
            const objectURL = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = objectURL; link.download = file.name;
            document.body.append(link); link.click(); link.remove();
            setTimeout(() => URL.revokeObjectURL(objectURL), 1000);
            announce(`${file.name} をダウンロードしました。`);
        }
        async function copy() {
            if (!snapshot) { announce('先にレポート・ログデータを確定して生成してください。'); return false; }
            try {
                try {
                    if (!navigator.clipboard?.writeText) throw new Error('clipboard unavailable');
                    await navigator.clipboard.writeText(text.value);
                } catch {
                    text.focus(); text.select();
                    if (!document.execCommand('copy')) throw new Error('copy failed');
                }
                announce('レポートをクリップボードにコピーしました。');
                return true;
            } catch {
                text.focus(); text.select();
                announce('自動コピーができませんでした。選択されたレポートを手動でコピーしてください。');
                return false;
            }
        }
        container.querySelector('#generate-report').addEventListener('click', finalize);
        container.querySelector('[data-action="copy"]').addEventListener('click', copy);
        for (const type of ['raw', 'questions', 'session']) container.querySelector(`[data-action="${type}"]`).addEventListener('click', () => download(type));
        return Object.freeze({ finalize, invalidate, download, copy });
    }
    window.ResultOutput = Object.freeze({ mount });
})();
