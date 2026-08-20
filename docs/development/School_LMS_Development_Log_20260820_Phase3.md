# School LMS / ALP-BKT 開発ログ
## 2026-08-20 HTML整理・AIレポート・Session / QuestionResult 改修

### 1. 今回の目的

テスト終了後の出力系を改修する前段として、`Edit_drill.html` 全体を整理し、
将来の HTML / CSS / JavaScript 分離を見据えた構造へ変更した。

その上で、以下の機能追加・出力改善を実施した。

- 自信度入力 ON / OFF
- 難易度選択
- AIレポート生成プロンプトの汎用化
- Session / QuestionResult のRawデータ出力整理
- BKT推定へ接続するための Skill_ID 導入
- 将来のALP-BKT / Python Dash向けデータフロー整理

---

## 2. Phase 1：HTML全体の整理

ベースとなる `Edit_drill.html` について、動作を維持しながら不要コードを整理した。

### 実施内容

- 古い `window.onload` の削除
- 旧 `startExam()` の削除
- 旧カテゴリ選択処理の削除
- 古いリスタートボタン等のコメントアウト残骸を削除
- `raw-questions` 時代の不要コードを整理
- JavaScriptを責務単位でSECTION分け
- 将来の外部JS分割先をコメントで明示

主なSECTIONは以下。

```text
Application State
Common Utilities
Category Selector
Exam Initialization
Question Rendering
Answer Control
Exam Finalization
Review / Understanding
AI Report
Data Export
```

将来的には、これらを以下のように外部ファイルへ分割する予定。

```text
assets/js/
├─ category-selector.js
├─ exam-controller.js
├─ answer-controller.js
├─ result-controller.js
├─ review-controller.js
├─ ai-report.js
├─ data-exporter.js
└─ skill-master.js
```

---

## 3. 自信度入力 ON / OFF 機能

学生から「ひたすら問題だけを解きたい」という要望があったため、
Practice / Drillモードでも自信度入力を任意化した。

### 動作

#### 自信度 ON

```text
回答
 ↓
自信度入力
 ↓
回答確定
 ↓
正解・解説表示
```

#### 自信度 OFF

```text
回答
 ↓
即時回答確定
 ↓
正解・解説表示
```

自信度OFFの場合は、ログ上では以下の扱いとする。

```text
ConfidenceLevel = NULL
```

Session側では、自信度入力を利用したか判別できるように設定値も保存する。

```text
UseConfidence
```

---

## 4. 難易度選択機能

Drill開始時に難易度を指定可能にした。

### 内部仕様

```text
すべて   : difficulty 1～5
易しい   : difficulty 1～3
難しい   : difficulty 3～5
```

difficulty=3 は標準帯として両方に含める。

### 学生向け表示

内部の1～5という数値は開発・分析用タグとし、学生画面では露骨に表示しない。

表示は以下のような抽象表現を使用する。

```text
すべて
易しい
難しい
```

AIレポートでは、さらに以下のラベルへ変換する。

```text
1～2 : 基礎
3    : 標準
4～5 : 発展
```

内部データでは引き続き `difficulty=1～5` を保持する。

---

## 5. AIレポート改修

従来のAIレポートはGemini Canvasを前提としており、
追加問題生成まで含んでいたため、モデル非依存の分析レポートへ変更した。

### 削除した仕様

- Canvas依存
- Canvas上での復習
- 類似問題3問の生成
- AIによる追加出題

### 新しい分析項目

AIへ以下を渡す。

- 正誤
- Category Lv1 / Lv2 / Lv3
- 難易度（基礎 / 標準 / 発展）
- 回答時間
- 自信度
- 解説確認後の理解度
- ReviewFlag
- 出題順

### AIレポートの考え方

正答率のみではなく、以下の組み合わせを評価対象とする。

```text
正解 × 自信度
不正解 × 自信度
正誤 × 回答時間
正誤 × 難易度
不正解 × 解説理解度
```

1回の演習のみで「苦手」「能力不足」と断定せず、
「できたこと」「伸びていること」「次に伸ばせること」を中心に評価させる。

### 複数回分析

運用上は、Excel等で5回程度の演習結果をまとめて生成AIへ渡す想定。

各レポートをSession単位で区切る。

```text
=== CBT_SESSION_BEGIN ===
...
=== CBT_SESSION_END ===
```

これにより、複数SessionをまとめてAIへ渡した際に、
実施日時・正答率・難易度・カテゴリ・自信度・回答時間等を比較しやすくした。

---

## 6. BKT用データフロー整理

BKTをCBT内部へ直接埋め込まず、
Rawデータを受け取る独立した推定処理として分離する方針とした。

```text
CBT
 ↓
Raw Data
 ├─ Session
 └─ QuestionResult
 ↓
BKT推定
 ↓
BKT Data Summary Tables
 ├─ BKTParameter
 ├─ KnowledgeStateHistory
 └─ KnowledgeState
 ↓
Python / Dash
 ↓
学習ダッシュボード
```

重要な設計思想は以下。

```text
Raw Data = 観測事実
BKT Table = 推定結果
```

BKT推定結果をRawログへ直接混在させない。

将来的にBKT以外のモデルを試す場合も、

```text
Raw Data
 ├─ BKT
 ├─ IRT
 ├─ ML
 └─ AI Analysis
```

と横展開できる構造とする。

---

## 7. BKTパラメータの扱い

BKT側で使用する基本パラメータは以下。

```text
P(L0) : 初期理解確率
P(T)  : 学習遷移確率
P(G)  : Guess
P(S)  : Slip
```

これらはQuestionResultへ保存せず、
BKT推定側の別テーブルで管理する。

想定テーブル：

```text
BKTParameter
----------------
BKTParamID
SkillID
P_L0
P_T
P_G
P_S
ModelVersion
CreatedAt
```

`BKTParamID` は推定処理側で割り当てる。

P(L1), P(L2), ... のような学生ごとの理解度推移は、
BKT推定結果としてKnowledgeState系テーブルへ保存する。

---

## 8. Skill_ID設計

Skill_IDは、

> 「この問題がどの知識・技能を観測する問題なのか」

を識別するためのタグとして定義した。

初期実装では、

```text
1 Question = 1 Skill
```

とする。

### 命名規則

School LMS全体でユニークになるよう、以下の形式を採用。

```text
SK_<Exam>_<Level>_<CategoryLv1Code>_<CategoryLv2Code>_<SkillCode>
```

JLPT N2の例：

```text
SK_JLPT_N2_LK_CH_KANJI_READING
SK_JLPT_N2_LK_CH_ORTHOGRAPHY

SK_JLPT_N2_LK_VO_WORD_FORMATION
SK_JLPT_N2_LK_VO_CONTEXT
SK_JLPT_N2_LK_VO_PARAPHRASE
SK_JLPT_N2_LK_VO_USAGE

SK_JLPT_N2_LK_GR_SENTENCE_1
SK_JLPT_N2_LK_GR_SENTENCE_2
SK_JLPT_N2_LK_GR_TEXT
```

JLPT N1も同じ命名体系を使用し、レベルのみ分離する。

```text
SK_JLPT_N1_LK_VO_USAGE
SK_JLPT_N2_LK_VO_USAGE
```

N1 / N2で同じカテゴリ名でも、BKT上のSkillは別管理とする。

### 現段階の実装

現在はSkill一覧をHTML内部に保持。

```text
SKILL_DEFINITIONS
```

Category Lv1 / Lv2 / Lv3からSkill_IDを解決する。

次回のHTML / JS分離時に、

```text
assets/js/skill-master.js
```

へ独立させる予定。

---

## 9. Phase 3：Session / QuestionResult Raw出力

`Edit_drill_phase3_session_questionresult.html` で、
終了後のログ出力を正式なRawデータ形式へ整理した。

### Session

主な出力項目：

```text
SessionID
StudentID
ExamID
ExamTitle
ExamLevel
Mode

UseConfidence
DifficultyMode

SelectedCategoryLevel1
SelectedCategoryLevel2
SelectedCategoryLevel3

StartAt
EndAt
TotalDurationSec

TotalQuestions
AnsweredCount
UnansweredCount
CorrectCount
WrongCount
ScoreRate

QuestionFiles
DataSchemaVersion
CreatedAt
```

### QuestionResult

Rawデータは多少冗長でも、
後から単体で分析可能な形を優先して多めに保存する。

```text
ResultID
SessionID
StudentID

QuestionSequence
QuestionID
SkillID
SkillName

CategoryLevel1
CategoryLevel2
CategoryLevel3

Difficulty
DifficultyLabel

QuestionText

SelectedOptionPosition
UserAnswerText
CorrectAnswerText
IsCorrect

ResponseTimeMs
AnswerTimeSec
ElapsedTimeSec
AnsweredAt

ConfidenceLevel
ConfidenceLabel

UnderstandingLevel
UnderstandingLabel

ReviewFlag
DuringExamReviewFlag

Mode
UseConfidence
DifficultyMode

Explanation
CreatedAt
```

### 主な修正点

- `AnsweredAt` は未回答時にNULLとする
- 選択肢シャッフル後の表示位置だけでなく、回答本文も保存
- QuestionResult内にSkill_IDを保存
- 数値difficultyと表示用DifficultyLabelを両方保存
- ConfidenceLevelとそのラベルを両方保存
- UnderstandingLevelとそのラベルを両方保存
- SessionからJOIN可能な情報もRaw用途として一部重複保持
- `DataSchemaVersion = 2.0.0` を追加

---

## 10. 出力ファイル

Phase 3では以下の出力を用意。

```text
Session_<SessionID>.csv
QuestionResult_<SessionID>.csv
統合Raw CSV
AIレポート
```

今後の標準データは、

```text
Session
QuestionResult
```

の2系統を中心とする。

---

## 11. 現在の状態

2026-08-20時点で以下を確認済み。

- HTML整理完了
- 自信度ON / OFF動作確認済み
- 難易度フィルタ動作確認済み
- AIレポート改修済み
- Session / QuestionResult出力改修済み
- Skill_ID割り当て実装済み
- JavaScript構文チェック済み
- 実ブラウザでPhase 3動作確認済み

Phase 3を現時点の基準版としてGitへ反映する。

---

## 12. 次回以降の候補

次回以降は、Phase 3を基準に以下を進める。

```text
1. HTML / CSS / JSの物理分離
2. SKILL_DEFINITIONS → skill-master.js
3. Exam Context / Config整理
4. Session / QuestionResultの実データ蓄積
5. BKTParameterテーブル設計
6. BKT推定エンジン実装
7. KnowledgeState / History生成
8. Python Dashによる可視化
9. 複数Sessionを扱うExcel履歴出力
```

---

## 13. 今回の到達点

今回の改修により、CBTは単純な問題演習画面から、

```text
問題ライブラリ
 ↓
条件指定Drill
 ↓
回答・自信度・時間・理解度記録
 ↓
AIレポート
 ↓
Raw Session / QuestionResult
 ↓
BKT / Dash
```

というALP-BKT向けのデータ生成基盤へ進んだ。

特に、CBT側は「観測事実を正確に残す」責務に限定し、
BKT推定・AI分析・ダッシュボードを後段へ分離したことで、
今後のモデル変更や横展開にも対応しやすい構造になった。
