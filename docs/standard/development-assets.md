# 現行版と開発資産の区分

ファイルが存在することと、現行版がそのファイルを使用していることを区別します。今回、旧ページ・問題データ・制作プロンプトは削除・移動していません。既存URLと開発時の参照を保ちます。

| 区分 | ファイル・場所 | 扱い |
| --- | --- | --- |
| 現行の問題実施 | `prototype/language/JLPT_N2/Actual_N2_261030.html` / `Drill_N2_261031.html` | 今後の基準。`index.html`から起動 |
| 現行の出題データ | 同フォルダのconfが指定する`JLPT_N2_LK_Ch.json` / `Vo.json` / `Gr.json` | 問題を改訂する際の確認対象 |
| 旧実装・比較元 | 同フォルダの`Edit_drill.html` / `Edit_drill_260820.html` / `separete_drill_261026.html` | 分割・移行の経緯と回帰確認用。現行入口には表示しない |
| 旧設定・旧ローダー | `config.js` / `drillConfig.js` / `questionLoader.js` / `questionLoader_old.js` | 旧ページの再現・比較用。現行ページの依存対象から除外 |
| 開発段階の画面 | 同フォルダの`test_version/` | 検討・実験の履歴。現行ランタイムとは区別 |
| 教材制作の思考資産 | 同フォルダの`prompt/`、`docs/development/`、`docs/design/`、`docs/decisions/` | 問題生成・解説改善・設計の経緯。削除せず制作側で管理 |
| 過去データ | 同フォルダの`data/old/` | 問題改訂の履歴。現行confには指定していない |
| 検討中の教材 | 同フォルダの`data/JLPT_N2_LK_Vo_Lv1-5_Phase3_unified.json` | 現行confには未指定。採用する場合は明示的な差し替えと検証を行う |
| 制作補助 | 同フォルダの`data/conv_CSV_JSON.py` | CSVから教材を作るための補助。ブラウザ実行には不要 |
| 実験領域 | `sandbox/`、他試験の既存prototype | 今回のN2標準基盤の検証範囲外。未確認のまま移行・削除しない |
| 公開領域 | `public/` | 今回は変更していない。展開の方法と対象は後日決める |

旧版は一部の共通JSを現行版と共用しています。旧HTMLを完全に独立した過去バージョンとして再現する必要がある場合は、Gitの当時のコミットを参照してください。

## 変更の記録

今回の配置整理:

- `assets/js/cbt/app.js` / `examCore.js` → `assets/js/actual/`
- `assets/css/cbt.css` → `assets/css/actual.css`
- `assets/js/cbt/tests/` → リポジトリ直下の`tests/standard/`
- assets配下の説明資料 → `docs/standard/`（旧パスに移転先への案内を残し、資料リンクを維持）
- 現行の問題IO・検証・変換 → `assets/js/shared/questionLoader.js`

HTML・設定・問題データの現行URLは維持しました。新しい実施入口と依存関係の定義・点検コマンドを追加しました。
