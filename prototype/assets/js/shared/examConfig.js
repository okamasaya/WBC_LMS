/* Common declarative configuration. URLs are resolved against the configuration file. */
(() => {
    const key = c => JSON.stringify([c.categoryLv1, c.categoryLv2, c.categoryLv3]);
    function normalize(source, mode) {
        const fail = message => { throw new Error(`設定エラー: ${message}`); };
        if (!source || ![1, 2].includes(source.schemaVersion)) fail('schemaVersion は1または2を指定してください。');
        if (!['actual', 'drill'].includes(mode)) fail('モードが不正です。');
        if (typeof source.title !== 'string' || !source.title.trim() || typeof source.examId !== 'string' || !source.examId.trim()) fail('title / examId が必要です。');
        if (!Array.isArray(source.questionFiles) || !source.questionFiles.length || source.questionFiles.some(p => typeof p !== 'string' || !p.trim())) fail('questionFiles に問題ファイルを指定してください。');
        if (new Set(source.questionFiles).size !== source.questionFiles.length) fail('問題ファイルの指定が重複しています。');
        if (!Array.isArray(source.categories) || !source.categories.length) fail('categories が必要です。');
        const keys = new Set();
        for (const c of source.categories) {
            if (!c || ['categoryLv1', 'categoryLv2', 'categoryLv3'].some(k => typeof c[k] !== 'string' || !c[k].trim())) fail('カテゴリLv1〜Lv3が必要です。');
            if (keys.has(key(c))) fail('カテゴリが重複しています。');
            keys.add(key(c));
        }
        if (source.schemaVersion === 1) {
            if (mode !== 'actual') fail('新しいdrillページにはschemaVersion: 2の設定を指定してください。');
            return structuredClone(source);
        }
        const settings = source[mode];
        if (!settings || typeof settings !== 'object') fail(`${mode} 設定が必要です。`);
        const result = { ...structuredClone(source), ...structuredClone(settings), schemaVersion: 1 };
        if (mode === 'actual') {
            result.categories = source.categories.map(c => ({ ...c, count: c.actualCount }));
        } else {
            for (const name of ['recordConfidence', 'allowConfidenceToggle', 'allowCategorySelection', 'shuffleQuestions', 'shuffleOptions']) {
                if (typeof settings[name] !== 'boolean') fail(`drill.${name} はtrue / falseを指定してください。`);
            }
            if (!Array.isArray(settings.questionCounts) || !settings.questionCounts.length || settings.questionCounts.some(n => n !== 'all' && (!Number.isSafeInteger(n) || n <= 0)) || new Set(settings.questionCounts).size !== settings.questionCounts.length) fail('drill.questionCounts は正の整数または "all" の重複しない配列にしてください。');
            if (!settings.questionCounts.includes(settings.defaultQuestionCount)) fail('defaultQuestionCount をquestionCountsに含めてください。');
            if (!Array.isArray(settings.difficultyModes) || !settings.difficultyModes.length || settings.difficultyModes.some(v => !['all', 'easy', 'hard'].includes(v)) || new Set(settings.difficultyModes).size !== settings.difficultyModes.length) fail('difficultyModes はall / easy / hardを指定してください。');
            if (!settings.difficultyModes.includes(settings.defaultDifficultyMode)) fail('defaultDifficultyMode をdifficultyModesに含めてください。');
        }
        return result;
    }
    async function load(mode, defaultPath) {
        const params = new URLSearchParams(window.location.search);
        const path = params.has('conf') ? params.get('conf') : defaultPath;
        if (!path?.trim()) throw new Error('設定ファイルのパスが空です。');
        const url = new URL(path, window.location.href);
        const response = await fetch(url, { cache: 'no-store' });
        if (!response.ok) throw new Error(`設定ファイルを取得できません (HTTP ${response.status})。`);
        const config = normalize(await response.json(), mode);
        config.sourceQuestionFiles = [...config.questionFiles];
        config.questionFiles = config.questionFiles.map(p => new URL(p, url).href);
        config.configURL = url.href;
        return config;
    }
    window.ExamConfig = Object.freeze({ normalize, load, categoryKey: key });
})();
