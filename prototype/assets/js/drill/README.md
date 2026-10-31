# Drill engine（初回分割版）

JLPT N2 の動作中の演習画面を、機能ごとの JavaScript と CSS に分けた構成です。

起動する HTML:

`prototype/language/JLPT_N2/separete_drill_261026.html`

比較元の `Edit_drill_260820.html` はそのまま残しています。

## 変更する場所

| 変更したいもの | ファイル |
| --- | --- |
| 問題 JSON の場所 | `prototype/language/JLPT_N2/config.js`（既存） |
| JSON の読込・検証・変換 | `prototype/language/JLPT_N2/questionLoader.js`（既存） |
| 演習モード、制限時間、レイアウト、試験情報、スキル定義、カテゴリ順 | `prototype/language/JLPT_N2/drillConfig.js` |
| 演習中の問題・回答・フラグ・時間・集計結果 | `drillState.js` |
| 文字整形、表示ラベル、トースト、計時などの共通処理 | `drillUtils.js` |
| カテゴリ Lv1〜Lv3 の選択肢と連動 | `categorySelector.js` |
| 条件絞り込み、問題と選択肢のシャッフル、演習開始 | `examController.js` |
| 問題・選択肢・即時解説・問題一覧の描画 | `questionView.js` |
| 回答、自信度、問題移動、演習中の確認フラグ | `answerController.js` |
| 採点、結果表示、Session / QuestionResult の生成 | `resultController.js` |
| 解説理解度、復習フラグ、出力確定前の確認 | `reviewController.js` |
| AI 用レポート本文と分析用 JSON | `reportGenerator.js` |
| CSV の列定義・生成・ダウンロード、コピー | `dataExporter.js` |
| 起動時の問題読込、モード別の画面準備、回答時間の更新 | `app.js` |
| この演習画面のスタイル | `prototype/assets/css/drill.css` |

表内でフォルダを省略した JavaScript は、すべてこの `prototype/assets/js/drill/` にあります。

## 読込順と互換性

HTML の head では既存の `config.js` と `questionLoader.js`、共通の `randomSelector.js` と `contentLauncher.js` を読み込みます。

body の末尾では次の順に読み込みます。

1. 教材フォルダの `drillConfig.js`
2. `drillState.js`
3. `drillUtils.js`
4. `categorySelector.js`
5. `examController.js`
6. `questionView.js`
7. `answerController.js`
8. `resultController.js`
9. `reviewController.js`
10. `reportGenerator.js`
11. `dataExporter.js`
12. `app.js`

初回は動作の維持を優先し、従来の関数名・共有変数・HTML の onclick / onchange を維持しています。これらは通常の script として同じグローバル環境を共有するため、読込順を保ち、個別のファイルだけを module / async に変更しないでください。起動処理は全ファイルの読込後に window.onload で実行されます。

スタイルは元の style 要素と同じ位置で `drill.css` を読み込み、その後に既存の `style.css` を読み込みます。CSS の適用順も維持します。

問題 JSON の相対パスは、共通 JS の配置先ではなく、起動した HTML を基準に解決されます。

## 起動と確認

リポジトリのルートを静的 HTTP サーバーで公開し、次のパスを開きます。

`/prototype/language/JLPT_N2/separete_drill_261026.html`

例:

```sh
python -m http.server 8000
```

`http://localhost:8000/prototype/language/JLPT_N2/separete_drill_261026.html`

確認項目:

- 練習モードでカテゴリ・難易度・問題数を変更し、開始できる。
- 自信度あり／なしの両方で回答し、解説を表示できる。
- 前後の問題への移動、採点、解説理解度、復習フラグを操作できる。
- レポートを生成・コピーでき、3種類の CSV をダウンロードできる。
- 模擬試験モードでは問題一覧、確認フラグ、制限時間での自動採点が動く。

## 今回維持したもの

初回分割では、元の44関数の処理、採点ルール、CSV の列名・列順、データ形式（2.0.0）、ダミーの学習者IDや出題元記録の扱いを維持しています。設定形式の統一、共有状態の再設計、採点関数の細分化は、この分割版の動作確認後に扱います。

新しい HTML の contentLauncher.js の参照先は、配置済みの `prototype/assets/js/contentLauncher.js` に合わせています。

## 結果・解説カードの共通化（261030）

終了後の解説カードと理解度の選択処理は `prototype/assets/js/shared/resultReview.js`、対応スタイルは `prototype/assets/css/resultReview.css` に切り出しました。`Actual_N2_261030.html` でも同じ部品を使用します。drill側は引き続き `resultController.js` が採点・Rawログを作成し、`reviewController.js` が理解度と復習フラグをログに反映します。レポートとCSVの列定義・生成処理は維持しています。

共通スクリプトは `resultController.js` より前に読み込んでください。カード内のクリック処理はイベントリスナーで登録します。表示・ログ更新・CSVの回帰確認は `node prototype/assets/js/cbt/tests/browser.cjs` で行えます（HTTPサーバー、Playwright、Chromiumが必要）。

## レポート・ログ出力の共通化（261031）

終了後の集計・Session / QuestionResult生成は `../shared/resultData.js`、AIレポートとCSVの列定義・文字列生成は `../shared/resultReport.js`、最下部の出力UI・理解度の未入力確認・確定・コピー・ダウンロードは `../shared/resultOutput.js` に移しました。Actual版も同じ処理を使用します。

`resultController.js` は共通処理にdrillの回答状態を渡すアダプターと、drill固有の得点表示を担当します。`reviewController.js` / `reportGenerator.js` / `dataExporter.js` は既存の関数名を維持するための薄いアダプターです。HTML内の出力ボタン・textareaは共通JSで生成し、表示先の `result-output` だけをHTMLに残しています。

確定後に理解度・復習フラグを変更すると、古いレポートは無効になり、再生成が必要です。詳細は `../shared/README.md` を参照してください。

## JSON設定の新Drillページ（261031）

`prototype/language/JLPT_N2/Drill_N2_261031.html` は既存練習エンジンを再利用し、Actualと共通のconf JSONから起動します。旧HTMLと設定JSは保持しています。新ページの設定・CSS・検証手順は `../shared/examConfig.md` を参照してください。
