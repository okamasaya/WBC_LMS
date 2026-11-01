# 開発記録：Gitに置いたSQLiteの読込と5回分ダミー（2026-11-02）

## 依頼

「現行でもGit上にSQLiteを配置して読めるか。可能なら5回分のダミーで動作を固めたい。先ほどの3つのCSVもGitへ保管したい」という依頼に対応した。

GitにSQLiteファイルを置くことは可能で、取得したローカルファイルをPythonのsqlite3で読む。既存画面はCSV中心だったため、今回SQLiteの入力アダプターと8055の選択肢を追加した。

## 実装したこと

- data/mock_jlpt_n2_5_sessions/learning_logs.sqlite3を作成。架空学習者1人、N2言語知識5回、各30問の150回答。
- 既存の合成生成器を5回設定で再利用し、Student・Skill・Question・Session・QuestionResultの5表へ格納。正誤・自信度・解説後理解度は架空で、動作確認用。
- sqlite_data.pyでDB生成、外部キーと整合性の検査、manifestとDDLの保存、読み取り専用読込を実装。
- DBから点数・本文・解説を読まず、識別情報と3項目を中心に必要14列へ変換。共通のestimate_importから既存補助モデルへ接続する。
- 8055の「データの種類」に「JLPT N2・5回分（SQLite）」を追加。150回答の推定・正誤フィルター・CSV出力を利用できる。
- CLI `python -m sandbox.dashboard.bkt.sqlite_data`でも読込・推定件数を確認できる。DB読込・推定はPython標準ライブラリだけで動く。

DBは保存用モックスキーマで、現行CSV全列を格納したものではない。DataSchemaVersion等が保存形式にない場合はNULLにし、列の対応を明示した。モデルの式・仮パラメータ・独立回答の方針は変更していない。

## 提供CSV原本の保管

利用者の明示依頼に基づき、data/prototype_exports/SESS_1793573633671/へSession・QuestionResult・CBT_RAWの3原本をコピーした。UTF-8 BOM・改行を含むバイト列の一致を確認し、サイズとSHA-256をmanifestへ保存。Gitチェックアウト時の改行変換も.gitattributesで無効にした。

これらは全未回答の10問で、推定用の5回分ダミーと分離する。前のログにある「添付原本はGitへ追加しない／未保管」は当時の扱いで、今回の保管依頼によって更新した。原本の点数・回答状態は変更していない。

## 検証と修正

SQLite関連10件を追加し、Python全体105件（BKT71件を含む）が成功。生成・再生成・制約・原本ハッシュ・読込・両モデル接続・エラー・欠損・CLI・画面出力を確認した。

ブラウザで150回答、正解81・誤答69のフィルターと結果CSVを確認。既存の32パターン・24回答・モック600回答・CSV取込も回帰確認した。テスト前後でDBハッシュが同一であり、DBを変更していない。

最初の生成で元のmanifestの設定キー参照を誤って失敗したため、実際の構成に合わせて修正した。詳細・生ログ・ハッシュは[テスト記録](TEST_RECORD_SQLITE_20261102.md)に保存。

## 現状とToDo

- [x] Git配布用の5回分SQLiteダミーを作成。
- [x] SQLite→必要列→既存モデル→ダッシュボード／CLIを接続。
- [x] CSV原本3点をGit保管対象へ追加し、原本一致を確認。
- [x] 開発側の自動テストと画面検証を完了。
- [ ] 自分のPCで最新版を取得し、8055の「JLPT N2・5回分（SQLite）」を選んで確認する。
- [ ] 回答済みの実CSVを出力し、既存のCSV取込でも推定と結果保存を確認する。
- [ ] 手元での確認結果・必要な修正をログに追記する。

次の仕様として、実ログのSQLite保存・更新・採用版管理、推定履歴のDB保存、Djangoによるアップロードと利用者への対応付けを保留する。論文・ALP–BKT仕様との照合、補助モデルの履歴接続と学習時点の定義、実ログでのパラメータ評価も別段階。今回の読込用DBを、それらが完成した実運用DBとは扱わない。

## 自分のPCでの確認

リポジトリルートで手元の変更を確認してから更新し、既存のPython環境を使う。

```sh
git status --short
git pull --ff-only origin main
python -m sandbox.dashboard.bkt.flat_app
```

http://127.0.0.1:8055 で「データの種類」→「JLPT N2・5回分（SQLite）」を選ぶ。追加のDBサービスやDjango起動は不要。

- [データの説明・再生成](data/mock_jlpt_n2_5_sessions/README.md)
- [CSV原本の保存場所](data/prototype_exports/SESS_1793573633671/README.md)
- [前段階の現状整理とToDo](DEVELOPMENT_LOG_CSV_CONNECTION_20261102.md#現状整理と再開用todo2026-11-02追記)
