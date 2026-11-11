/* IT question banks: validate before filtering; never infer pool membership from IDs. */
export const MODES = Object.freeze(['appropriate', 'inappropriate', 'mixed']);
export const MODE_LABELS = Object.freeze({ appropriate: '適切を選ぶ', inappropriate: '不適切を選ぶ', mixed: '混在', standard: '通常4択' });
const POOLS = ['appropriate', 'inappropriate'];
export const questionType = (q, version) => version === '0.1.0' ? 'polarity' : q?.question_type;
const fail = (path, message) => { throw new Error(`${path}: ${message}`); };
function object(value, keys, path) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) fail(path, 'オブジェクトが必要です');
    for (const key of keys) if (!Object.hasOwn(value, key)) fail(path, `${key} がありません`);
    for (const key of Object.keys(value)) if (!keys.includes(key)) fail(path, `未対応の項目 ${key}`);
}
function text(value, path) {
    if (typeof value !== 'string' || !/\S/u.test(value)) fail(path, '空白以外の文字が必要です');
}
function identifier(value, path, ids) {
    if (typeof value !== 'string' || !/^[A-Za-z][A-Za-z0-9_-]*$/u.test(value) || value.trim() !== value) fail(path, 'IDの形式が不正です');
    if (ids.has(value)) fail(path, `IDが重複しています: ${value}`);
    ids.add(value);
}

// entries: [{ bank: parsed JSON, url: resolved source URL }]
export function validateBanks(entries) {
    if (!Array.isArray(entries) || !entries.length) fail('問題バンク', '1ファイル以上が必要です');
    const ids = new Set(), sources = new Set();
    let examId;
    for (const { bank, url } of entries) {
        text(url, '問題ファイルURL');
        if (sources.has(url)) fail(url, '同じファイルが重複しています');
        sources.add(url);
        object(bank, ['format', 'schema_version', 'exam_id', 'questions'], url);
        if (bank.format !== 'it-polarity-pool' || !['0.1.0', '0.2.0'].includes(bank.schema_version)) fail(url, '未対応の問題形式・バージョンです');
        text(bank.exam_id, `${url}.exam_id`);
        if (examId !== undefined && examId !== bank.exam_id) fail(url, 'exam_id が他のバンクと一致しません');
        examId = bank.exam_id;
        if (!Array.isArray(bank.questions) || !bank.questions.length) fail(url, 'questions に1テーマ以上が必要です');
        for (const q of bank.questions) {
            const path = `${url} [${q?.question_id ?? 'IDなし'}]`;
            const legacy = bank.schema_version === '0.1.0';
            const type = questionType(q, bank.schema_version);
            if (!['polarity', 'standard'].includes(type)) fail(path, 'question_type はpolarityまたはstandardにしてください');
            object(q, legacy ? ['question_id', 'chapter', 'topic', 'stems', 'explanation', 'pools']
                : ['question_id', 'question_type', 'chapter', 'topic', 'question', 'explanation', 'pools', ...(type === 'polarity' ? ['instructions'] : [])], path);
            identifier(q.question_id, path, ids);
            if (!Number.isSafeInteger(q.chapter) || q.chapter < 1) fail(path, 'chapter は正の整数にしてください');
            text(q.topic, `${path}.topic`);
            text(q.explanation, `${path}.explanation`);
            if (legacy) {
                object(q.stems, POOLS, `${path}.stems`);
                POOLS.forEach(pool => text(q.stems[pool], `${path}.stems.${pool}`));
            } else {
                text(q.question, `${path}.question`);
                if (type === 'polarity') {
                    object(q.instructions, POOLS, `${path}.instructions`);
                    for (const pool of POOLS) {
                        const items = q.instructions[pool];
                        if (!Array.isArray(items) || !items.length) fail(path, `instructions.${pool} に1件以上が必要です`);
                        const instructions = new Set();
                        for (const item of items) {
                            text(item, `${path}.instructions.${pool}`);
                            const normalized = item.normalize('NFKC').trim();
                            if (instructions.has(normalized)) fail(path, '末尾表現が重複しています');
                            instructions.add(normalized);
                        }
                    }
                }
            }
            const pools = type === 'polarity' ? POOLS : ['correct', 'incorrect'];
            object(q.pools, pools, `${path}.pools`);
            const texts = new Set();
            for (const pool of pools) {
                const minimum = pool === 'correct' ? 1 : 3;
                if (!Array.isArray(q.pools[pool]) || q.pools[pool].length < minimum) fail(path, `${pool} の候補が${minimum}件未満です`);
                for (const o of q.pools[pool]) {
                    const opath = `${path}.${pool} [${o?.option_id ?? 'IDなし'}]`;
                    object(o, ['option_id', 'text', 'explanation'], opath);
                    identifier(o.option_id, opath, ids);
                    text(o.text, `${opath}.text`);
                    text(o.explanation, `${opath}.explanation`);
                    const normalized = o.text.normalize('NFKC').trim();
                    if (texts.has(normalized)) fail(opath, 'テーマ内で候補本文が重複しています');
                    texts.add(normalized);
                }
            }
        }
    }
    return examId;
}

function draw(random) {
    const value = random();
    if (!Number.isFinite(value) || value < 0 || value >= 1) throw new Error('乱数は0以上1未満が必要です');
    return value;
}
export function shuffle(values, random = Math.random) {
    const result = [...values];
    for (let i = result.length - 1; i > 0; i--) {
        const j = Math.floor(draw(random) * (i + 1));
        [result[i], result[j]] = [result[j], result[i]];
    }
    return result;
}
function freeze(value) {
    if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); }
    return value;
}
export function createExercise(entries, { mode = 'appropriate', chapter = 'all', questionId = 'all', count = 'all', random = Math.random } = {}) {
    const examId = validateBanks(entries);
    if (![...MODES, 'standard'].includes(mode)) throw new Error('出題方式が不正です');
    if (chapter !== 'all' && (!Number.isSafeInteger(chapter) || chapter < 1)) throw new Error('章の指定が不正です');
    if (count !== 'all' && (!Number.isSafeInteger(count) || count < 1)) throw new Error('問題数は正の整数またはallにしてください');
    const candidates = entries.flatMap(({ bank, url }) => bank.questions
        .filter(q => (chapter === 'all' || q.chapter === chapter) && (questionId === 'all' || q.question_id === questionId))
        .map(q => ({ q, bank, url })));
    if (!candidates.length) throw new Error('条件に合うテーマがありません');
    if (count !== 'all' && count > candidates.length) throw new Error(`対象は${candidates.length}テーマです。問題数を減らしてください`);
    const hasPolarity = candidates.some(({ q, bank }) => questionType(q, bank.schema_version) === 'polarity');
    if (mode === 'standard' && hasPolarity) throw new Error('切り替え型を含む範囲では、適切・不適切・混在から方式を選んでください');
    const questions = shuffle(candidates, random).slice(0, count === 'all' ? candidates.length : count).map(({ q, bank, url }) => {
        const type = questionType(q, bank.schema_version);
        const questionMode = type === 'standard' ? 'standard' : mode === 'mixed' ? (draw(random) < 0.5 ? 'appropriate' : 'inappropriate') : mode;
        const targetPool = type === 'standard' ? 'correct' : questionMode;
        const pools = type === 'standard' ? ['correct', 'incorrect'] : POOLS;
        let selectedInstruction = null, instructionPosition = null;
        if (type === 'polarity' && bank.schema_version === '0.2.0') {
            const instructions = q.instructions[questionMode];
            instructionPosition = Math.floor(draw(random) * instructions.length) + 1;
            selectedInstruction = instructions[instructionPosition - 1];
        }
        const options = pools.flatMap(pool => shuffle(q.pools[pool], random)
            .slice(0, pool === targetPool ? 1 : 3)
            .map(o => ({ optionId: o.option_id, text: o.text, rationale: o.explanation, pool, isCorrect: pool === targetPool })));
        return {
            id: q.question_id, chapter: q.chapter, topic: q.topic,
            question: bank.schema_version === '0.1.0' ? q.stems[questionMode] : q.question + (selectedInstruction ?? ''), explanation: q.explanation,
            questionType: type, questionPrefix: selectedInstruction === null ? null : q.question,
            selectedInstruction, instructionPosition,
            category_lv1: `第${q.chapter}章`, category_lv2: q.topic, category_lv3: '',
            category: `第${q.chapter}章 > ${q.topic}`, difficulty: null,
            bankSource: url, bankFormat: bank.format, bankSchemaVersion: bank.schema_version,
            questionMode, options: shuffle(options, random)
        };
    });
    return freeze({ examId, requestedMode: hasPolarity ? mode : 'standard', chapter, questionId, questions,
        bankSources: entries.map(({ bank, url }) => ({ url, format: bank.format, schemaVersion: bank.schema_version })) });
}

export function parseConfig(value) {
    object(value, ['version', 'title', 'examId', 'bankFiles'], '設定');
    if (value.version !== 1) throw new Error('未対応の設定バージョンです');
    text(value.title, '設定.title');
    text(value.examId, '設定.examId');
    if (!Array.isArray(value.bankFiles) || !value.bankFiles.length) throw new Error('設定.bankFiles に1ファイル以上が必要です');
    value.bankFiles.forEach(path => text(path, '設定.bankFiles'));
    return value;
}
function localURL(path, base) {
    const url = new URL(path, base);
    if (!['http:', 'https:'].includes(url.protocol) || url.origin !== new URL(base).origin) throw new Error('設定と問題ファイルは同じHTTPサーバー内に置いてください');
    return url.href;
}
async function readJSON(url, fetcher) {
    const response = await fetcher(url, { cache: 'no-store' });
    if (!response.ok) throw new Error(`${url}: 読込失敗 (HTTP ${response.status})`);
    try { return await response.json(); }
    catch { throw new Error(`${url}: JSONを解析できません`); }
}
export async function loadBanks(configPath, baseURL, fetcher = fetch) {
    const configURL = localURL(configPath, baseURL);
    const config = parseConfig(await readJSON(configURL, fetcher));
    const entries = await Promise.all(config.bankFiles.map(async path => {
        const url = localURL(path, configURL);
        return { url, bank: await readJSON(url, fetcher) };
    }));
    if (validateBanks(entries) !== config.examId) throw new Error('設定と問題バンクのexam_idが一致しません');
    return { config, configURL, entries };
}
