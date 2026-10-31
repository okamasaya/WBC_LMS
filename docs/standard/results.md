# 終了後の共通処理（Drill / Actual）

`separete_drill_261026.html`、`Drill_N2_261031.html`、`Actual_N2_261030.html` が同じ部品を使用します。HTMLには出力先の `<div id="result-output"></div>` だけを置き、ボタンやtextareaは共通JSが生成します。生成AIのAPIを自動で呼び出す処理はなく、レポートをコピーして渡す方式です。

| ファイル | 管理する内容 |
| --- | --- |
| `resultData.js` | 正誤・時間・自信度を集計し、Session / QuestionResult（2.0.0）とサマリーを生成する純粋な処理 |
| `resultReview.js` | 問題ごとの解説カード、理解度4段階、復習フラグ |
| `resultReport.js` | AI用レポート本文と分析JSON、CSV列定義・エスケープ・3種類のCSV文字列生成。DOMに依存しない |
| `resultOutput.js` | 共通出力UI、理解度未入力の確認、確定、コピー・CSVダウンロード、変更時の再生成案内 |
| `prototype/assets/css/resultReview.css` / `prototype/assets/css/resultOutput.css` | 共通解説カードと共通出力UIの見た目 |

## ページ側との接続

ページ固有の回答を `ResultData.build()` に渡します。回答形式は `selected`（表示上の0始まりの位置、未回答はnull）、`confidence`（1〜4またはnull）、`elapsedTimeMs`（問題を表示していた累計時間）、`answeredAt`（最後の回答選択時刻のISO文字列またはnull）、`flagged`（試験中の確認フラグ）です。メタデータ・開始終了時刻・必要ならスキル解決関数を渡してください。

返り値は `summary` / `records` / `questions` / `reportBaseText` / `mainCatStats` です。ページ側はその `records` に解説理解度と復習フラグを反映し、`ResultOutput.mount({ container, getData, notify? })` へ渡します。`getData` は現在の返り値を返す関数です。理解度・復習フラグを変更した際には、返されたコントローラーの `invalidate()` を呼びます。

出力確定時にデータを複製し、AIレポートと全CSVを同じ確定データから作ります。確定後に理解度・復習フラグを変えると出力欄を閉じ、再確定が必要になります。理解度が未入力なら従来と同じ確認を行い、キャンセル時は未入力の問題に戻ります。

Drillには既存の関数名を維持する薄いアダプター（`reviewController.js` / `reportGenerator.js` / `dataExporter.js`）を残しています。CSVの列名・順序・ファイル名形式を維持し、試験中の確認フラグと終了後の復習フラグは別の列に保存します。未回答には架空の回答時刻や選択位置を付けません。

Actualの試験名・試験種別・レベル・出題元・スキル情報は `conf_JLPT_N2_LK.json` を参照します。学習者IDが未設定ならActualのStudentIDは空欄です。Drillの既存の仮IDは変更していません。自信度はモード名ではなく、セッションで記録する設定かどうかに従って出力します。

## 検証

リポジトリのルートから:

```sh
node tests/standard/examCore.test.mjs
node tests/standard/sharedResults.test.mjs
```

Playwright / Chromium が使える環境でHTTPサーバーを起動し:

```sh
python3 -m http.server 8000 --bind 127.0.0.1
node tests/standard/browser.cjs
```

共通の集計・スキーマ・AIデータ・CSVに加え、両ページの解説・確定・変更後の再生成、Actualのコピーと全CSV、未回答・時間切れ・自信度無効・モバイル表示を確認します。

JSON起動の共通化については `configuration.md` を参照してください。新DrillとActualは同じconfを読み込み、試験情報・問題データ・スキル定義を共用します。

## 推定処理へ渡す前のデータの意味

この段階では理解度推定を行っていません。出力は学習者の回答・自己申告と、画面で計測した記録です。

| 項目 | 現在の意味 |
| --- | --- |
| `isAnswered` / `isCorrect` | 未回答と不正解を区別する。未回答にもisCorrect=falseが入る |
| `confidenceLevel` | 回答時の自己申告。1が自信あり、4が直感に近い。未入力はnull。確率値ではない |
| `understandingLevel` | 解説を読んだ後の自己申告。0〜3、未入力はnull。モデルの推定値ではない |
| `responseTimeMs` | Drillは回答確定前の累計時間（自信度入力を含み、解説閲覧は除く）。Actualはその問題の表示時間の累計（再訪と終了確認中の表示時間を含み、制限時間で打ち切る） |
| `answeredAt` | 最後の回答選択・確定時刻。未回答はnull。問題表示時間の終了時刻とは異なる |
| `duringExamReviewFlag` / `reviewFlag` | 試験中の見直し指定と、解説確認後の復習指定。別の意思表示 |
| `skillId` | 現在はカテゴリLv3単位の対応付け。理解度推定の粒度として妥当かは別途検討する |
| `studentId` | 現行Drill・Actualは未設定ならnull。旧drillの仮IDは実在の学習者識別に使わない |

AIレポートとCSVは確定時点の同じスナップショットを使用します。理解度・復習フラグを変更すると再確定が必要です。これらの意味を保ってから、後続の推定モデルの入力設計を行います。
