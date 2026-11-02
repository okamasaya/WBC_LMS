# 2026-11-02 N2全領域モックの検証

対象は`full_mock_dataset.py`、`full_learning_dashboard.py`と共通リーダーの領域・分類・実施回フィルター追加です。最終コードのサーバーを再起動してブラウザ検証しました。

## 結果

| 検証 | 結果 |
|---|---|
| dashboard全体のPython unittest | **123件成功、失敗0、skip 0**（従来117＋新規6） |
| 全領域8057 Playwright | **成功** |
| 既存8056 Playwright回帰検証 | **成功** |
| SQLite integrity_check／foreign_key_check | **ok／違反なし** |
| SQLite全5表とCSVの全列・値・順序 | **一致** |
| 生成器の再実行と異なる既存ファイルの保護 | **成功** |
| 既存5回データ12ファイル | **HEADとバイト一致** |
| 従来モデル入力アダプターで全領域DB読込 | **1,605回答推定、除外0** |

Pythonの新規6テストは、PDFから独立に転記した各大問の配分、全15回の107回答、ID・範囲・回答時刻と受験後理解度記録、再現性、CSV同値性、階層フィルター、件数による加重正答率、空条件の表示、HTTPレイアウトを確認しています。

ブラウザは3領域ごとの810／315／480回答、読解→内容理解→中文→第1回の9回答、対応するCSV・モデル仮定JSON、親変更時の子条件解除、棒クリックでの絞り込み、全条件リセット、SQLite／CSV切替時の同値性、独立モデルへの表示切替、390px幅での横はみ出しなし、JavaScript／HTTPエラーなし、DBハッシュ不変を確認しました。既存8056では従来のKPI・150回答CSV・分類絞り込み・期間選択・SQLite／CSV切替・モバイル表示を再確認しました。

## データの確認値

| 領域 | 正解数 | 回答数 | 正答率 |
|---|---:|---:|---:|
| 言語知識 | 480 | 810 | 59.26% |
| 読解 | 139 | 315 | 44.13% |
| 聴解 | 253 | 480 | 52.71% |
| 全体 | 872 | 1,605 | 54.33% |

全体の自己申告理解度平均は1.9751／3、独立モデル試算平均は34.83%。いずれも合成データの動作確認値です。モデル試算と正答率は混ぜていません。

## 証跡と実行方法

[Python生ログ](test-records/20261102_full_n2/python.log)、[全領域ブラウザログ](test-records/20261102_full_n2/full_browser.log)、[既存画面ブラウザログ](test-records/20261102_full_n2/legacy_browser.log)、[実行環境・コードハッシュ](test-records/20261102_full_n2/metadata.json)、[デスクトップ画像](test-records/20261102_full_n2/screenshots/desktop.png)、[モバイル画像](test-records/20261102_full_n2/screenshots/mobile.png)。

リポジトリルートで実行:

```sh
PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/wbc-lms/bin/python -m unittest discover -s sandbox/dashboard/tests -p 'test_*.py' -v
# full_learning_dashboardを8057で起動後
BKT_FULL_TEST_DIR=sandbox/dashboard/bkt/test-records/20261102_full_n2/screenshots node sandbox/dashboard/bkt/tests/full_learning.browser.cjs
# learning_dashboardを8056で起動後
node sandbox/dashboard/bkt/tests/learning_dashboard.browser.cjs
```

## 今回の検証に含まないもの

公式尺度得点・合否の再現、実問題／音声、共通素材に対する複数設問、モデル校正・学習効果・累積習得率、実ログの書込、複数利用者、公開環境での動作は未検証・未実装です。添付PDFの配分は目安であり、現行公式構成の確認とは区別します。標準CBTのコードは変更しておらず、今回そのブラウザ一式は再実行していません。
