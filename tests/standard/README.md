# 標準問題基盤の検証

リポジトリのルートから `scripts/check-standard.sh` を実行します。

`--browser` を付ける場合はPlaywright / Chromiumと、リポジトリを配信するHTTPサーバーが必要です。

- `examConfig.test.mjs`: 共通conf・モード別設定と不正設定
- `examCore.test.mjs`: 出題配分・重複防止・採点・旧ローダーとの全N2問題変換の一致
- `sharedResults.test.mjs`: 生ログ・AIレポート・CSV
- `runtimeBoundary.test.mjs`: 依存関係の不足・旧版への混入の検出
- `jsonDrill.browser.cjs`: 現行Drill、設定切替、Actualの別設定起動、モバイル・異常系
- `browser.cjs`: Actualの問題実施・時間切れ・全出力と、旧drillの回帰確認
- `styles.browser.cjs`: 両モードの共通描画、テーマ変更、狭い画面、キーボードフォーカス、出力ボタンと旧版の配色
- `entry.browser.cjs`: 入口の2ページへの遷移、モバイル、実行資産のネットワーク参照

現在のブラウザテストには、N2の既定条件（Actual 30問、Drill 10問など）を確認する検証もあります。試験の仕様を変える場合はその期待値を確認してください。汎用の設定・集計ロジックは単体テストで別に検証しています。

手順と構成は [docs/standard](../../docs/standard/README.md) を参照してください。これらのファイルは実行用assetsや公開候補一覧には含めません。
