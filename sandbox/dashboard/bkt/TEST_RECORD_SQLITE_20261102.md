# テスト記録：Git配布用SQLiteとCSV原本保管（2026-11-02）

## 対象

sqlite_data.pyの合成DB生成・読み取り専用アダプター、flat_app.pyのSQLite選択、csv_inference.pyの取込元保持、5回分のDBとCSV原本3点。モデルの数式・仮パラメータは変更していない。

- 基点コミット：`f1d0f2fffc01dccaa01129c14d8ad04a45534dc6`。
- 開始JST：2026-11-02T08:28:44.707341+09:00。
- 終了JST：2026-11-02T08:29:04.916241+09:00。
- 新規Python10件、全体105件（BKT関連71件を含む）。105件と71件は足し合わせない。
- SQLite 3.53.1、保存形式mock-storage-v1。
- DB件数：{"Student": 1, "Skill": 9, "Question": 144, "Session": 5, "QuestionResult": 150}。
- 回答は合成150件、正答81・誤答69、除外0。利用者の添付原本とは別データ。

## 実行結果

| 検証 | 終了コード | 生ログ |
|---|---:|---|
| all_python | 0 | [ログ](test-records/20261102_082844_sqlite/all_python.log) |
| sqlite_browser | 0 | [ログ](test-records/20261102_082844_sqlite/sqlite_browser.log) |
| flat_browser | 0 | [ログ](test-records/20261102_082844_sqlite/flat_browser.log) |
| csv_import_browser | 0 | [ログ](test-records/20261102_082844_sqlite/csv_import_browser.log) |
| mock_browser | 0 | [ログ](test-records/20261102_082844_sqlite/mock_browser.log) |
| sqlite_stdlib_cli | 0 | [ログ](test-records/20261102_082844_sqlite/sqlite_stdlib_cli.log) |

[実行コマンド・時刻・ソースとログのSHA-256・DB読込前後のハッシュ・CSV原本ハッシュ](test-records/20261102_082844_sqlite/metadata.json)

## 確認項目

| 項目 | 結果 |
|---|---|
| 生成内容 | 1学習者×5回×30問＝150回答。全回答済み、自信度1〜4・理解度0〜3を含む |
| DB構造・制約 | 5表の件数、主キー・参照、foreign_key_checkが空、integrity_check=ok |
| 再生成・保護 | 同条件・同SQLite版でDBがバイト一致。異なる既存DBは明示的上書き指定なしでは保護 |
| 読込 | QuestionResult表の必要列だけSELECTし、CSVと共通のモデルへ接続。DBの点数・問題文・解説は不使用 |
| 標準／補助モデル | 標準BKTで150履歴・9状態、独立回答の補助モデルで150回答・除外0 |
| 現行CSV由来の列 | 現行CSVの必要列を持つ表でも、CSV入力と同じ推定結果。保存形式の違いはアダプターで吸収 |
| 任意項目と不正入力 | 理解度0とNULL・自信度欠損を区別。存在しないDBは作らず、不正ファイル、必要表・列なし、空表、行数超過を拒否 |
| 読み取り専用 | mode=roで書込を拒否。全テスト・ブラウザ操作前後でDBのSHA-256が一致、WAL/journalを作らない |
| 画面 | SQLiteの150回答表示、正解81・誤答69フィルター、結果CSV、他データへの切替。JS/HTTPエラーなし |
| 既存機能 | 32パターン・24回答・600回答CSV・実CSVアップロード・理由CSV・クリア・モバイルを回帰確認 |
| CLI・依存 | Python -SでSQLite読込→推定が成功。標準ライブラリのみで動作 |
| 原本保管 | 3つの添付CSVを元のバイト列でコピーし、サイズ・SHA-256が一致。RawとQuestionResultの10問が一致。Gitの改行変換も無効化 |

## DBとCSV原本の区別

[SQLiteダミーDB](data/mock_jlpt_n2_5_sessions/README.md)は、推定を実行できるよう回答済みの架空データを生成したもの。既存の20回用モック生成器をsessions=5で再利用し、元の600回答CSVは変更していない。DBのQuestionResultは保存用33列で、現行41列エクスポートの複製ではない。DataSchemaVersionがない場合はNULLとして、共通の必要14列へ変換する。

[提供CSV原本](data/prototype_exports/SESS_1793573633671/README.md)は全未回答の10問をそのまま保存した。回答済みに書き換えたり、ダミーDBへ混ぜたりしない。今回ユーザーから明示的なGit保管依頼があったため、以前の「原本未保管」から状態を更新した。

## 工程中の修正と限界

最初の生成で、元のmanifestにsettingsという入れ子があると誤認して参照し、KeyErrorになった。元のmanifestは設定が直下にあるため、必要な設定キーを取得するよう修正。再生成後、全105件と画面検証が成功した。

GitはDBファイルの配布・版管理に使い、実行時にはチェックアウト先のローカルファイルを読む。GitHubにSQLで接続する構成ではない。今回のDBは読込用の合成サンプルで、実CSVのDB追記・実ログや推定履歴の保存・複数利用者・Django連携は未実装。利用者自身のPCでの受入確認は後日。
