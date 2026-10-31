/* JSON-driven page adapter. Legacy separete_drill continues to use config.js / drillConfig.js. */
const CONFIG = {};
const appConfig = { mode: 'practice', layout: 'normal', showCategoryScore: true };
const EXAM_CONTEXT = {};
const SKILL_DEFINITIONS = [];
const CATEGORY_ORDER = { lv2: {}, lv3: {} };
const RAW_DATA_SCHEMA_VERSION = '2.0.0';
window.DrillPageReady = (async () => {
    const config = await ExamConfig.load('drill', document.documentElement.dataset.config);
    CONFIG.questionFiles = config.questionFiles;
    CONFIG.sourceQuestionFiles = config.sourceQuestionFiles;
    Object.assign(EXAM_CONTEXT, { examId: config.examId, examType: config.examType, examLevel: config.examLevel, examTitle: config.examTitle || config.title });
    Object.assign(appConfig, { shuffleQuestions: config.shuffleQuestions, shuffleOptions: config.shuffleOptions, studentId: config.studentId ?? null });
    config.categories.forEach(c => {
        SKILL_DEFINITIONS.push({ ...c, examLevel: config.examLevel });
        const lv2 = CATEGORY_ORDER.lv2[c.categoryLv1] ||= [];
        if (!lv2.includes(c.categoryLv2)) lv2.push(c.categoryLv2);
        const lv3 = (CATEGORY_ORDER.lv3[c.categoryLv1] ||= {})[c.categoryLv2] ||= [];
        lv3.push(c.categoryLv3);
    });
    document.title = `${config.title} | Drill`;
    document.getElementById('title-display').textContent = config.title;
    document.getElementById('exam-subtitle').textContent = `${config.examTitle || config.examId} ／ 練習ドリル`;
    const populate = (id, values, selected, labels) => {
        const select = document.getElementById(id);
        select.replaceChildren(...values.map(value => {
            const option = document.createElement('option');
            option.value = value;
            option.textContent = labels?.[value] || (value === 'all' ? '全問' : `${value}問`);
            return option;
        }));
        select.value = selected;
    };
    populate('question-count-select', config.questionCounts, config.defaultQuestionCount);
    populate('difficulty-select', config.difficultyModes, config.defaultDifficultyMode, {all:'すべて',easy:'易しい問題を中心',hard:'難しい問題を中心'});
    const confidence = document.getElementById('use-confidence-checkbox');
    confidence.checked = config.recordConfidence;
    confidence.disabled = !config.allowConfidenceToggle;
    document.getElementById('confidence-setting').hidden = !config.allowConfidenceToggle;
    window.loadDrillQuestionSet = async () => (await loadMultipleQuestionData(CONFIG.questionFiles)).map(convertQuestionFormat);
    window.prepareDrillQuestions = questions => {
        const allowed = new Set(config.categories.map(ExamConfig.categoryKey));
        const filtered = questions.filter(q => allowed.has(ExamConfig.categoryKey({categoryLv1:q.category_lv1,categoryLv2:q.category_lv2,categoryLv3:q.category_lv3})));
        const ids = new Set();
        for (const q of filtered) {
            if (ids.has(q.id)) throw new Error(`問題IDが重複しています: ${q.id}`);
            ids.add(q.id);
        }
        return filtered;
    };
    window.configureDrillControls = () => {
        document.getElementById('category-select-container').style.display = config.allowCategorySelection ? 'block' : 'none';
    };
})();
// Attach a rejection handler immediately; app.js displays the actual error after load.
window.DrillPageReady.catch(() => {});
