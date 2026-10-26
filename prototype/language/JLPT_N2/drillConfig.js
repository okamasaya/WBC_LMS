// JLPT N2 drill settings. config.js continues to select the question JSON files.
// Classic scripts share these names with the drill engine; keep this file first.
const appConfig = {"mode":"practice","timeLimit":40,"layout":"normal","showCategoryScore":true};

/* =========================================================
 * Raw Data Schema / Exam Context
 * File: prototype/language/JLPT_N2/drillConfig.js
 * ========================================================= */
const RAW_DATA_SCHEMA_VERSION = "2.0.0";

// This configuration is the JLPT N2 Language Knowledge drill.
// When N1 / other exams are created, change only this context block.
const EXAM_CONTEXT = Object.freeze({
    examId: "JLPT_N2_LK",
    examType: "JLPT",
    examLevel: "N2",
    examTitle: "JLPT N2 言語知識"
});


/* =========================================================
 * Skill Master
 * File: prototype/language/JLPT_N2/drillConfig.js
 *
 * Rule:
 *   SK_<EXAM>_<LEVEL>_<AREA>_<CATEGORY>_<SKILL>
 *
 * Initial policy:
 *   1 Question = 1 Skill
 *   Category Lv3 is used as the initial Skill granularity.
 * ========================================================= */
const SKILL_DEFINITIONS = Object.freeze([
    // JLPT N1
    { skillId: "SK_JLPT_N1_LK_CH_KANJI_READING", examLevel: "N1", categoryLv1: "言語知識", categoryLv2: "文字", categoryLv3: "漢字読み", skillName: "文字・漢字読み" },
    { skillId: "SK_JLPT_N1_LK_CH_ORTHOGRAPHY", examLevel: "N1", categoryLv1: "言語知識", categoryLv2: "文字", categoryLv3: "表記", skillName: "文字・表記" },
    { skillId: "SK_JLPT_N1_LK_VO_WORD_FORMATION", examLevel: "N1", categoryLv1: "言語知識", categoryLv2: "語彙", categoryLv3: "語形成", skillName: "語彙・語形成" },
    { skillId: "SK_JLPT_N1_LK_VO_CONTEXT", examLevel: "N1", categoryLv1: "言語知識", categoryLv2: "語彙", categoryLv3: "文脈規定", skillName: "語彙・文脈規定" },
    { skillId: "SK_JLPT_N1_LK_VO_PARAPHRASE", examLevel: "N1", categoryLv1: "言語知識", categoryLv2: "語彙", categoryLv3: "言い換え類義", skillName: "語彙・言い換え類義" },
    { skillId: "SK_JLPT_N1_LK_VO_USAGE", examLevel: "N1", categoryLv1: "言語知識", categoryLv2: "語彙", categoryLv3: "用法", skillName: "語彙・用法" },
    { skillId: "SK_JLPT_N1_LK_GR_SENTENCE_1", examLevel: "N1", categoryLv1: "言語知識", categoryLv2: "文法", categoryLv3: "文の文法1", skillName: "文法・文の文法1" },
    { skillId: "SK_JLPT_N1_LK_GR_SENTENCE_2", examLevel: "N1", categoryLv1: "言語知識", categoryLv2: "文法", categoryLv3: "文の文法2", skillName: "文法・文の文法2" },
    { skillId: "SK_JLPT_N1_LK_GR_TEXT", examLevel: "N1", categoryLv1: "言語知識", categoryLv2: "文法", categoryLv3: "文章の文法", skillName: "文法・文章の文法" },

    // JLPT N2
    { skillId: "SK_JLPT_N2_LK_CH_KANJI_READING", examLevel: "N2", categoryLv1: "言語知識", categoryLv2: "文字", categoryLv3: "漢字読み", skillName: "文字・漢字読み" },
    { skillId: "SK_JLPT_N2_LK_CH_ORTHOGRAPHY", examLevel: "N2", categoryLv1: "言語知識", categoryLv2: "文字", categoryLv3: "表記", skillName: "文字・表記" },
    { skillId: "SK_JLPT_N2_LK_VO_WORD_FORMATION", examLevel: "N2", categoryLv1: "言語知識", categoryLv2: "語彙", categoryLv3: "語形成", skillName: "語彙・語形成" },
    { skillId: "SK_JLPT_N2_LK_VO_CONTEXT", examLevel: "N2", categoryLv1: "言語知識", categoryLv2: "語彙", categoryLv3: "文脈規定", skillName: "語彙・文脈規定" },
    { skillId: "SK_JLPT_N2_LK_VO_PARAPHRASE", examLevel: "N2", categoryLv1: "言語知識", categoryLv2: "語彙", categoryLv3: "言い換え類義", skillName: "語彙・言い換え類義" },
    { skillId: "SK_JLPT_N2_LK_VO_USAGE", examLevel: "N2", categoryLv1: "言語知識", categoryLv2: "語彙", categoryLv3: "用法", skillName: "語彙・用法" },
    { skillId: "SK_JLPT_N2_LK_GR_SENTENCE_1", examLevel: "N2", categoryLv1: "言語知識", categoryLv2: "文法", categoryLv3: "文の文法1", skillName: "文法・文の文法1" },
    { skillId: "SK_JLPT_N2_LK_GR_SENTENCE_2", examLevel: "N2", categoryLv1: "言語知識", categoryLv2: "文法", categoryLv3: "文の文法2", skillName: "文法・文の文法2" },
    { skillId: "SK_JLPT_N2_LK_GR_TEXT", examLevel: "N2", categoryLv1: "言語知識", categoryLv2: "文法", categoryLv3: "文章の文法", skillName: "文法・文章の文法" }
]);


/**
 * Category Lv2・Lv3 表示順
 */
const CATEGORY_ORDER = {

    lv2: {

        "言語知識": [
            "文字",
            "語彙",
            "文法"
        ]

    },

    lv3: {

        "言語知識": {
            "文字": [
                "漢字読み",
                "表記"
            ],
 
            "語彙": [
                "語形成",
                "文脈規定",
                "言い換え類義",
                "用法"
            ],

            "文法": [
                "文の文法1",
                "文の文法2",
                "文章の文法"
            ]
        }


    }

};

