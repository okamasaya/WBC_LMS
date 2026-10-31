// Pure configuration, selection and scoring logic. No changes to the drill engine.
export function validateConfig(config) {
    const fail = message => { throw new Error(`試験設定: ${message}`); };
    if (!config || config.schemaVersion !== 1) fail('schemaVersion は 1 が必要です。');
    if (typeof config.title !== 'string' || !config.title.trim()) fail('title が必要です。');
    if (typeof config.examId !== 'string' || !config.examId.trim()) fail('examId が必要です。');
    if (!Number.isFinite(config.timeLimitMinutes) || config.timeLimitMinutes <= 0 || config.timeLimitMinutes > 1440) fail('timeLimitMinutes は0より大きく1440以下の数値にしてください。');
    for (const key of ['recordConfidence', 'shuffleQuestionsWithinCategory', 'shuffleOptions']) {
        if (typeof config[key] !== 'boolean') fail(`${key} は true / false を指定してください。`);
    }
    if (!Array.isArray(config.questionFiles) || !config.questionFiles.length || config.questionFiles.some(p => typeof p !== 'string' || !p.trim())) fail('questionFiles に問題ファイルを指定してください。');
    if (new Set(config.questionFiles).size !== config.questionFiles.length) fail('questionFiles が重複しています。');
    if (!Array.isArray(config.categories) || !config.categories.length) fail('categories が必要です。');
    const keys = new Set();
    for (const category of config.categories) {
        if (!category || ['categoryLv1', 'categoryLv2', 'categoryLv3'].some(k => typeof category[k] !== 'string' || !category[k].trim())) fail('各カテゴリの Lv1 / Lv2 / Lv3 を指定してください。');
        if (!Number.isSafeInteger(category.count) || category.count < 0) fail('count は0以上の整数にしてください。');
        const key = categoryKey(category);
        if (keys.has(key)) fail('同じカテゴリが重複しています。');
        keys.add(key);
    }
    if (!config.categories.some(c => c.count > 0)) fail('1問以上出題してください。');
    return config;
}

export function categoryKey(c) {
    return JSON.stringify([c.categoryLv1, c.categoryLv2, c.categoryLv3]);
}

export function shuffled(items, random = Math.random) {
    const copy = [...items];
    for (let i = copy.length - 1; i > 0; i--) {
        const j = Math.floor(random() * (i + 1));
        [copy[i], copy[j]] = [copy[j], copy[i]];
    }
    return copy;
}

export function selectQuestions(config, questions, random = Math.random) {
    validateConfig(config);
    const ids = new Set();
    for (const q of questions) {
        if (!q.id || ids.has(q.id)) throw new Error(`問題IDが空、または重複しています: ${q.id}`);
        ids.add(q.id);
    }
    return config.categories.flatMap(c => {
        const pool = questions.filter(q => q.category_lv1 === c.categoryLv1 && q.category_lv2 === c.categoryLv2 && q.category_lv3 === c.categoryLv3);
        if (pool.length < c.count) throw new Error(`${c.categoryLv2}・${c.categoryLv3}: 指定 ${c.count}問に対して ${pool.length}問しかありません。`);
        const selected = config.shuffleQuestionsWithinCategory ? shuffled(pool, random) : pool;
        return selected.slice(0, c.count).map(q => ({ ...q, options: config.shuffleOptions ? shuffled(q.options, random) : [...q.options] }));
    });
}

export function scoreQuestions(questions, answers) {
    return questions.map((q, i) => ({ question: q, answer: answers[i], correct: Number.isInteger(answers[i]?.selected) && q.options[answers[i].selected]?.isCorrect === true }));
}
