# ALP–BKT：推定・取込・表示の作業領域

2026-11-02に、dashboard直下の既存BKT試作をここへ整理しました。Iris・BikeのBI機能確認サンプルとは分けて、次のモデル検証に進むための配置です。整理時点では数式・入力判定・仮パラメータ・推定結果の意味を変更していません。その後、標準BKTを保持したまま、[正誤中心・補助2項目のフラット試作](ASSISTED_MODEL.md)を追加しました。

## 現在の構成

```text
bkt/
├── __init__.py            # 推定APIの公開（Dashへ依存しない）
├── __main__.py            # python -m sandbox.dashboard.bkt
├── model.py               # 旧bkt.py：標準BKTの計算
├── assisted_model.py      # 正誤中心・補助2項目の独立回答モデル
├── flat_app.py            # 補助モデルの確認画面（8055）
├── mock_dataset.py        # N2のモック学習ログを再生成
├── data/                  # CSV・辞書・manifest・SQLite案
├── learning_data.py       # CSV解析・正規化・除外・重複検出
├── demo_data.py           # 架空の学習ログ
├── bkt_parameters.json    # 手動設定の仮パラメータ
├── alp_app.py             # 既存Dash試作、取込と推定の接続
├── dashboard_views.py     # 推定結果のグラフ
├── assets/                # alp.css、flat.css
├── tests/                 # BKT／取込／画面のPython・ブラウザ検証
├── test-records/           # 今回以降の実行証跡
├── references/            # 参照資料・確認事項
└── TEST_RECORD_REORGANIZATION_20261102.md
```

model.pyは標準ライブラリだけで利用でき、画面やファイルアップロードから独立しています。将来Django側からも同じ推定APIを呼ぶ構成を想定しています。Djangoはまだ導入していません。

## 起動・推定API

リポジトリルートで既存の環境を使います。依存関係は親フォルダーのrequirements.txtで管理し、今回は追加していません。

```sh
/workspace/.venvs/wbc-lms/bin/python -m sandbox.dashboard.bkt
```

新しい入口のポートは**8054**。Iris 8052、Bike 8053、旧Bike基本画面8051と分けています。dashboardフォルダーを作業ディレクトリにする場合は`python -m bkt`でも起動できます。ローカルでは利用する仮想環境のPythonへ読み替えてください。

モデルだけの利用例（リポジトリルート）:

```python
from sandbox.dashboard.bkt import BKTParameters, estimate, update

parameters = BKTParameters(p_l0=0.2, p_t=0.1, p_g=0.25, p_s=0.1)
predicted, posterior, after_learning = update(0.2, True, parameters)
# estimate(records, defaults=parameters) に正規化済みの回答履歴を渡す。
```

APIの返す正答予測、正誤観測後の習得確率、学習遷移後の習得確率は別の値です。実測正答率や自己申告の理解度と混ぜません。

## 以前の入口

- 親のalp_app.pyは互換入口として残し、従来の`python sandbox/dashboard/alp_app.py`は8051で起動します。旧bike_app.pyと同時には起動しないでください。
- `from bkt import BKTParameters, estimate, update`はdashboardがPythonの検索パスにある場合、パッケージの公開APIとして引き続き使えます。
- 親のtests/test_bkt.pyとtest_dashboard.py、および追加したtest_assisted_model.pyは、bkt/tests内のテストを読み込む入口です。整理時の既存47件に今回の17件を加え、全体64件を経て、モック検証10件を追加した全体74件の検証を実行できます。
- 親のtests/browser.cjsは従来のALPポート8051へ接続する互換入口です。新しいテストの既定ポートは8054です。
- learning_data.py、demo_data.py、dashboard_views.py、設定・CSSの実体はこのフォルダーへ移動しました。新しいコードからはパッケージ経由で参照してください。

過去のテスト記録・ソースハッシュ・開発ログ内のパスは、当時の配置を示す証跡として変更しません。旧配置を読む場合はGit履歴も参照してください。

## 検証

サーバーを起動する前でもPythonテストは実行できます。

```sh
# BKTだけ：40件（整理時13＋補助モデル17＋モック10）
/workspace/.venvs/wbc-lms/bin/python -m unittest discover -s sandbox/dashboard/bkt/tests -p 'test_*.py' -v

# 既存Iris・Bikeも含む全体：74件（上の40件を含む）
/workspace/.venvs/wbc-lms/bin/python -m unittest discover -s sandbox/dashboard/tests -p 'test_*.py' -v

# 8054のサーバー起動後
node sandbox/dashboard/bkt/tests/browser.cjs

# 8055の補助モデル画面を起動後
node sandbox/dashboard/bkt/tests/flat.browser.cjs
```

40件と74件は足し合わせません。テストの探索範囲を無差別に広げると互換入口と実体を重ねて実行し得るため、上記のどちらかのPythonコマンドを使ってください。

今回の配置変更に対する結果は[整理のテスト記録](TEST_RECORD_REORGANIZATION_20261102.md)へ保存しています。

## 標準BKTモデルの位置付け

- 標準的な二状態BKT。学習者×スキルごとに、回答日時順の正誤を使って更新します。
- 初期習得確率P(L0)、学習遷移P(T)、当て推量P(G)、誤答P(S)は手動の仮設定です。4択に対応するP(G)=0.25も、実ログから校正した値ではありません。
- 忘却やパラメータの自動学習は実装していません。自信度、解説理解度、難易度、回答時間は現在の推定入力に使っていません。
- QuestionResult.csv／統合Raw CSVを取込可能ですが、ファイルと推定結果は永続保存せず、既存Dash試作で扱います。Djangoによる取込・保存・運用は次の段階です。

## 次に進める順序

1. **モデル構築・検証**：既存の式と入力・出力の意味を確認し、代表的な正誤系列で動作を検証する。必要ならmatplotlibで推移を描く。パラメータを実ログから学習するかは別に決める。
2. **ダッシュボード化**：検証済みの同じ推定APIを使い、既存Dash試作を必要な表示へ整える。
3. **Djangoで外部ファイル取込**：アップロード・検証・必要に応じた保存から、同じモデルと表示へ接続する。Dashとの組込方法はこの接続設計で決める。

現在は、正誤を中心に自信度・理解度を補助に使う初版の計算と確認画面まで進めています。Djangoの取込・保存やパラメータの自動学習は未実装です。Iris・Bikeの「次の仕様として保留」はそのままです。

## 資料

論文が手元にないことは今回の整理を妨げません。基本文献の候補、後で確認したい情報、リポジトリ内の既存資料を[資料メモ](references/README.md)へまとめています。

## 正誤中心・補助2項目のフラット試作

```sh
/workspace/.venvs/wbc-lms/bin/python -m sandbox.dashboard.bkt.flat_app
```

ポート8055。8054の標準BKT画面とは別に起動できます。初版は各回答を同じ初期値から評価し、履歴をつなぎません。自信度で正誤観測の重みを、解説後の理解度で学習遷移を調整します。未校正の仮定であり、実測の理解度や予測精度ではありません。

32通りの合成パターン、1回答の段階比較、既存の架空24回答、CSV、モデル仮定JSONを確認できます。自信度は1が高く4が低い、理解度は0が低く3が高いという元データの向きを保持しています。

- [数式・入力・仮定・実行方法](ASSISTED_MODEL.md)
- [開発ログ](DEVELOPMENT_LOG_ASSISTED_20261102.md)
- [テスト記録](TEST_RECORD_ASSISTED_20261102.md)

## JLPT N2言語知識・20回分のモック

[data/mock_jlpt_n2_20_sessions/](data/mock_jlpt_n2_20_sessions/README.md)に、架空学習者1人・各30問・20回の600回答をCSVで置いています。回答ファイルはQuestionResult.csv、回次別の集計はSession.csvです。列定義・合成フラグ・再生成条件・SQLite用スキーマ案も同梱しています。

8055の画面で「JLPT N2・20回分のモック」を選択できます。現行モデルは各回答の独立評価のままです。永続SQLiteへの移行と、履歴をつなぐモデルはまだ実装していません。

- [開発記録](DEVELOPMENT_LOG_MOCK_DATA_20261102.md)
- [テスト記録](TEST_RECORD_MOCK_DATA_20261102.md)
