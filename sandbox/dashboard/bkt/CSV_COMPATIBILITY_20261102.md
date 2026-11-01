# 現行prototypeとBKTモックCSVの互換性確認（2026-11-02）

## 結論

**最初に作ったモックは、現行prototype出力の完全な複製ではなかった。** 正誤・自信度・理解度とモデルに必要な共通列は一致していたが、列数・列順・付随項目・ID形式・時刻表現に違いがあった。実施後のCSVをモデルへ渡すという目的に対して、共通項目の互換性だけの確認では不足していた。

現行のJavaScript出力処理を使った互換CSVを別フォルダーへ追加した。元のSQLite準備用モックは維持する。現行画面からの実ダウンロードでも、CSV解析から標準BKT・補助モデルへの接続を検証した。実際の学習者の成績を検証したものではない。

## 確認した現行版

- `prototype/language/JLPT_N2/Actual_N2_261030.html`
- `prototype/language/JLPT_N2/Drill_N2_261031.html`（JSON版）
- `prototype/assets/js/shared/resultData.js`：正誤、ID、時刻、集計。
- `resultReview.js`：解説後の理解度・ラベル、見直しフラグ。
- `resultOutput.js`：確認後のスナップショット確定。
- `resultReport.js`：Session・QuestionResult・統合Raw CSV、サマリーレポート。

現行prototypeのコードは変更していない。出力の版は`DataSchemaVersion=2.0.0`。列定義の正本は`resultReport.js`の2つのCSV_COLUMNSで、モック側へ列定義を手で複製しない。

## 元のモックとの差

| CSV | 元のモック | 現行prototype | 共通列 |
|---|---:|---:|---:|
| Session | 21列 | 26列 | 16列 |
| QuestionResult | 33列 | 41列 | 25列 |

### Session

現行にはあり、元のモックにはなかった列：

`DataSchemaVersion`、`UseConfidence`、`DifficultyMode`、`DifficultyModeLabel`、`SelectedCategoryLevel1`、`SelectedCategoryLevel2`、`SelectedCategoryLevel3`、`WrongCount`、`SourceQuestionFiles`、`CreatedAt`。

元のモック独自の列：

`SessionNumber`、`ReviewEndAt`、`IsSynthetic`、`DatasetID`、`MockSchemaVersion`。

### QuestionResult

現行にはあり、元のモックにはなかった列：

`DataSchemaVersion`、`ExamTitle`、`UseConfidence`、`DifficultyMode`、`CategoryLabel`、`DifficultyLabel`、`QuestionText`、`UserAnswerText`、`CorrectAnswerText`、`CorrectAnswerSource`、`AnswerTimeSec`、`ElapsedTimeSec`、`ReviewFlag`、`DuringExamReviewFlag`、`Explanation`、`CreatedAt`。

元のモック独自の列：

`SessionNumber`、`QuestionPresentedAt`、`ConfidenceRecordedAt`、`ExplanationViewedAt`、`UnderstandingRecordedAt`、`IsSynthetic`、`DatasetID`、`MockSchemaVersion`。

元のモックのイベント時刻・合成フラグは将来のDB検討用の情報。現行CSVからこれらが取得できるとは扱わない。元のモックは+09:00、現行はUTCのZ表記だが、回答時刻は同じ瞬間になることを600件で比較した。SessionID・ResultIDは現行処理で再生成されるため、`ResultMapping.csv`で対応付ける。

## 3項目の対応

| 用途 | CSV列 | 現行とモックで共通の値・意味 |
|---|---|---|
| 主観測：正誤 | IsCorrect | TRUE/FALSE。IsAnswered=FALSEを誤答として更新しない |
| 回答時の補助：自信度 | ConfidenceLevel | 1=自信がある、2=少し自信がある、3=やや不安、4=直感に近い |
| 解説後の補助：理解度 | UnderstandingLevel | 0=全然分からない、1=まだ少し分からない、2=だいたい理解できた、3=理解できた |

空欄は未入力、理解度0は有効な回答として区別する。`CreatedAt`は試験終了を基準に作られ、理解度をチェックした時刻ではない。現行CSVは解説閲覧時刻・理解度入力時刻を記録していない。系列モデルでの正確な学習時点を扱う場合は、別途記録仕様が必要。

## どのファイルを使うか

| 現行からの出力 | 役割 | モデルへの入力 |
|---|---|---|
| QuestionResult_SESS_*.csv | 各問の正誤・自信度・理解度・識別情報 | **推奨** |
| CBT_RAW_SESS_*.csv | Session節とQuestionResult節をまとめたCSV | 既存パーサーでQuestionResult節を抽出できる |
| Session_SESS_*.csv | 回全体のサマリー | 単独では各問モデルの入力にならない |
| サマリーレポート | 人間・AI向けの表示・分析情報 | CSVと整合性を照合。通常のモデル入力にはしない |

解説後の理解度を入力し、「AI用サマリーレポート生成」で**確定した後**にダウンロードする。3つのCSVとレポートは同じ確定データを参照している。再確定で同じResultIDの理解度が変わることがあるため、古いCSVと新しいCSVを混ぜず、採用版を決める。

補助モデルには`estimate_flat(parse_question_csv(text))`で直接渡す。標準BKT用の`normalize_records`は補助項目の変更を重複競合として扱わず、最初の付随情報を残すため、補助モデルの前処理には使わない。補助モデル自身は同一IDの3項目が異なる版を競合として拒否する。

## 学習者IDの注意点

**現行の標準設定はStudentIDが空欄になる。** ActualとJSON版Drillの両方で確認した。

- 今回の独立回答の補助モデルは、StudentIDなしでも各回答を評価できる。
- 学習者×スキルの履歴を使う標準BKTは、StudentIDなしの行を除外する。
- 既存の取込APIでは、同一学習者のファイルであることを明示確認した場合だけ、呼出側でIDを補完できる。空欄を自動的に全員同じ人とみなさない。
- 追加した600回答の互換モックは、合成学習者IDを**明示的に指定**して現行出力処理へ渡している。この点は実際のデフォルト出力と異なる。Djangoの取込時に利用者へ結び付ける設計は今後の作業。

## 追加した互換データ

[data/mock_jlpt_n2_20_sessions/prototype_csv/](data/mock_jlpt_n2_20_sessions/prototype_csv/README.md)

- Session.csv：現行と同じ26列・列順、20回。
- QuestionResult.csv：現行と同じ41列・列順、600回答。
- sample_session/：1回分の実際の3種CSV出力形式＋サマリーレポート。
- ResultMapping.csv・manifest.json：元のモックとのID対応、合成データの識別、生成元コードと生成物のSHA-256。

Node.jsのVMで現行のResultData・ResultReview・ResultReportを実行し、既存の600回答を再出力する。集約CSVだけは同じ列定義と出力オブジェクトを使ってPythonで結合する。列内の改行・引用符・日本語を保持する。再生成にはPythonとNode.jsが必要だが、推定API自体はNode.jsへ依存しない。

```sh
python -m sandbox.dashboard.bkt.prototype_csv
# 差異がある既存ファイルは保護。更新する場合のみ --overwrite
```

8055の「JLPT N2・20回分のモック」は、この互換版を読み込むように変更した。外部CSVのアップロードUIを8055へ追加したわけではなく、外部ファイル取込とDjango連携は次段階のまま。

## 検証

[テスト記録・生ログ・実ダウンロード](TEST_RECORD_PROTOTYPE_CSV_20261102.md)に保存する。主な確認は、列と列順、600回答の3項目と時刻の保持、再生成、2種類のモデル入力、学習者ID空欄、理解度0と未入力、未回答、再確定による競合、現行Actual/Drillの画面から確定・実ダウンロード・推定まで。
