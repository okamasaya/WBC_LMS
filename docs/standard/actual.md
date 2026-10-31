# JLPT N2 CBT（開発中）

起動ページ: `prototype/language/JLPT_N2/Actual_N2_261030.html`

リポジトリのルートで `python3 -m http.server 8000` を実行し、上記パスをHTTP経由で開いてください。file:// ではJSONを取得できません。

## 設定

`prototype/language/JLPT_N2/conf_JLPT_N2_LK.json` だけで出題条件を変更できます。初期値の30問・40分とカテゴリ配分は開発用の暫定値です。公式試験の構成・尺度得点を再現するものではありません。

| キー | 内容 |
| --- | --- |
| schemaVersion | 共通設定形式は2（旧Actual専用の1も読み込み可能） |
| title / examId | 画面名 / 試験識別子。画面には固定の「開発中」バッジも表示 |
| examType / examLevel / examTitle | レポート・CSV用の試験種別 / レベル / 試験名 |
| categories[].skillId / skillName | レポート・CSV用のスキルID / スキル名（既存drillと同じN2の識別子） |
| studentId | 任意の学習者ID。未設定時はCSVでは空欄 |
| actual.timeLimitMinutes | 制限時間（分、0より大きく1440以下。小数可） |
| questionFiles | 問題JSON一覧。パスはconfファイルからの相対パス |
| categories | 出題順のカテゴリ一覧。categoryLv1 / categoryLv2 / categoryLv3 は問題データと完全一致させる |
| categories[].actualCount | そのカテゴリからの出題数。0なら出題しない。合計が試験全体の問題数 |
| actual.shuffleQuestionsWithinCategory | trueならカテゴリ内から重複なしでランダム抽出。falseならデータ順の先頭から抽出 |
| actual.shuffleOptions | 選択肢をシャッフルするか。初期値はfalse（元の順番を維持） |
| actual.recordConfidence | 自信度入力を表示するか。入力は任意 |

カテゴリは設定順に出題します。問題不足、設定重複、不正JSON、不正問題、問題ID重複は開始前にエラーとなり、出題数を自動で減らしません。設定の変更は再読み込み後に反映されます。

## 動作と構成

問題データと `prototype/assets/js/shared/questionLoader.js` の読込・検証・変換を現行Drill版と共用します。受験中はCBT専用の `app.js` / `examCore.js` / `actual.css` を使用します。終了後の解説カードは `prototype/assets/js/shared/resultReview.js` と `prototype/assets/css/resultReview.css` に切り出し、drill版と共用しています。drillの採点・ログ形式・練習中の動作は維持しています。

回答は終了まで変更可能です。回答を選び直すと旧回答の自信度を消し、再入力できるようにします。未回答でも次へ移動・フラグ付け・提出できます。番号一覧では自信度入力の有無と関係なく、回答選択済みを「回答済み」とします。自信度入力後も解説は出しません。

終了確認中もタイマーは動き、期限に達するとダイアログを閉じて自動採点します。バックグラウンドから戻った際も期限時刻と照合します。終了後に回答の変更はできません。各問1点でカテゴリ別の素点・正答率と全問の解説を表示します。解説は折り畳まず、drill版と同じカード形式（問題、正誤、回答、思考時間、自信度、不正解時の正解、解説、理解度4段階、復習フラグ）で一覧表示します。思考時間は各問題を表示していた時間の累計で、時間切れ後の遅延は含みません。試験中の確認フラグと終了後の復習フラグは別に記録します。理解度は同じボタンをもう一度押すと未入力に戻ります。理解度・復習フラグの確認後、drill版と共通のレポート欄でAI用レポートをコピーし、統合Raw CSV、QuestionResult.csv、Session.csvをダウンロードできます。再読み込みで画面内の回答・理解度・フラグは失われるため、必要な結果は出力してください。

回答はメモリ内のみで、再読み込みでは失われます。画面離脱の警告はブラウザ依存です。サーバーによる答案保存や不正防止を行う試験システムではなく、操作練習のための模擬試験です。

## 検証

リポジトリのルートから実行:

```sh
node tests/standard/examCore.test.mjs
```

実データで配分・重複防止・設定不備・問題不足・選択肢のシャッフルと採点を検証します。

Playwright と Chromium が利用可能な環境では、上記のHTTPサーバー起動後にブラウザ検証も実行できます:

```sh
node tests/standard/browser.cjs
```

既定のChromiumは `/usr/bin/chromium`。必要なら `CBT_TEST_CHROMIUM` と `CBT_TEST_BASE_URL` で実行ファイル・サーバーURLを変更できます。回答・自信度・フラグの保持、番号移動、終了確認、時間切れ、結果、設定エラー、スマートフォン幅を検証します。共通化の回帰確認として、drillの即時解説、終了後の理解度・復習フラグとログ更新、レポート生成、QuestionResult CSVも検証します。

終了後の集計・解説・レポート・CSVは `results.md` にまとめた共通処理を使用します。設定を変更する場合は、`node tests/standard/sharedResults.test.mjs` でも出力の回帰確認ができます。

## JSON設定の共用

`Drill_N2_261031.html` と同じconfを使う形式に移行しました。`?conf=設定.json` で切り替えできます。共通項目とモード別の詳細は `configuration.md` を参照してください。共通CSSは `learning.css`、Actual固有CSSは `actual.css` です。
