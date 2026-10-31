# Prototypeの入口と開発資産

現行の標準問題は `language/JLPT_N2/index.html` から実施します。

- 練習: `Drill_N2_261031.html`
- 模擬試験: `Actual_N2_261030.html`
- 共通設定: `conf_JLPT_N2_LK.json`

実行手順とassetsの役割は [標準基盤の説明](../docs/standard/README.md)、開発途中のページ・プロンプト・過去データの位置は [開発資産の一覧](../docs/standard/development-assets.md) を参照してください。

このフォルダには現行版と開発履歴が同居しています。現行版の既定構成で使うファイルは、リポジトリのルートから `node scripts/audit-standard-runtime.mjs --json` で確認できます。`public` への展開はまだ行っていません。

## 開発記録

- [2026-10-30〜10-31：環境準備、Actual／Drill共通化、assets整理とToDo](DEVELOPMENT_LOG_20261030-20261031.md)
- [2026-10-31：共通CSS・モード別表示の整理と検証](DEVELOPMENT_LOG_20261031_CSS.md)
