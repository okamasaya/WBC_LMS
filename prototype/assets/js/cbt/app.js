import { validateConfig, selectQuestions, scoreQuestions } from './examCore.js';

const $ = id => document.getElementById(id);
const confidenceLabels = ['自信がある', '少し自信がある', '怪しい', '直感！'];
let config, bank, questions, answers, current = 0;
let resultData, resultOutputController;
let active = false, startedAt, deadline, interval, visitedAt;
const configURL = new URL('./conf_JLPT_N2_LK.json', window.location.href);

// Keep the inline formatting used by the question bank, without accepting active HTML.
function formatted(target, value) {
    const template = document.createElement('template');
    template.innerHTML = String(value ?? '');
    const allowed = new Set(['U', 'BR', 'RUBY', 'RT', 'RP', 'B', 'STRONG', 'EM', 'I', 'SUB', 'SUP']);
    function copy(node, parent) {
        if (node.nodeType === Node.TEXT_NODE) parent.append(document.createTextNode(node.textContent));
        else if (node.nodeType === Node.ELEMENT_NODE) {
            if (['SCRIPT', 'STYLE', 'IFRAME', 'OBJECT'].includes(node.tagName)) return;
            const next = allowed.has(node.tagName) ? document.createElement(node.tagName) : parent;
            if (next !== parent) parent.append(next);
            for (const child of node.childNodes) copy(child, next);
        }
    }
    target.replaceChildren();
    for (const child of template.content.childNodes) copy(child, target);
}

function duration(seconds) {
    seconds = Math.max(0, Math.ceil(seconds));
    return `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
}

async function initialize() {
    try {
        const response = await fetch(configURL, { cache: 'no-store' });
        if (!response.ok) throw new Error(`設定ファイルを取得できません (HTTP ${response.status})。`);
        config = validateConfig(await response.json());
        $('exam-title').textContent = config.title;
        document.title = `${config.title} | 開発中・JLPT N2 CBT`;
        const raw = (await Promise.all(config.questionFiles.map(path => window.loadQuestionData(new URL(path, configURL).href)))).flat();
        // Reuse the same validation and conversion as separete_drill, without loading its practice settings.
        bank = raw.map((q, i) => window.convertQuestionFormat(q, i));
        const preview = selectQuestions(config, bank);
        $('summary').textContent = `${preview.length}問 ／ 制限時間 ${config.timeLimitMinutes}分`;
        for (const c of config.categories.filter(c => c.count > 0)) {
            const item = document.createElement('li');
            item.textContent = `${c.categoryLv2}・${c.categoryLv3}：${c.count}問`;
            $('category-summary').append(item);
        }
        $('confidence-instruction').hidden = !config.recordConfidence;
        $('load-status').textContent = '準備ができました。';
        $('exam-info').hidden = false;
    } catch (error) {
        $('load-status').textContent = '試験を開始できません。';
        $('error').textContent = `${error.message}\n設定・問題ファイルを確認して再読み込みしてください。HTMLはHTTPサーバーから開いてください。`;
        $('error').hidden = false;
    }
}

function start() {
    if (active || !bank) return;
    questions = selectQuestions(config, bank);
    answers = questions.map(() => ({ selected: null, confidence: null, flagged: false, elapsedTimeMs: 0, answeredAt: null }));
    current = 0;
    startedAt = Date.now();
    deadline = startedAt + config.timeLimitMinutes * 60000;
    visitedAt = startedAt;
    active = true;
    $('start-screen').hidden = true;
    $('exam-screen').hidden = false;
    $('palette').replaceChildren();
    questions.forEach((_, i) => {
        const button = document.createElement('button');
        button.textContent = i + 1;
        button.addEventListener('click', () => navigate(i));
        $('palette').append(button);
    });
    renderQuestion();
    tick();
    interval = window.setInterval(tick, 250);
}

// A deadline, rather than a decrementing counter, also accounts for background tabs.
function canInteract() {
    if (!active) return false;
    if (Date.now() >= deadline) { finish(true); return false; }
    return true;
}

function tick() {
    if (!active) return;
    $('timer').textContent = duration((deadline - Date.now()) / 1000);
    $('timer').classList.toggle('urgent', deadline - Date.now() <= 60000);
    if (Date.now() >= deadline) finish(true);
}

function recordVisitTime() {
    const now = Math.min(Date.now(), deadline);
    answers[current].elapsedTimeMs += Math.max(0, now - visitedAt);
    visitedAt = now;
}

function navigate(index) {
    if (!canInteract() || index < 0 || index >= questions.length) return;
    recordVisitTime();
    current = index;
    renderQuestion();
}

function optionRadio(name, value, label, checked, onChange) {
    const wrapper = document.createElement('label');
    wrapper.className = 'choice';
    const radio = document.createElement('input');
    radio.type = 'radio'; radio.name = name; radio.value = value; radio.checked = checked;
    radio.addEventListener('change', onChange);
    const text = document.createElement('span');
    formatted(text, label);
    wrapper.append(radio, text);
    return wrapper;
}

function renderQuestion() {
    const q = questions[current], answer = answers[current];
    $('progress').textContent = `問題 ${current + 1} / ${questions.length}`;
    $('question-heading').textContent = `問題 ${current + 1}`;
    $('category').textContent = `${q.category_lv2}・${q.category_lv3}`;
    formatted($('question-text'), q.question);
    $('option-list').replaceChildren();
    q.options.forEach((option, i) => {
        const choice = optionRadio('answer', i, `${i + 1}. ${option.text}`, answer.selected === i, () => {
            if (!canInteract()) return;
            answer.selected = i;
            answer.answeredAt = new Date().toISOString();
            // Changing an answer invalidates the confidence recorded for the old answer.
            answer.confidence = null;
            renderConfidence();
            $('clear-answer').disabled = false;
            renderPalette();
        });
        $('option-list').append(choice);
    });
    $('clear-answer').disabled = answer.selected === null;
    renderConfidence();
    $('previous').disabled = current === 0;
    $('next').disabled = current === questions.length - 1;
    $('flag').setAttribute('aria-pressed', String(answer.flagged));
    $('flag').textContent = answer.flagged ? '⚑ 確認フラグを解除' : '⚑ あとで確認';
    renderPalette();
    $('question-heading').focus();
}

function renderConfidence() {
    $('confidence').hidden = !config.recordConfidence;
    $('confidence-options').replaceChildren();
    if (!config.recordConfidence) return;
    confidenceLabels.forEach((label, i) => {
        const choice = optionRadio('confidence', i + 1, `${i + 1}. ${label}`, answers[current].confidence === i + 1, () => {
            if (canInteract()) answers[current].confidence = i + 1;
        });
        choice.querySelector('input').disabled = answers[current].selected === null;
        $('confidence-options').append(choice);
    });
}

function counts() {
    return { answered: answers.filter(a => a.selected !== null).length, flagged: answers.filter(a => a.flagged).length };
}

function renderPalette() {
    const { answered, flagged } = counts();
    $('counts').textContent = `回答 ${answered} / ${questions.length} ／ 未回答 ${questions.length - answered} ／ ⚑ ${flagged}`;
    [...$('palette').children].forEach((button, i) => {
        const answer = answers[i];
        button.classList.toggle('answered', answer.selected !== null);
        button.classList.toggle('flagged', answer.flagged);
        if (i === current) button.setAttribute('aria-current', 'step');
        else button.removeAttribute('aria-current');
        button.setAttribute('aria-label', `問題 ${i + 1}、${answer.selected === null ? '未回答' : '回答済み'}${answer.flagged ? '、あとで確認' : ''}`);
    });
}

function finish(timedOut) {
    if (!active) return;
    if (!timedOut && Date.now() >= deadline) timedOut = true;
    recordVisitTime();
    active = false;
    clearInterval(interval);
    if ($('finish-dialog').open) $('finish-dialog').close();
    $('exam-screen').hidden = true;
    $('result-screen').hidden = false;
    const endedAt = Math.min(Date.now(), deadline);
    resultData = window.ResultData.build({
        questions, answers, startedAt, endedAt,
        metadata: {
            examId: config.examId, examType: config.examType || null,
            examLevel: config.examLevel || null, examTitle: config.examTitle || config.title,
            studentId: config.studentId ?? null, mode: 'Actual',
            useConfidence: config.recordConfidence, difficultyMode: 'all',
            sourceQuestionFiles: config.questionFiles.join(' | ')
        },
        resolveSkill: question => config.categories.find(category =>
            category.categoryLv1 === question.category_lv1 && category.categoryLv2 === question.category_lv2 && category.categoryLv3 === question.category_lv3)
    });
    const results = scoreQuestions(questions, answers);
    const correct = results.filter(r => r.correct).length;
    $('finish-reason').textContent = timedOut ? '制限時間になったため、自動で終了・採点しました。' : '回答を確定し、採点しました。';
    $('score').textContent = `${correct} / ${questions.length}問 正解（${Math.round(correct / questions.length * 100)}%）`;
    $('elapsed').textContent = `所要時間 ${duration((Math.min(Date.now(), deadline) - startedAt) / 1000)} ／ 未回答 ${questions.length - counts().answered}問 ／ あとで確認 ${counts().flagged}問`;
    for (const c of config.categories.filter(c => c.count > 0)) {
        const group = results.filter(r => r.question.category_lv1 === c.categoryLv1 && r.question.category_lv2 === c.categoryLv2 && r.question.category_lv3 === c.categoryLv3);
        const n = group.filter(r => r.correct).length;
        const row = document.createElement('tr');
        for (const text of [`${c.categoryLv2}・${c.categoryLv3}`, `${n} / ${group.length}`, `${Math.round(n / group.length * 100)}%`]) {
            const cell = document.createElement('td'); cell.textContent = text; row.append(cell);
        }
        $('category-results').append(row);
    }
    results.forEach(({ question: q, answer }, i) => {
        const record = resultData.records[i];
        const review = window.ResultReview.createItem({
            index: i,
            question: q,
            selectedIndex: answer.selected,
            responseTimeMs: answer.elapsedTimeMs,
            confidence: answer.confidence,
            showConfidence: config.recordConfidence,
            duringExamFlag: answer.flagged,
            reviewFlag: record.reviewFlag,
            onReviewFlagChange: checkbox => { record.reviewFlag = checkbox.checked; resultOutputController.invalidate(); },
            onUnderstandingChange: level => { window.ResultReview.toggleUnderstanding(record, i, level); resultOutputController.invalidate(); }
        });
        $('reviews').append(review);
    });
    resultOutputController = window.ResultOutput.mount({ container: $('result-output'), getData: () => resultData });
    $('result-heading').focus();
}

$('start').addEventListener('click', start);
$('previous').addEventListener('click', () => navigate(current - 1));
$('next').addEventListener('click', () => navigate(current + 1));
$('flag').addEventListener('click', () => {
    if (!canInteract()) return;
    answers[current].flagged = !answers[current].flagged;
    $('flag').setAttribute('aria-pressed', String(answers[current].flagged));
    $('flag').textContent = answers[current].flagged ? '⚑ 確認フラグを解除' : '⚑ あとで確認';
    renderPalette();
});
$('clear-answer').addEventListener('click', () => {
    if (!canInteract()) return;
    answers[current].selected = null; answers[current].confidence = null; answers[current].answeredAt = null;
    renderQuestion();
});
$('finish').addEventListener('click', () => {
    if (!canInteract()) return;
    const { answered, flagged } = counts();
    $('finish-summary').textContent = `未回答 ${questions.length - answered}問 ／ あとで確認 ${flagged}問`;
    $('finish-dialog').showModal();
});
$('cancel-finish').addEventListener('click', () => $('finish-dialog').close());
$('confirm-finish').addEventListener('click', () => finish(false));
$('restart').addEventListener('click', () => window.location.reload());
window.addEventListener('beforeunload', event => {
    if (active) { event.preventDefault(); event.returnValue = ''; }
});
document.addEventListener('visibilitychange', tick);
initialize();
