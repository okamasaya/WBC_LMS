# 共通CSSとモード別CSS

対象は現行の `Actual_N2_261030.html`、`Drill_N2_261031.html`、N2の入口 `index.html`。問題実施・採点・レポートの仕様は変えず、色・文字・配置とCSSの管理境界を揃えています。

## 責務と読込順

| ファイル | 管理するもの |
| --- | --- |
| `learning.css` | 基本色・フォント・寸法のCSS変数、ページ、カード、開始画面、ボタン・フォーム、問題文・選択状態・自信度の列、操作列、フォーカス、共通のレスポンシブ調整 |
| `actual.css` | 残り時間、時間切れ間近の表示、右側の番号一覧、現在位置・回答済み・見直しフラグ、Actualの画面構成 |
| `drillPage.css` | 問題数・カテゴリ・難易度の設定、確定後の正解／不正解、即時解説、Drillの通知・画面構成 |
| `resultReview.css` | 終了後の解説カード、理解度ボタン、復習フラグ、理解度未入力の注意表示 |
| `resultOutput.css` | レポート確定、コピー・CSVボタン、本文欄 |
| `launcher.css` | モードを選ぶ入口のカード配置 |

各モードは `learning.css` → モードCSS → 結果・出力CSS の順に読み込みます。入口は `learning.css` → `launcher.css` です。

基本デザインを変える場合はlearning.css、即時解説のように特定モードだけの表現ならモードCSS、結果表示だけの表現なら対応する結果CSSを変更します。同じ部品の基本色や寸法をモードごとに追加しないでください。

## HTMLの共通クラス

| クラス | 役割 |
| --- | --- |
| `learning-page` | bodyに付ける現行ページの目印。基本スタイルと共通フォームの適用範囲 |
| `learning-start` | 開始画面の共通最大幅 |
| `learning-category` / `learning-question` | カテゴリと問題本文 |
| `learning-confidence-grid` | 自信度の選択肢を並べる共通グリッド |
| `learning-navigation` | 前後移動・見直し・終了確認などの操作列 |

JSが利用する既存のID・クラスは残しています。例えばDrillの `control-box` に `learning-navigation` を追加しており、進行処理のセレクターを変更していません。Actualのラジオ選択肢 `.choice` とDrillの `.option-btn` は、共通CSSで枠・文字・選択状態を揃えています。

## テーマと寸法の変更

色や基本寸法は `--learning-*` 変数にまとめています。デフォルト値はlearning.cssの先頭で管理します。

例として、別の配色にする場合は、learning.cssの後に読み込む専用CSSで次のように上書きできます。

```css
body.learning-page {
  --learning-color-primary: #6b3fa0;
  --learning-color-primary-hover: #4f237d;
  --learning-color-primary-soft: #f3eaff;
}
```

これはCSSの拡張方法であり、confにtheme項目を追加したものではありません。通常時・ホバー時・選択背景の色を組にして指定してください。

主な変数:

- `--learning-font-family`: 問題・操作・現行結果カードの基本フォント。
- `--learning-color-primary` / `primary-hover` / `primary-soft`: 主操作・選択枠・選択背景。
- `--learning-color-text` / `muted` / `surface` / `page`: 文字と背景。
- `--learning-color-danger` / `success` / `warning`: 状態の意味を持つ色。それぞれの薄い背景も定義。
- `--learning-color-focus`: キーボードフォーカス。
- `--learning-content-width` / `start-width`: ページ・開始画面の最大幅。
- `--learning-control-height` / `review-control-height`: 操作の最小高さ。現行値は44px／理解度の補助ボタン40px。
- `--learning-control-radius` / `card-radius`: 基本の角丸。

レポート出力ボタンは用途別の色も変数化しています。共通のホバー指定は低い詳細度にして、状態色や出力ボタンの色を上書きしないようにしています。

## 小さい画面での配置

800px以下のカード余白、ページ余白、ヘッダー、自信度の1列化はlearning.cssで共通管理します。

Actualのサイドバーを下へ送る処理と番号一覧の列数はactual.css、600px以下でのDrillの操作ボタンの折返しはdrillPage.cssに残しています。レポート出力ボタンの縦並びはresultOutput.css、入口の1列化はlauncher.cssが担当します。

## 旧ページとの関係

旧ページの `drill.css` / `style.css` は変更していません。現行ページにはlearning-pageを付け、旧ページへ基本CSSを追加していません。

旧drillでも共用するresultReview.css／resultOutput.cssには、CSS変数が存在しないときの従来値を指定しています。共通化後も旧ページで理解度の選択色や出力ボタンを表示できます。

## 検証

```sh
scripts/check-standard.sh --browser
```

基本の問題実施・出力に加え、`tests/standard/styles.browser.cjs` が次を確認します。

- 両モードの開始画面・問題文・回答の選択状態の描画。
- 320／390／768px幅での問題画面・結果画面の横はみ出しと、自信度の1列化。
- 共通変数の上書きが両モードの選択状態・理解度・レポートに反映されること。
- selectとtextareaのキーボードフォーカス。
- 出力ボタンのホバー時に、色付き背景が共通ボタン色で消えないこと。
- 確定したDrillの選択肢を薄くせず、正誤を読める状態にすること。
- learning.cssを読まない旧drillで従来値のフォールバックが働くこと。

状態色はCSSの遷移完了後に検証します。`CBT_TEST_SCREENSHOT_DIR` を指定すると確認用画像も保存します。画像は通常のテスト実行では生成せず、現行ランタイムにも含めません。
