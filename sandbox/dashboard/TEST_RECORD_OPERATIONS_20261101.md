# Dashのローカル運用機能：テスト記録（2026-11-01）

## 今回の目的と対象

「まず分析画面とローカル動作を充実」という利用形態に合わせ、sample_dsbd_bike.py（8053）へ、CSV／SQLite切替、手動／定期再読込、読込確認時刻、入力検証・更新失敗時の前版保持、版別キャッシュ、明細のサーバー側ページング・並べ替え、PNG、印刷／PDF保存を追加した。

bike_data_service.pyがデータ版とキャッシュを管理し、bike_timeseries.pyは任意の検証済みフレームを渡せるようにした。元CSV・既存Iris画面は変更していない。ローカルSQLiteとPythonキャッシュはGit管理外。

## 実行証跡

- 開始: 2026-11-01T18:33:44.642609+09:00
- 終了: 2026-11-01T18:34:01.792268+09:00
- 基点: `976e22a5171a623f703dedc6108e05dbe759f49e`（今回の変更を含む検証ソースはメタデータ内のSHA-256で特定）
- バージョン: {'python': '3.12.14', 'dash': '4.4.1', 'plotly': '7.1.0', 'pandas': '3.1.0'}
- 作業ディレクトリ: `/workspace/WBC_LMS`。専用仮想環境でサーバーを起動、Playwright 1.62.1 / Chromium 154.0.8037.57で操作。
- Pythonは47件（既存37件＋更新・DB・キャッシュ等10件）：成功47、失敗0、エラー0、スキップ0。
- ブラウザ2スクリプトとベンチマークは別の検証で、単体テスト件数へ加算しない。

| 検証 | 終了コード | 生ログ |
|---|---:|---|
| python | 0 | [ログ](test-records/20261101_183344_operations_python.log) |
| timeseries_browser | 0 | [ログ](test-records/20261101_183344_operations_timeseries_browser.log) |
| operations_browser | 0 | [ログ](test-records/20261101_183344_operations_operations_browser.log) |
| benchmark | 0 | [ログ](test-records/20261101_183344_operations_benchmark.log) |

[メタデータ・コマンド・ソースハッシュ](test-records/20261101_183344_operations_metadata.json)

## 機能別の確認

| 項目 | 期待値・結果 | 方法 |
|---|---|---|
| CSV再読込 | 同内容は同版、変更後は別版 | Python |
| SQLite接続 | 実DBからの読取で全期間3,292,679回。日・時間両テーブルへ1回を追加すると3,292,680回 | Python・実SQL |
| DB画面 | 2012年2,049,576回がCSV／SQLiteで一致 | ブラウザ |
| 再読込失敗 | 不正列・負数・日時間不一致を拒否。HTTP応答200で説明し、ブラウザの版を変更しない | Python／Flask HTTP |
| データ版 | DB更新後は再計算、既存画面のCSVは既存版のまま。保存期限切れは再読込を案内 | Python |
| キャッシュ | 同条件はhit、版が違えばmiss。呼出側の書換えが保存結果へ漏れず、LRU上限を守る | Python |
| 手動更新 | ボタンから実際のHTTP再読込を実行し、同内容の集計キャッシュを再利用 | ブラウザ |
| 定期更新 | dcc.Intervalから実HTTP再読込。既定60秒をテスト内だけ1秒へ短縮し、タイマー発火を確認 | Python／ブラウザ |
| ページ転送 | 15行でページ送り、全データに対する数値並べ替え、範囲外ページの補正 | Python／ブラウザ |
| 期間操作 | レンジスライダーのハンドルを実ドラッグ。KPIは変わらず、適用後に全体が絞られ、戻るで復帰 | ブラウザ |
| PNG | カメラから実ダウンロード、PNG形式を確認。日本語のタイトル・軸を目視確認 | ブラウザ／画像確認 |
| 印刷・PDF | ボタンがwindow.printを呼ぶことを確認。別途ChromiumでPDF生成、日本語テキスト抽出と通知混入なしを確認 | ブラウザ／pdftotext |
| 既存分析 | ズーム、ドリルダウン、復帰、指標・粒度・平均、空データ、モバイル、JS／HTTPエラーなし | timeseries_browser |

印刷ダイアログはヘッドレスでは操作せずwindow.printをテスト用に差し替えて呼出を検証。PDF生成はChromiumの印刷機能で別途確認した。OS固有の保存ダイアログは未確認。

[実際の日本語PNG](test-records/20261101_183344_bike_series.png) ／ [実際の印刷PDF](test-records/20261101_183344_bike_print.pdf)

## 合成データの集計測定

100万行は実時間別データを繰り返して作った関数検証用の合成観測。元CSVやSQLiteを100万行に置き換えていない。各粒度で総数189,023,818回が保たれることをassertで確認した。

| 粒度 | 集計時間 ms | バケット数 |
|---|---:|---:|
| M | 56.066 | 24 |
| W | 36.854 | 106 |
| D | 36.887 | 731 |
| H | 29.125 | 17544 |

月別キャッシュ初回 40.193 ms、hit 0.034 ms。hit=1、miss=1で、結果一致を検証。

時間は今回のマシンでの参考値。速度比や合格基準を設定しておらず、100万行を含むブラウザ・CSV検証・DB読取・同時利用者の負荷試験ではない。

## 開発中の検出と修正

- 更新後のKPIがDOMへ入っていてもLoading表示が残っているタイミングがあり、テストのinnerTextが空になった。通信とKPIの可視化完了を待つようテストを修正した。
- PNG保存直後の通知が印刷PDFへ混入することをPDFテキスト抽出で検出。印刷CSSでPlotly通知を非表示にし、日本語の見出し・移動平均の文字が残り、通知が含まれないことを再確認した。
- SQLiteの2テーブルは同一読取トランザクション、更新失敗時は検証済みの前版を保持。テストのDB変更は一時フォルダーのみで実施した。

CSV保存は、版の保存期限切れなどで実行できない場合も再読込を案内するようにした。最終コードで上記一式を再実行している。

その前の成功した一式も、[18:32:34の実行メタデータ](test-records/20261101_183234_operations_metadata.json)と各ログに保持している。CSV保存の案内追加前の結果で、最終結果とは分けて参照できる。

## 再実行

専用環境でsample_dsbd_bike.pyを先に起動し、リポジトリルートで以下を実行。

```sh
/workspace/.venvs/wbc-lms/bin/python -m unittest discover -s sandbox/dashboard/tests -p 'test_*.py' -v
node sandbox/dashboard/tests/bike_timeseries.browser.cjs
node sandbox/dashboard/tests/bike_operations.browser.cjs
/workspace/.venvs/wbc-lms/bin/python sandbox/dashboard/tests/benchmark_bike.py --rows 1000000
```

PNG・PDFは運用ブラウザテストが/tmpへ出力する。PDFの文字検証にはpdftotextを使用。分析画面を動かすだけなら追加パッケージ不要。

## 制約・未実施

- 単一プロセスのローカルサンプル。キャッシュ最大16条件、スナップショット最大8版。再起動でメモリー状態は消える。分散・複数ワーカー・多人数の負荷試験は未実施。
- CSV／DBの対応期間は2011〜2012年に固定。新年度や実業務データへの適用はスキーマ・期間の設計が別途必要。
- 印刷の表は現在ページのみ。全明細はCSV。自動PDF配信や帳票テンプレートではない。
- 初回のSQLiteはCSVのコピー。以降のCSV変更はSQLiteへ自動同期しない。
- 自動更新60秒の実時間待機は行わず、1秒のテスト用間隔で同じIntervalの経路を確認。
- バックグラウンドジョブ、認証、権限、監査、通知・定期配信、外部DB接続は未実装・未実施。
- Iris・ALP・JLPTのブラウザ検証は今回は実行せず、既存Pythonテストを含む47件で回帰確認。

[最新の機能確認一覧](FEATURE_CHECKLIST.md)で、実施済みと対象外を確認できる。
