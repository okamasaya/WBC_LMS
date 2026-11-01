# BKTファイル整理のテスト記録（2026-11-02）

## 変更の範囲

既存BKT試作のモデル、CSV取込、架空データ、グラフ、設定、Dash画面、専用CSS、テストをbkt/配下へ移動。モデルはmodel.pyへ改名し、パッケージAPIを設けた。内部importは相対参照へ変更し、新しい起動入口をpython -m sandbox.dashboard.bkt（8054）とした。

旧alp_app.py（8051）、全体テストのtest_bkt.py／test_dashboard.py、旧ブラウザテストの入口は互換用に残した。元BKTモデル・取込・架空データ・描画関数・仮パラメータ・CSSは移動前とバイト単位で同一。これらのハッシュと移動先はメタデータへ記録。

数式・パラメータ・入力判定の変更、パラメータ学習、matplotlib追加、Django導入は行っていない。既存の固定パラメータ試作を次のモデル検証に使えるよう整理した。

## 実行対象

- 基点コミット: `c8467c3e8110ad0b5e7029a603f0fc26c8e8cbc1`
- 開始（JST）: 2026-11-02T05:34:46.338328+09:00
- 終了（JST）: 2026-11-02T05:34:58.794547+09:00
- 対象は基点へ今回の移動・import変更を加えたソース。ハッシュはメタデータで特定。
- 作業ディレクトリ: /workspace/WBC_LMS。既存Python仮想環境・Playwright・Chromiumを使用。
- BKT専用13件は全体47件に含まれる。合計60件とは数えない。

| 検証 | 終了コード | 生ログ |
|---|---:|---|
| bkt_python | 0 | [ログ](test-records/20261102_203446_bkt_python.log) |
| all_python | 0 | [ログ](test-records/20261102_203446_all_python.log) |
| bkt_browser | 0 | [ログ](test-records/20261102_203446_bkt_browser.log) |
| legacy_browser | 0 | [ログ](test-records/20261102_203446_legacy_browser.log) |
| model_only | 0 | [ログ](test-records/20261102_203446_model_only.log) |
| legacy_import | 0 | [ログ](test-records/20261102_203446_legacy_import.log) |

[実行コマンド・終了コード・移動前後の照合・ソースハッシュ](test-records/20261102_203446_metadata.json)

## 確認した動作

- Python：更新式、正誤・パラメータの検証、学習者×スキルの独立性、回答時刻の順序、入力不変、重複・競合・未回答・ID補完の扱い。
- Flask HTTP：レイアウト・コールバック・CSV3種、取込失敗・不正パラメータで古い推定を消す、データクリア。
- ブラウザ：架空24回答の取込と推定、学習者フィルター、既存の問題実施側JSから生成したQuestionResult／統合Rawの実アップロード、同一ID補完の確認、重複除外、CSV保存、異常パラメータからの復帰、モバイル、クリア、JavaScript例外なし。
- 配置：モデル単体を-S（site-packagesを読まない）でimportし、Dash・pandasを読み込まず計算できる。
- 互換入口：旧Python importとHTTP／CSS応答を確認。旧ブラウザ入口はALP_TEST_URLを8054へ指定して、移動したテスト実体を正常に呼び出せることを確認。

## 結果と限界

BKT専用13件・全体47件が成功（失敗・エラー・スキップ0）。新旧のブラウザ入口、モデル単体import、旧画面importも成功。

これは移動後の機能維持の確認。実学習ログに対する予測精度やパラメータの妥当性を実証したものではない。論文本文との照合は未実施。Iris・Bikeのブラウザ検証は今回は実行せず、全体Python47件で回帰確認した。旧入口の8051への実バインドは行わず、新入口8054の実起動と旧import・互換テスト呼出を確認した。

過去のテスト記録は当時のパス・ハッシュのまま保持する。現在の構成・起動と再実行方法は[README](README.md)、資料の確認事項は[資料メモ](references/README.md)を参照。
