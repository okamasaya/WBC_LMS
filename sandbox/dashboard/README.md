# Dash機能確認

N2の言語知識・読解・聴解を含む[全領域版は8057](bkt/FULL_LEARNING_DASHBOARD.md)。リポジトリルートで`python -m sandbox.dashboard.bkt.full_learning_dashboard`を実行します。架空学習者1人×15回×107問のSQLite／同内容CSVで段階的な絞り込みを確認できます。

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

## ローカルでの更新・接続・出力

sample_dsbd_bike.py（8053）に次の機能を追加しました。requirementsの追加は不要です。

- **接続先**：CSV／SQLiteを切替。SQLiteは初回だけCSVから`.local/bike.sqlite3`を作ります。以降はDB自体を読み、CSVを自動で再取り込みしません。`.local/`はGit対象外です。
- **更新**：「データを再読込」または「60秒ごとに再読込」。表示する時刻は読込確認時刻（JST）で、2011〜2012年のサンプルを現在の実データと誤解しないようにしています。
- **失敗時**：必須列、整数・範囲、重複日時、回数整合性、日別と時間別の日次合計を検証。失敗時はエラーを示し、前回のデータを保持します。
- **版管理**：内容のハッシュでデータ版を判定。同じデータの再読込では計算を再利用し、内容が変われば再集計。CSV出力も、その画面のデータ版を使います。
- **キャッシュ**：公開サンプルの集計結果だけをプロセス内で最大16条件分保存。利用者の選択条件そのものは共有しません。「開発用の処理情報」で計算時間とhit/missを確認できます。
- **表**：サーバーで全明細を並べ替えて、1ページ15行だけを転送。CSVには抽出された全行を含めます。
- **PNG**：各グラフ右上のカメラボタンで日本語ラベル付きの画像を保存。
- **印刷・PDF**：「印刷・PDF保存」でブラウザの印刷ダイアログを開く。印刷先からPDFを選んでください。表は表示中のページだけです。自動配信や全明細帳票ではありません。

### SQLite更新の試し方

元CSVを変更せず、ローカルDBで2012年1月1日の貸出を1回増やす例です。再読込前後のKPIを比較できます。

```python
import sqlite3
with sqlite3.connect('sandbox/dashboard/.local/bike.sqlite3') as conn:
    conn.execute("UPDATE day SET casual=casual+1, cnt=cnt+1 WHERE dteday='2012-01-01'")
    conn.execute("UPDATE hour SET casual=casual+1, cnt=cnt+1 WHERE dteday='2012-01-01' AND hr=0")
```

両方を同じトランザクションで更新します。元に戻す場合は同じ条件で`+1`を`-1`へ置き換えます。片方だけ変更すると整合性検証で失敗し、前回の画面が維持されます。テストでは一時フォルダーのDBを使い、実際のCSVや`.local`のDBを変更しません。

### 保存と性能の範囲

このサンプルは単一Pythonプロセスでのローカル動作を対象とします。メモリー上のスナップショットは最大8版で、期限切れの画面は再読込を案内します。キャッシュ・更新時刻・履歴は永続保存や複数ワーカー間共有ではありません。DBパスはサンプル内で固定し、画面から任意のSQLは実行しません。

100万行のベンチマークは集計関数だけを測る合成データです。CSV入力検証、描画、ネットワーク、複数利用者を含む100万行対応を保証するものではありません。

```sh
/workspace/.venvs/wbc-lms/bin/python -m unittest discover -s sandbox/dashboard/tests -p 'test_*.py' -v
node sandbox/dashboard/tests/bike_operations.browser.cjs
/workspace/.venvs/wbc-lms/bin/python sandbox/dashboard/tests/benchmark_bike.py --rows 1000000
```

[機能確認一覧](FEATURE_CHECKLIST.md) と [更新・出力・性能のテスト記録](TEST_RECORD_OPERATIONS_20261101.md) に対応状況をまとめています。

## 開発記録

- [2026-11-01：DashによるBI機能確認の経緯・実装・検証・保留事項](DEVELOPMENT_LOG_20261101.md)

## 再確認記録

- [2026-11-02：エラー表示の報告を受けた時系列・更新機能の再確認](TEST_RECORD_RECHECK_20261102.md)

## ALP–BKTの作業領域

既存の推定・CSV取込・ALP画面・設定・専用CSS・テストを [bkt/](bkt/README.md) へ整理しました。新しい入口はリポジトリルートで`python -m sandbox.dashboard.bkt`（8054）です。旧alp_app.py（8051）と従来の全体テストは互換入口として残しています。

モデルだけの利用方法、資料、次の進め方は [BKT README](bkt/README.md) を参照してください。Iris・Bikeの保留事項とは別の作業です。過去のログ・ハッシュ内のパスは当時の配置として保持しています。

### BKTの正誤中心・補助2項目モデル

自信度と解説後の理解度を補助に使う初版を [bkt/ASSISTED_MODEL.md](bkt/ASSISTED_MODEL.md) に追加しました。各回答を同じ事前確率から独立に評価する未校正の実験モデルです。

リポジトリルートで`python -m sandbox.dashboard.bkt.flat_app`（8055）。標準BKTの8054画面と分けて、32パターン、段階比較、CSV・仮定JSONを確認できます。[開発ログ](bkt/DEVELOPMENT_LOG_ASSISTED_20261102.md) と [テスト記録](bkt/TEST_RECORD_ASSISTED_20261102.md) も保存しています。

8055には[実CSVの取込](bkt/README.md#実csvを8055画面へ読み込む)も追加しました。現行prototypeのQuestionResult・統合Raw・Sessionをまとめて選択でき、同じ回答を二重計上せず、正誤・自信度・解説後の理解度で独立回答の補助モデルを確認できます。点数は使いません。

さらに[5回分のSQLiteダミーDB](bkt/data/mock_jlpt_n2_5_sessions/README.md)を同梱しています。8055で「JLPT N2・5回分（SQLite）」を選ぶと150回答を読み込めます。利用者提供の[3種CSV原本](bkt/data/prototype_exports/SESS_1793573633671/README.md)も保管しました。

### JLPT N2の20回分モック

[bkt/data/mock_jlpt_n2_20_sessions/](bkt/data/mock_jlpt_n2_20_sessions/README.md)に、架空学習者1人・20回・各30問の600回答をCSVで保存しています。回答はQuestionResult.csv、回次別の概要はSession.csvです。生成条件・列定義・SQLite案・[検証記録](bkt/TEST_RECORD_MOCK_DATA_20261102.md)も参照できます。8055の「JLPT N2・20回分のモック」から確認できます。

学習結果をまとめて見る[新ダッシュボードは8056](bkt/LEARNING_DASHBOARD.md)です。SQLiteを標準とし、大問題別の正解率・自己申告理解度・モデル試算を分けて表示します。同じ5表のCSV控えも用意しました。今回はこの初版をブレイクポイントとして記録しています。
