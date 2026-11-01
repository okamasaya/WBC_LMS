# テスト記録：現行prototypeのCSV互換性（2026-11-02）

## 対象と目的

prototypeの実施・解説後に確定するCSVをBKTへ渡すという用途に対し、最初の独自モックとの差を調査し、現行処理による互換版を追加した。対象はprototype_csv.py、tools/prototype_exports.cjs、追加CSV、flat_app.pyの読込先、Python・ブラウザの検証。

- 基点コミット：`4f7b89eb69635a15af8b5f7672d3c247ebe07436`。
- 開始（JST）：2026-11-02T07:37:55.294369+09:00。
- 終了（JST）：2026-11-02T07:38:11.233654+09:00。
- 新規Pythonテスト8件。全体82件にBKT関連48件を含む（足し合わせない）。
- 現行Actual・JSON版Drillの操作は自動テストによる合成回答。実際の学習者の記録ではない。

## 実行結果

| 検証 | 終了コード | 生ログ |
|---|---:|---|
| all_python | 0 | [ログ](test-records/20261102_073755_prototype_csv/all_python.log) |
| prototype_browser | 0 | [ログ](test-records/20261102_073755_prototype_csv/prototype_browser.log) |
| prototype_import | 0 | [ログ](test-records/20261102_073755_prototype_csv/prototype_import.log) |
| flat_browser | 0 | [ログ](test-records/20261102_073755_prototype_csv/flat_browser.log) |
| mock_browser | 0 | [ログ](test-records/20261102_073755_prototype_csv/mock_browser.log) |

[コマンド・実行時刻・ソースと成果物のSHA-256](test-records/20261102_073755_prototype_csv/metadata.json)

## 確認したこと

| 対象 | 結果 |
|---|---|
| 列と順序 | 現行のSession26列・QuestionResult41列に一致。元の21列・33列は完全一致ではなかったことも固定テストで確認 |
| 600回答 | 正誤、自信度、理解度、問題ID、スキルID、反応時間と回答時刻を元データに照合。新旧IDは対応表で追跡 |
| 生成とファイル | 現行JS処理で生成し、同条件でバイト一致。格納CSVとmanifestも一致 |
| 推定接続 | 互換版600件を標準BKTで600履歴・9状態、独立回答の補助モデルで600行・除外0として処理 |
| 1回分の出力 | Session・QuestionResult・統合Raw CSV・レポートの同一スナップショットと3項目の一致 |
| 学習者ID空欄 | 実出力の空欄を確認。標準BKTは除外。明示した単一学習者の補完で処理可能。補助モデルはIDなしで処理 |
| 未入力と理解度0 | 空欄は欠損、0は有効値として保持。未回答は推定から除外 |
| 再確定 | 同じResultIDで補助項目を変更した版の混在は、補助モデルが競合として拒否 |
| 入力の区別 | Session集計CSVだけを回答入力へ渡すと拒否。QuestionResult・統合Rawを受付 |
| 実Actual画面 | 30問のうち2問回答、解説後理解度0/3、見直しフラグ、レポート確定、3種CSV実ダウンロード |
| 実Drill画面 | 10問のうち2問回答、解説後理解度0/3、レポート確定、3種CSV実ダウンロード |
| 実CSV→推定 | Actual28行・Drill8行の未回答を除外し、各2回答を両モデルへ接続。QuestionResultとRawの回答情報は一致、サマリーレポートとも一致 |
| Dash回帰 | 32パターン、入力連動、24回答、異常値、モバイル。互換CSVの600行、誤答272・正答328の絞込、272行CSV出力。JS例外・HTTP400以上なし |

## 現行画面から保存した証跡

- [Actualの出力一覧](test-records/20261102_073755_prototype_csv/ui_exports/Actual/manifest.json)
- [Drillの出力一覧](test-records/20261102_073755_prototype_csv/ui_exports/Drill/manifest.json)

各フォルダーに3種CSVとAI_Report.txtを保存した。CSVのStudentIDは空欄のまま保存し、検証時だけ明示した合成IDで標準BKTに対応付けた。実際の運用データでは、本人・同一学習者の確認をせず空欄を補完しない。

## 工程中に確認・修正した点と限界

元のモックはモデルに必要な共通列の互換性だけを確認していた。今回、現行の出力全列と比較し、完全一致でないことを検出したため、既存モックを残して互換版を追加した。

現行JSの解説後更新処理も使用して、未入力の理解度ラベルを「未入力」のまま保持するよう生成補助処理を整えた。実出力の検証スクリプトを作成した際は回答数の列名を誤ってAnsweredCountとして参照して失敗し、現行のAnsweredQuestionsへ直して最終検証した。prototype本体の変更はない。

互換版には明示的に合成StudentIDを指定する点がデフォルト実出力と異なる。現行CSVには解説閲覧時刻・理解度入力時刻がなく、CreatedAtで代替しない。CSVアップロードUIの8055への追加・Django連携・実ログの精度評価・パラメータ推定は今回実施していない。
