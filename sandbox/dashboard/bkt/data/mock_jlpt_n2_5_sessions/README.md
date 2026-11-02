# N2言語知識・5回分のSQLiteダミーデータ

**架空の学習者1人×5回×30問＝150回答。** 回答はすべて回答済みで、正誤、自信度1〜4、解説後理解度0〜3を含みます。内容は既存の合成生成器と固定seedから作った動作確認用です。実績や学習効果の証拠ではありません。

`learning_logs.sqlite3`をGitで配布し、チェックアウトしたローカルファイルを読みます。GitHub自体がDBサーバーとして動くわけではありません。外部DBサービス・Django・追加Pythonパッケージは不要です。

| ファイル | 内容 |
|---|---|
| learning_logs.sqlite3 | Student・Skill・Question・Session・QuestionResultの5表 |
| schema.sql | 使用したDDL、主キー・外部キー・値の制約 |
| manifest.json | 合成識別、件数、生成条件、元コードとDBのSHA-256 |

## ダッシュボードから使う

```sh
# リポジトリルート。既存のPython環境を使用
python -m sandbox.dashboard.bkt.flat_app
```

`http://127.0.0.1:8055`を開き、「3. 学習ログの取込・明細と出力」のデータ種類で **「JLPT N2・5回分（SQLite）」** を選びます。150回答の推定、正誤フィルター、結果CSV・仮定JSONを確認できます。現在の補助モデルは各回答を独立に評価し、5回分を累積学習したモデルではありません。

## Python API・CLI

```python
from sandbox.dashboard.bkt.sqlite_data import load_database
from sandbox.dashboard.bkt.csv_inference import estimate_import

result = estimate_import(load_database())
# result['records']は150行。任意パスはload_database('path/to/file.sqlite3')。
```

```sh
# 標準ライブラリだけで読込・推定し、件数を確認
python -m sandbox.dashboard.bkt.sqlite_data
# 再生成（異なる既存DBは保護。更新するときだけ --overwrite）
python -m sandbox.dashboard.bkt.sqlite_data --create-demo
```

リーダーは`mode=ro`で開き、DBへ書き込みません。画面操作や推定でGit管理下のファイルは更新されません。CSVをDBへ追記する処理、推定結果のDB保存、複数利用者の運用は今回の対象外です。

保存形式は既存モックの5表スキーマです。QuestionResultの33列は、現行prototypeの41列CSVを丸ごと保存したものではありません。リーダーが推定に必要な14列へ変換し、保存形式にないDataSchemaVersionはNULLにします。正誤・自信度・理解度の意味は共通です。点数・本文・解説を推定へ渡しません。

SQLiteのバイナリは利用するSQLite版で差が出る場合があるため、manifestに版とハッシュを残します。同じ環境の再生成で一致すること、別環境でも論理内容・件数・外部キーが一致することを確認基準にします。原本CSVは[参照用アーカイブ](../prototype_exports/SESS_1793573633671/README.md)に分離しています。

## 学習サマリー画面とCSV控えの追加

[8056の新しい学習画面](../../LEARNING_DASHBOARD.md)では、SQLiteが初期入力です。数値・大問題別正解率・理解度・履歴を確認できます。既存の8055はモデル検証用として保持しています。

SQLiteと同じ5表・同じ150回答の[CSV控え](csv/README.md)も追加しました。`python -m sandbox.dashboard.bkt.dashboard_data --export-csv`でDBから再生成できます。
