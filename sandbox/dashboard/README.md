# Dash機能確認

専用環境の準備（リポジトリのルートで実行）:

```sh
python3 -m venv /workspace/.venvs/wbc-lms
/workspace/.venvs/wbc-lms/bin/python -m pip install -r sandbox/dashboard/requirements.txt
```

## Iris：グラフ間の連動

```sh
cd /workspace/WBC_LMS/sandbox/dashboard
/workspace/.venvs/wbc-lms/bin/python app_1.py
```

ポート8050。品種選択、点クリック、範囲選択、複数グラフの条件交差、KPI・表の連動、条件解除を確認できます。折れ線の横軸はサンプル番号で、時系列ではありません。

## Bike：時系列と標準操作

```sh
cd /workspace/WBC_LMS/sandbox/dashboard
/workspace/.venvs/wbc-lms/bin/python bike_app.py
```

ポート8051。日別／時間別の切替、期間・天候・勤務日の絞り込み、KPI、日別推移、曜日／時間帯平均、気温との散布図、表の並べ替え・列フィルター、CSV出力、全条件リセットを確認できます。Bikeのグラフ自体の選択は他のグラフを絞り込みません。

表内フィルターは表だけに適用され、CSVは上部の条件に一致する全行です。日別と時間別を重複加算せず、欠けた時間を0補完しません。元データのtempを41倍して摂氏へ換算しています。一般／登録は利用回数で、ユニーク人数ではありません。

添付のBike Sharing Datasetをdata/bikeに保持しています。2011–2012年、day.csvは731行、hour.csvは17,379行。出典と列定義は同フォルダのReadme.txtを参照してください。

## 既存Iris検証

リポジトリのルートで（ブラウザ検証はIrisサーバー起動後）:

```sh
/workspace/.venvs/wbc-lms/bin/python -m unittest discover -s sandbox/dashboard/tests -p test_iris_crossfilter.py -v
node sandbox/dashboard/tests/iris.browser.cjs
```

## 入門用：sample_dsbd_iris.py

```sh
cd /workspace/WBC_LMS/sandbox/dashboard
/workspace/.venvs/wbc-lms/bin/python sample_dsbd_iris.py
```

ポート8052。既存のapp_1.pyとは別に起動します。

1. 全150行のKPI・表を確認する。
2. Speciesを選び、全表示が50行の品種に連動することを確認する。
3. 散布図の横軸・縦軸を切り替える。KPIの平均と標本標準偏差は横軸の測定項目に対応する。
4. 点をクリック、またはドラッグで範囲選択する。KPI・他のグラフ・表が連動する。
5. 棒グラフの品種を選択し、複数条件の共通部分に絞られることを確認する。
6. 各グラフの選択解除、同じ点の再クリック、すべてリセットを試す。リセットは選択条件を解除し、測定軸の指定は保持する。
7. 表を並べ替え、抽出結果のCSVを保存する。CSVはページ内だけでなく抽出された全行。

グラフは自身の選択条件だけを除いて表示し、選択を広げ直せるようにしています。選択された点は強調し、他のグラフ・KPI・表には全条件を適用します。該当0行、1行の場合の表示も確認できます。折れ線はサンプル番号順であり、時間的な変化を表しません。

コードを読む順序：Layout → 選択コールバック → 描画コールバック → CSVコールバック。Inputは更新のきっかけ、Outputは更新先、Stateは実行時に参照する値です。dcc.Storeはブラウザごとの選択状態を持ち、共通データを書き換えません。選択・集計の補助関数はiris_crossfilter.pyを参照します。

新サンプルの連動・モバイル検証：

```sh
IRIS_TEST_URL=http://127.0.0.1:8052 node sandbox/dashboard/tests/iris.browser.cjs
```

## 表示条件の復元・共有

sample_dsbd_iris.pyでは、品種・測定軸・各グラフの選択条件を同じタブのsessionStorageに保持します。再読み込みしても復元され、独立したブラウザセッションへ自動的に漏れません。

「現在の条件を開く・共有する」のリンクをコピーすると別のブラウザでも同じ条件を再現できます。URLにはバージョン、品種、測定軸、選択した行IDだけを含めます。データ表の並べ替え・ページ番号、グラフのズームは共有対象外です。共有URLを開いた場合やそのURLを再読み込みした場合はURLの条件が優先されます。その後操作した条件を共有したい場合は、新しいリンクをコピーしてください。

URLの入力検証はiris_view_state.pyに分離しています。形式・品種・測定軸・行IDを検証し、無効なURLは説明付きで初期条件に戻します。0行の選択は無効条件とは区別して保持します。認証・アクセス制御の仕組みではありません。

追加の検証コマンド（リポジトリルート、サーバー起動後）:

```sh
/workspace/.venvs/wbc-lms/bin/python -m unittest discover -s sandbox/dashboard/tests -p 'test_*.py' -v
node sandbox/dashboard/tests/sample_iris.browser.cjs
node sandbox/dashboard/tests/iris_state.browser.cjs
```

テストの対象・実行結果・未確認事項は [Irisのテスト記録](TEST_RECORD_IRIS_20261101.md) にまとめています。

## 時系列BI：sample_dsbd_bike.py

```sh
cd /workspace/WBC_LMS/sandbox/dashboard
/workspace/.venvs/wbc-lms/bin/python sample_dsbd_bike.py
```

ポート8053。既存のbike_app.py（8051）は変更していません。初期表示は前年と比較できる2012年です。

1. 主グラフをドラッグでズーム、下部のレンジスライダーで範囲を変更する。ここではKPI・表は変わらない。
2. 「表示期間を全体に適用」を押すと、表示範囲の境界を含む日単位でKPI・各グラフ・明細・CSVへ適用する。時刻単位の切り出しではない。
3. 「ひとつ戻る」で前の期間・粒度へ戻る。
4. 月の点をクリックして日別へ、日の点をクリックして時間別へ進む。時間別は必ずhour.csvを使用。日別データを24時間分へ水増ししない。
5. 日・週・月・時間を切り替え、一般／登録／全利用と合計／観測行平均を比較する。
6. 前年同月日比較・7日移動平均・基準線を確認する。天候・勤務日を絞り込み、0行になった場合も確認する。
7. CSVと明細の件数を確認する。「初期表示に戻す」は期間・集計元・粒度・指標・集計方法・天候・勤務日・履歴・ズームを初期化する。

集計の注意点：

- 週は月曜始まり。期間境界の週・月は選択期間内の行だけを集計する。
- 合計は貸出回数、平均は実際に抽出された元データ1行あたり。日別と時間別では平均の分母が異なる。各バケットの平均を単純平均して全体平均にはしない。
- 欠損やフィルター除外を0補完しない。実際の0と未観測を区別する。未観測時間数は元のhour.csvを基準に計算し、天候・勤務日フィルターの除外件数とは分ける。
- 前年比較は同じ月日で、同じ天候・勤務日条件を適用。曜日や天候自体が同一という意味ではない。2月29日や2010年の未収録データは空白。
- 移動平均は選択期間内の直近7暦日が全て観測されている場合だけを表示する。初めの6日や欠損を含む窓は表示しない。
- ドリルダウン・ズーム適用の履歴で期間と粒度を戻す。手動で期間・粒度を変更すると履歴を解除する。指標等のフィルターは戻る操作の対象外。

実装の読み方：bike_timeseries.pyが抽出・集計・前年対応を担当し、sample_dsbd_bike.pyのnavigateが操作→期間・粒度、renderが共通条件→全表示、exportが同じ条件→CSVを担当します。更新中はdcc.Loadingで待機表示します。

検証（リポジトリルート。ブラウザはサーバー起動後）：

```sh
/workspace/.venvs/wbc-lms/bin/python -m unittest discover -s sandbox/dashboard/tests -p 'test_*.py' -v
node sandbox/dashboard/tests/bike_timeseries.browser.cjs
```

[時系列機能のテスト記録](TEST_RECORD_BIKE_20261101.md) を参照してください。
