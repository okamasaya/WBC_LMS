# JLPT N2・20回分モックのテスト記録（2026-11-02）

## 対象

mock_dataset.py、data/mock_jlpt_n2_20_sessions/、flat_app.pyのデータ選択、専用テスト。実装モデルの数式・仮パラメータは変更せず、学習ログのモックを追加した。

架空学習者1人×20回×開発用30問＝600回答。9スキル、500問の既存問題定義を使用。正答328、誤答272、高自信誤答78、低自信正答89。学習者と回答は全て合成で、実績データではない。

## 実行証跡

- 基点コミット: `f8db1569d557348d1ad832d10827a10cddd469e5`。今回のコード・CSV・SQL等のSHA-256をメタデータで特定。
- 開始（実行環境JST）: 2026-11-02T06:26:35.040908+09:00
- 終了（実行環境JST）: 2026-11-02T06:26:48.423398+09:00
- Pythonテストは追加10件。BKT専用40件、既存も含む全体74件。40件は74件に含まれ、足し合わせない。
- ブラウザは8055のサーバーに対して、既存フラット画面とモック選択の2スクリプトを実行。

| 検証 | 終了コード | 生ログ |
|---|---:|---|
| bkt_python | 0 | [ログ](test-records/20261102_212635_mock_bkt_python.log) |
| all_python | 0 | [ログ](test-records/20261102_212635_mock_all_python.log) |
| flat_browser | 0 | [ログ](test-records/20261102_212635_mock_flat_browser.log) |
| mock_browser | 0 | [ログ](test-records/20261102_212635_mock_mock_browser.log) |
| stdlib_generation | 0 | [ログ](test-records/20261102_212635_mock_stdlib_generation.log) |

[実行コマンド・ハッシュ・データ生成条件・終了コード](test-records/20261102_212635_mock_metadata.json)

## 確認内容

| 項目 | 確認したこと |
|---|---|
| 件数・配分 | 学習者1、受験20、回答600。全回が30問・9スキルのconf配分どおり、出題順1〜30 |
| IDと参照 | ResultIDが600件で一意、回内問題重複なし。学習者・セッション・問題・スキルの対応が一致 |
| 実問題照合 | 使用500問のID、問題文、難易度、正解位置を既存JSONと照合 |
| 正誤・集計 | 選択位置と正解位置から正誤を照合。Sessionの正答数・誤答数・ScoreRateと明細が一致 |
| 自己申告 | 自信度1〜4、理解度0〜3を含み、高自信の誤答と低自信の正答も存在 |
| 時刻 | 提示→回答→自信度→解説→理解度が順序どおり。解説は試験終了後。+09:00付き。反応時間と時刻差が一致。解答は40分以内 |
| 再生成 | 同じseed・入力・設定でCSV等がバイト単位で一致。seed変更で問題・応答も変わる |
| 上書き保護 | 異なる既存内容は拒否して原本維持。生成対象外の利用者メモも維持 |
| 同梱ファイル | 再生成結果とGitに保存する全生成ファイルが一致。manifestの各ハッシュも一致 |
| 取込・モデル | 既存CSV解析・正規化で600件、除外0。標準BKTで9状態・600履歴、補助モデルで独立600行、除外0 |
| SQLite準備 | インメモリーSQLiteへ5表を型変換して投入。行数・外部キー・integrity_checkが正常。不正外部キーの更新は拒否 |
| 画面 | 同梱CSVから600行、正解328・不正解272へ絞り込み。不正解272行＋見出しのCSV出力。JS例外・HTTP400以上なし |
| 既存画面 | 32パターン・架空24回答、条件入力、仮定JSON、異常パラメータ、モバイルは既存ブラウザで回帰確認 |
| 依存 | -Sで生成を実行し、Dash・pandasなしで600行を生成 |

## 結果と開発中の修正

BKT40件・全体74件が成功（失敗・エラー・スキップ0）。ブラウザ2本、標準ライブラリのみの生成も成功。

最初のSQLiteテストでDDLの構文エラー（near Difficulty）を検出した。列定義の途中に外部キーの表制約を入れていたため、表制約を全列の後へ集めるよう修正し、schema.sqlとmanifestを再生成した。上記は修正後の採取結果。初回エラーは開発中のツール出力と開発ログへ記録しており、最終成功ログへ混ぜていない。

## 再実行

```sh
# リポジトリルート。データは同じ内容なら更新されない
python -m sandbox.dashboard.bkt.mock_dataset
/workspace/.venvs/wbc-lms/bin/python -m unittest discover -s sandbox/dashboard/bkt/tests -p 'test_*.py' -v
/workspace/.venvs/wbc-lms/bin/python -m unittest discover -s sandbox/dashboard/tests -p 'test_*.py' -v

# 別ターミナルで8055を起動してからブラウザ検証
/workspace/.venvs/wbc-lms/bin/python -m sandbox.dashboard.bkt.flat_app
node sandbox/dashboard/bkt/tests/flat.browser.cjs
node sandbox/dashboard/bkt/tests/mock_data.browser.cjs
```

## 意味と未実施

- データの構造・再生成・入力互換性・計算の実行性を確認した。実学習者の分布、モデルの精度、学習効果を実証していない。
- モックは現行の開発用30問構成。JLPT公式の試験全体・尺度得点ではない。
- 標準BKTの600履歴は正誤のみの既存計算の互換確認。解説後の理解度を同じ回の次問へ伝播するモデルを実装したわけではない。
- 現行画面は各回答の独立推定。系列更新、欠損・未回答を含む新しいモック、複数学習者のモックは次の候補。
- 永続SQLite、複数版データの蓄積、Djangoのアップロード・保存は未実装。SQLiteの検証はメモリー内のみで、実運用DBファイルは作っていない。
- 標準ALP・Iris・Bike・JLPTのブラウザ検証は今回未実行。Python全体74件と補助モデル画面で回帰確認した。

[データ説明と各回の概要](data/mock_jlpt_n2_20_sessions/README.md) ／ [開発ログ](DEVELOPMENT_LOG_MOCK_DATA_20261102.md)

[600回答を選択した画面](test-records/20261102_212635_mock_dashboard.png)
