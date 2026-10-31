# 共通assets

標準問題の現行基盤:

| 場所 | 役割 |
| --- | --- |
| `js/shared/` | 設定・問題IO・採点データ・解説・レポート・CSV |
| `js/actual/` | 模擬試験の進行 |
| `js/drill/` | 練習の進行。従来の分割drillとも共用 |
| `css/learning.css` | 両モードの基本デザイン |
| `css/actual.css` / `drillPage.css` | モード別の配置・操作 |
| `css/resultReview.css` / `resultOutput.css` | 終了後の共通表示 |
| `css/launcher.css` | 現行版を選ぶ入口 |

ルート直下の旧JSや `css/drill.css` / `style.css` は他のprototype・旧ページ用です。一括削除せず、使用状況を確認してください。

テストは `tests/standard/`、設計・設定の説明は [docs/standard](../../docs/standard/README.md) にあります。実行対象は `prototype/standard-runtime.json` と点検コマンドで区分けします。
