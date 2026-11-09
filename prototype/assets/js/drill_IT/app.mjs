import { loadBanks, createExercise, MODE_LABELS } from './bank.mjs';
import { DrillSession } from './session.mjs';
import { buildResults, buildReport, exportFile, UNDERSTANDING_LABELS } from './results.mjs';

const $ = id => document.getElementById(id);
let loaded, session, result, finalized;
function element(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
}
function button(text, action, className) {
    const node = element('button', text, className);
    node.type = 'button';
    node.addEventListener('click', action);
    return node;
}
function announce(message) { $('output-status').textContent = message; }
function showError(error) {
    $('description-display').textContent = `開始できません: ${error.message}`;
    $('description-display').setAttribute('role', 'alert');
}
function choices(id, items, value = 'all') {
    $(id).replaceChildren(...items.map(([key, label]) => {
        const option = element('option', label); option.value = key; return option;
    }));
    $(id).value = value;
}
function availableQuestions() {
    return loaded.entries.flatMap(e => e.bank.questions)
        .filter(q => $('chapter-select').value === 'all' || String(q.chapter) === $('chapter-select').value);
}
function refreshCounts() {
    const count = availableQuestions().filter(q => $('topic-select').value === 'all' || q.question_id === $('topic-select').value).length;
    choices('question-count-select', [['all', `全${count}テーマ`], ...[5, 10, 20, 30].filter(n => n < count).map(n => [n, `${n}テーマ`])]);
    $('available-count').textContent = `対象: ${count}テーマ。同じテーマは1回の演習に1問だけ出題します。`;
}
function refreshTopics() {
    choices('topic-select', [['all', 'すべてのテーマ'], ...availableQuestions().map(q => [q.question_id, `第${q.chapter}章 / ${q.topic}`])]);
    refreshCounts();
}
function start() {
    if (!loaded || session?.active) return;
    try {
        const exercise = createExercise(loaded.entries, {
            mode: $('mode-select').value,
            chapter: $('chapter-select').value === 'all' ? 'all' : Number($('chapter-select').value),
            questionId: $('topic-select').value,
            count: $('question-count-select').value === 'all' ? 'all' : Number($('question-count-select').value)
        });
        session = new DrillSession(exercise, { useConfidence: $('use-confidence-checkbox').checked });
        $('start-container').hidden = true;
        $('exam-container').hidden = false;
        renderQuestion();
        $('progress').focus();
    } catch (error) { showError(error); }
}

function explanations(q) {
    const section = element('div', undefined, 'it-explanations');
    section.append(element('h4', 'テーマの解説'), element('p', q.explanation, 'it-plain'));
    const list = element('ol');
    q.options.forEach(o => {
        const li = element('li');
        li.append(element('strong', `内容は${o.pool === 'appropriate' ? '適切' : '不適切'}${o.isCorrect ? ' ／ この回に選ぶ正解' : ''}`),
            element('p', o.text, 'it-plain'), element('p', o.rationale, 'it-plain'));
        list.append(li);
    });
    section.append(list);
    return section;
}
function renderQuestion() {
    const q = session.exercise.questions[session.index], a = session.currentAnswer;
    $('progress').textContent = `問題 ${session.index + 1} / ${session.answers.length}`;
    $('category-display').textContent = `${q.category} ／ ${MODE_LABELS[q.questionMode]}`;
    $('question-text').textContent = q.question;
    $('options-container').replaceChildren(...q.options.map((o, i) => {
        const node = button('', () => {
            session.select(i);
            renderQuestion();
            if (!session.currentAnswer.confirmed) $('confidence-panel').querySelector('button').focus();
            else $('feedback-title').focus();
        }, 'option-btn');
        node.dataset.optionId = o.optionId;
        node.setAttribute('aria-pressed', String(a.selected === i));
        node.append(element('span', String(i + 1), 'option-num'), element('span', o.text, 'option-text'));
        node.classList.toggle('selected', a.selected === i);
        if (a.confirmed) {
            node.disabled = true;
            node.classList.toggle('correct', o.isCorrect);
            node.classList.toggle('incorrect', a.selected === i && !o.isCorrect);
        }
        return node;
    }));
    $('confidence-panel').hidden = !session.useConfidence || a.selected === null || a.confirmed;
    $('instant-feedback').hidden = !a.confirmed;
    $('instant-feedback').replaceChildren();
    if (a.confirmed) {
        const heading = element('h3', q.options[a.selected].isCorrect ? '正解です' : '不正解です');
        heading.id = 'feedback-title'; heading.tabIndex = -1;
        const correct = q.options.findIndex(o => o.isCorrect);
        $('instant-feedback').append(heading, element('p', `この回の正解は ${correct + 1}. ${q.options[correct].text}`, 'it-plain'), explanations(q));
    }
    $('previous-question').disabled = session.index === 0;
    $('next-question').disabled = session.index === session.answers.length - 1;
    $('answer-status').textContent = a.confirmed
        ? `回答確定${session.useConfidence ? ` ／ 自信度 ${a.confidence}` : ''}。解説を読む時間は回答時間に含みません。`
        : a.selected === null ? '選択肢を選んでください。' : '自信度を選ぶと回答が確定します。確定前は選択肢を変更できます。';
}
function move(offset) {
    session.move(session.index + offset);
    renderQuestion();
    $('progress').focus();
}
function finish() {
    if (!session?.active) return;
    // Account for the confirmation dialog time just as for the rest of the active question.
    const pending = session.answers.filter(a => !a.confirmed).length;
    if (!window.confirm(`${pending ? `未完了の問題が ${pending} 問あります。未確定の回答は未回答として集計します。\n` : ''}演習を終了して採点しますか？`)) return;
    session.finish();
    // getRandomValues is available on ordinary HTTP as well as secure origins.
    const sessionId = `IT_${Array.from(crypto.getRandomValues(new Uint8Array(16)), value => value.toString(16).padStart(2, '0')).join('')}`;
    result = buildResults(session, loaded.config.title, { ResultData: window.ResultData, sessionId });
    $('exam-container').hidden = true;
    $('score-container').hidden = false;
    $('final-score').textContent = `${result.summary.correctCount} / ${result.summary.totalQuestions} 問正解（未回答 ${result.summary.unansweredQuestions} 問）`;
    const byChapter = Object.entries(result.mainCatStats).map(([chapter, stats]) => `${chapter}: ${stats.correct}/${stats.total}問`);
    $('category-score-list').textContent = byChapter.join(' ／ ');
    $('review-list').replaceChildren(...session.exercise.questions.map((q, i) => reviewItem(q, i)));
    $('result-heading').focus();
}
function invalidate() {
    if (!finalized) return;
    finalized = null;
    $('output-section').hidden = true;
    $('report-text').value = '';
    announce('理解度・復習フラグが変更されました。レポートを再生成してください。');
}
function reviewItem(q, index) {
    const r = result.records[index], item = element('article', undefined, 'review-item');
    item.id = `review-item-${index}`;
    item.append(element('h3', `問${index + 1} ／ ${MODE_LABELS[q.questionMode]} ／ ${r.isCorrect ? '正解' : r.isAnswered ? '不正解' : '未回答'}`),
        element('p', q.question, 'review-q it-plain'),
        element('p', `あなたの回答: ${r.userAnswerText ?? '未回答'}\n回答時間: ${r.answerTimeSec}秒${session.useConfidence ? ` ／ 自信度: ${r.confidenceLevel ?? '未記録'}` : ''}`, 'it-plain'), explanations(q));
    const flag = document.createElement('input'); flag.type = 'checkbox'; flag.className = 'review-flag-cb';
    const flagLabel = element('label', ' この問題をもう一度復習する'); flagLabel.prepend(flag);
    flag.addEventListener('change', () => { r.reviewFlag = flag.checked; invalidate(); });
    item.append(flagLabel);
    const field = element('fieldset', undefined, 'understanding-control');
    field.append(element('legend', '解説を読んだ後の理解度（自己申告）'));
    const controls = [3, 2, 1, 0].map(level => {
        const node = button(`${level}. ${UNDERSTANDING_LABELS[level]}`, () => {
            r.understandingLevel = r.understandingLevel === level ? null : level;
            r.understandingLabel = UNDERSTANDING_LABELS[r.understandingLevel] ?? '未入力';
            controls.forEach((b, j) => {
                const selected = r.understandingLevel === [3, 2, 1, 0][j];
                b.classList.toggle('selected', selected); b.setAttribute('aria-pressed', String(selected));
            });
            invalidate();
        }, 'comp-btn');
        node.setAttribute('aria-pressed', 'false');
        return node;
    });
    field.append(...controls);
    item.append(field);
    return item;
}
function finalize() {
    if (!result) return;
    const missing = result.records.flatMap((r, i) => r.understandingLevel === null ? [i] : []);
    if (missing.length && !window.confirm(`解説の理解度が未入力の問題が ${missing.length} 問あります。このまま確定しますか？`)) {
        $(`review-item-${missing[0]}`).scrollIntoView({ behavior: 'smooth', block: 'center' });
        announce('解説の理解度を確認してください。'); return;
    }
    finalized = structuredClone(result);
    $('report-text').value = buildReport(finalized, window.ResultReport);
    $('output-section').hidden = false;
    announce('レポートとIT演習ログを確定しました。');
}
function download(type) {
    if (!finalized) return;
    const file = exportFile(finalized, type, window.ResultReport);
    const blob = new Blob([...(type === 'json' ? [] : ['\uFEFF']), file.content], { type: `${file.mime};charset=utf-8` });
    const url = URL.createObjectURL(blob), link = element('a');
    link.href = url; link.download = file.name;
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    announce(`${file.name} を保存しました。`);
}
async function copyReport() {
    if (!finalized) return;
    try {
        await navigator.clipboard.writeText($('report-text').value);
        announce('レポートをコピーしました。');
    } catch {
        $('report-text').focus(); $('report-text').select();
        announce('レポートを選択しました。手動でコピーしてください。');
    }
}

$('start-exam').addEventListener('click', start);
$('chapter-select').addEventListener('change', refreshTopics);
$('topic-select').addEventListener('change', refreshCounts);
$('previous-question').addEventListener('click', () => move(-1));
$('next-question').addEventListener('click', () => move(1));
$('finish-exam').addEventListener('click', finish);
document.querySelectorAll('[data-confidence]').forEach(node => node.addEventListener('click', () => {
    session.confirm(Number(node.dataset.confidence)); renderQuestion(); $('feedback-title').focus();
}));
$('generate-report').addEventListener('click', finalize);
$('copy-report').addEventListener('click', copyReport);
document.querySelectorAll('[data-download]').forEach(node => node.addEventListener('click', () => download(node.dataset.download)));
$('restart').addEventListener('click', () => window.location.reload());
window.addEventListener('beforeunload', event => { if (session?.active) { event.preventDefault(); event.returnValue = ''; } });

try {
    if (location.protocol === 'file:') throw new Error('HTTPサーバー経由で開いてください');
    loaded = await loadBanks(new URLSearchParams(location.search).get('conf') || document.documentElement.dataset.config, location.href);
    document.title = `${loaded.config.title} | IT Drill`;
    $('title-display').textContent = loaded.config.title;
    const chapters = [...new Set(loaded.entries.flatMap(e => e.bank.questions.map(q => q.chapter)))].sort((a, b) => a - b);
    choices('chapter-select', [['all', 'すべての章'], ...chapters.map(n => [n, `第${n}章`])]);
    refreshTopics();
    $('description-display').textContent = '4択の練習ドリルです。選択後（自信度ありの場合は自信度入力後）に回答を確定し、正解と各候補の解説を表示します。';
    $('start-exam').disabled = false;
} catch (error) { showError(error); }
