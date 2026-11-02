# N2ダミーデータを使い始める入口・01

新しい作業の入口を枝番01で追加しました。既存のデータ・画面は保持し、検証済みの全領域画面を再利用します。

| 比較対象 | 起動モジュール（`sandbox.dashboard.bkt.`の後ろ） | データ | ポート |
|---|---|---|---:|
| 既存版 | `learning_dashboard` | 言語知識のみ・5回・150回答 | 8056 |
| 新しい名前の全領域版 | `n2_learning_dashboard_01` | 言語知識・読解・聴解・15回・1,605回答 | 8058 |

新しい入口は`data/mock_jlpt_n2_full_15_sessions/learning_logs.sqlite3`を使います。先に作った`full_learning_dashboard`（8057）と同じ全領域データ・画面です。旧データと新データの対象・件数が異なるため、正答率の差を学習効果として比較するものではありません。

- `n2_learning_data_01.py`：SQLiteの読込と全体・領域・回次の集計。画面を起動せず利用でき、標準ライブラリだけで動作。
- `n2_learning_dashboard_01.py`：データ確認後に画面起動。既定ポート**8058**。既存8055〜8057と併用可能。

## データ確認だけ実行

リポジトリルート`/workspace/WBC_LMS`から:

```sh
/workspace/.venvs/wbc-lms/bin/python -m sandbox.dashboard.bkt.n2_learning_dashboard_01 --check
```

15回・1,605回答、言語知識810／読解315／聴解480回答と表示します。DBの生成や書き換え、サーバー起動は行いません。

## 画面起動

同じディレクトリから:

```sh
/workspace/.venvs/wbc-lms/bin/python -m sandbox.dashboard.bkt.n2_learning_dashboard_01
```

ポート8058で全領域画面を起動します。必要なら`--port 8060`等を指定。画面操作と指標は[全領域版の説明](FULL_LEARNING_DASHBOARD.md)と同じです。今回の01は新しい起動・読込入口で、独自の画面レイアウトを追加したものではありません。

## Pythonから利用

```python
from sandbox.dashboard.bkt.n2_learning_data_01 import load_records, make_summary

records = load_records()  # 全領域SQLiteを読み取り専用で開く
report = make_summary(records, domain='読解', group='内容理解')
print(report['overall'])  # 短文・中文、15回・210回答の集計
```

JSONで領域別に確認する場合:

```sh
/workspace/.venvs/wbc-lms/bin/python -m sandbox.dashboard.bkt.n2_learning_data_01 --domain 聴解
```

正答率・自己申告理解度・独立モデル試算の定義は維持します。公式尺度得点・合否・累積習得率とは扱いません。

## 今回の確認

2026-11-02、`--check`で15回・1,605回答と領域別件数を確認。集計APIで全体・読解の内容理解210回答・該当なしの条件とDBバイト不変を確認しました。8058で起動し、既存の`full_learning.browser.cjs`を`BKT_FULL_TEST_URL=http://127.0.0.1:8058`で実行して成功。段階絞り込み・CSV出力・SQLite／CSV一致・モバイル表示を検証しました。今回既存画面のロジックは変更していません。
