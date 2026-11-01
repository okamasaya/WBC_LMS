# 現行prototype出力と同じ列の互換モック

架空学習者1人・N2言語知識20回×30問＝600回答。実績データではありません。

| ファイル | 内容 |
|---|---|
| QuestionResult.csv | 現行と同じ41列・列順の600回答。モデル入力と8055画面で使用 |
| Session.csv | 現行と同じ26列・列順の20回分サマリー |
| sample_session/ | 1回分の現行3種CSV形式とAI_Report.txt。同じスナップショットから出力 |
| ResultMapping.csv | 元のモックIDと現行形式IDの対応。IsSynthetic=TRUE |
| manifest.json | 合成であること、件数、列、生成元と生成物のSHA-256 |

列を現行と揃えるため、CSV本体へ独自の合成フラグ・版・イベント時刻を追加していません。合成データの識別はフォルダー・manifest・対応表で行います。元のモックとこの版を二重の実績として投入しないでください。

元のモックの正誤・自信度・理解度を、現行のResultData・ResultReview・ResultReportへ渡して再出力しました。現行形式のResultID/SessionIDへ変換し、回答時刻は同一の瞬間をUTC表記にしています。互換版には合成StudentIDを明示的に指定していますが、現行のデフォルト設定の実出力はStudentIDが空欄になります。

集約2ファイルは20回を結合したもので、実際の1回分のダウンロードはsample_session/を参照してください。QuestionResultまたは統合Raw CSVがモデル入力です。SessionやAIレポート単独はモデル入力ではありません。

```sh
# リポジトリルート。PythonとNode.jsが必要
python -m sandbox.dashboard.bkt.prototype_csv
```

SQLite準備用の元データは[親フォルダー](../README.md)に残しています。項目差と学習者ID・再確定の注意は[互換性確認](../../../CSV_COMPATIBILITY_20261102.md)を参照してください。
