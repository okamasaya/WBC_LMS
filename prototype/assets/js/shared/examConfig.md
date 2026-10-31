# JSONで起動するDrill / Actual（N2）

## 入口

- 練習: `prototype/language/JLPT_N2/Drill_N2_261031.html`
- 模擬試験: `prototype/language/JLPT_N2/Actual_N2_261030.html`
- 共通設定: `prototype/language/JLPT_N2/conf_JLPT_N2_LK.json`

HTMLの `data-config` が既定の設定ファイルです。両ページで `?conf=別の設定.json` を付けると指定したファイルを使用します。confのパスはHTMLから、問題ファイルのパスはconfの場所から解決します。HTTPサーバーで開いてください。

例:

```text
Drill_N2_261031.html?conf=conf_JLPT_N2_LK.json
Actual_N2_261030.html?conf=conf_JLPT_N2_LK.json
```

設定を切り替えるだけで、問題ファイル・試験情報・選択肢・出題条件を変更できます。N1/N3/TOEICの実データでの検証とpublicへの配置は今回の対象外です。

## schemaVersion: 2

共通情報と、`drill` / `actual` の設定を1ファイルで管理します。

| 場所 | 設定する内容 |
| --- | --- |
| `title` | 画面タイトル。初期値は「開発中」 |
| `examId` / `examType` / `examLevel` / `examTitle` | レポート・CSV用の試験情報 |
| `studentId` | 任意。未設定なら新Drill・ActualのCSVは空欄 |
| `questionFiles` | 問題JSONの一覧。confからの相対パス |
| `categories` | 対象カテゴリと表示順。問題データのLv1〜Lv3に完全一致させる |
| `categories[].skillId` / `skillName` | スキル情報。両モードで共用 |
| `categories[].actualCount` | Actualでそのカテゴリから出題する数。0ならActualでは出題しない。Drillの出題数には影響しない |

### drill

| キー | 内容 |
| --- | --- |
| `questionCounts` | 選択できる出題数。正の整数と `"all"`（全問）を指定可能 |
| `defaultQuestionCount` | 問題数の初期値。questionCountsに含める |
| `difficultyModes` | 選択可能な難易度。`all` / `easy`（1〜3）/ `hard`（3〜5） |
| `defaultDifficultyMode` | 難易度の初期値。difficultyModesに含める |
| `allowCategorySelection` | カテゴリ選択を表示するか。falseなら設定された全カテゴリが対象 |
| `recordConfidence` | 自信度入力の初期値 |
| `allowConfidenceToggle` | 開始前に自信度入力の有無を変更できるか。falseならrecordConfidenceで固定 |
| `shuffleQuestions` / `shuffleOptions` | 問題 / 選択肢をランダム化するか |

Drillはカテゴリ・難易度で絞り込み、指定した問題数を抽出します。問題が少ない場合は従来どおり、その範囲にある問題だけを出題します。0問なら条件変更を促します。自信度ありなら入力後、自信度なしなら回答直後に正誤と解説を表示し、回答を確定します。解説を読んでいる時間は思考時間に含めません。

### actual

| キー | 内容 |
| --- | --- |
| `timeLimitMinutes` | 制限時間（分、0より大きく1440以下） |
| `recordConfidence` | 自信度を記録するか（入力は任意） |
| `shuffleQuestionsWithinCategory` | カテゴリ内からランダム抽出するか |
| `shuffleOptions` | 選択肢をランダム化するか |

Actualはcategoriesの順にactualCount問ずつ出題します。指定数に足りない場合は開始を止めます。終了まで回答変更が可能で、解説は終了後だけ表示します。

## 互換性と見た目

従来の `separete_drill_261026.html` / `config.js` / `drillConfig.js` は保持しています。新しいDrillは旧設定JSを読み込まず、`jsonConfig.js` がJSONを既存エンジンの設定に変換します。Actualは従来のschemaVersion: 1のconfも引き続き読み込めます。新DrillにはschemaVersion: 2を指定してください。

新DrillとActualの共通デザインは `prototype/assets/css/learning.css`、モード固有の調整は `drillPage.css` / `cbt.css` です。終了後の解説・集計・AIレポート・CSVは両モードで同じ共通部品を使います。従来drillのCSSは維持しています。

## 検証

リポジトリのルートで:

```sh
node prototype/assets/js/cbt/tests/examConfig.test.mjs
node prototype/assets/js/cbt/tests/examCore.test.mjs
node prototype/assets/js/cbt/tests/sharedResults.test.mjs
```

Playwright / Chromiumが利用可能な環境でHTTPサーバーを起動して:

```sh
python3 -m http.server 8000 --bind 127.0.0.1
node prototype/assets/js/cbt/tests/jsonDrill.browser.cjs
node prototype/assets/js/cbt/tests/browser.cjs
```

新Drillの練習機能、conf切替、相対パス、設定不備・問題取得失敗、モバイル、レポート・CSV、Actualと従来drillの回帰確認を行います。
