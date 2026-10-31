# 標準問題の実施基盤

現行の基準は `Actual_N2_261030.html` と `Drill_N2_261031.html` です。N2の標準4択問題を実施し、結果をレポート・CSVとして出力する部分までを扱います。理解度推定モデルとpublicへの展開は含みません。

## 起動

リポジトリのルートで:

```sh
python3 -m http.server 8000 --bind 127.0.0.1
```

ブラウザで `/prototype/language/JLPT_N2/index.html` を開き、練習ドリルまたはCBT模擬試験を選びます。既存の2ページへの直接アクセス、`?conf=別の設定.json` での設定切替も維持しています。

## 管理する場所

| 区分 | 配置 |
| --- | --- |
| 現行の入口 | `prototype/language/JLPT_N2/index.html` と上記2ページ |
| 試験ごとの設定・教材 | `prototype/language/JLPT_N2/conf_JLPT_N2_LK.json` とそのquestionFilesに指定されたJSON |
| 共通JS | `prototype/assets/js/shared/`（設定、問題読込、結果データ、解説、レポート・CSV） |
| Actual固有JS | `prototype/assets/js/actual/` |
| Drill固有JS | `prototype/assets/js/drill/`（既存の練習エンジンとJSON設定アダプター） |
| 共通CSS | `learning.css`、`resultReview.css`、`resultOutput.css` |
| モード固有CSS | `actual.css`、`drillPage.css`。入口は`launcher.css` |
| 検証 | `tests/standard/`、`scripts/check-standard.sh` |
| 設計・設定の説明 | この`docs/standard/` |
| 旧版・検討資料 | [開発資産の一覧](development-assets.md) |

問題ローダーの現行版は `prototype/assets/js/shared/questionLoader.js` です。旧N2の `questionLoader.js` は旧ページ用に保持しています。現行版は旧設定の`CONFIG`を参照する起動処理を持たず、confが指定した問題データを読み込みます。実データの変換結果が旧版と一致することをテストしています。

`prototype/assets/js/drill/` は旧ページとも共用するため、ファイル名だけで旧版と判断しないでください。`jsonConfig.js` は新Drill専用、`reportGenerator.js` / `dataExporter.js` は共通出力への小さなアダプターです。Drill内部の共有状態をモジュール化する作業は別の変更として扱います。

## 実行用ファイルと開発資産の境界

`prototype/standard-runtime.json` が現行版の入口を宣言します。点検コマンドはHTML、JSのimport、CSSの参照、既定confの問題ファイルをたどります。

```sh
node scripts/audit-standard-runtime.mjs
node scripts/audit-standard-runtime.mjs --json
```

既定のN2構成では33ファイルです。旧設定・過去データへの依存、参照切れ、prototype外の参照を検出すると失敗します。一覧は将来の公開対象を判断する材料で、公開済み・公開審査済みを意味しません。コマンドは一覧化のみで、publicへのコピーや公開は行いません。別confで使う追加教材は、そのconfを含めて別途点検・動作確認してください。

従来ページと開発資料は既存URL・参照を保つために元の場所に残しています。歴史的資料を一括コピーして公開対象にしないでください。

## 検証

```sh
scripts/check-standard.sh
```

依存関係の点検と、設定・出題・変換・集計・レポートの単体テストを実行します。ブラウザ検証はHTTPサーバーを起動した状態で:

```sh
scripts/check-standard.sh --browser
```

ブラウザ検証にはPlaywright（今回の検証は1.62.1）とChromiumが必要です。このクラウド環境では導入済みのものを使っています。別の環境ではそれらを用意してください。ChromiumのパスとサーバーURLは `CBT_TEST_CHROMIUM` / `CBT_TEST_BASE_URL` で変更できます。JSやCSS、設定の配置を変えた場合は、点検とブラウザ検証の両方を行います。

ブラウザ検証では現行2ページの問題実施・設定切替・即時解説・時間切れ・モバイル表示・レポート・CSVと、旧drillの回帰確認を行います。

## 次の拡張に向けた基準

- 現行形式は1問に4選択肢、正解は1つです。共通本文を持つ複数設問・音声問題は未対応です。
- 試験ごとの違いはまずconfと問題JSONで表します。個別の表示や操作が必要な場合は専用部品を追加します。
- N1/N3/TOEICの実データ検証は、教材の用意後に行います。
- 解説理解度と回答時の自信度は学習者の自己申告です。推定した理解度とは区別します。
- 理解度推定に着手する前に、[出力データの意味](results.md#推定処理へ渡す前のデータの意味)を確認します。

CSSの責務・テーマ変数・表示確認は [共通CSSとモード別CSS](styles.md) を参照してください。

詳細: [設定](configuration.md) / [Actual](actual.md) / [結果・レポート](results.md) / [drillの分割経緯](drill-history.md)
