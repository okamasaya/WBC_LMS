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
