# SQLiteと同内容のCSV控え

同じフォルダーの親にあるlearning_logs.sqlite3の5表をCSVへ書き出した控えです。架空学習者1人・5回・150回答。Student・Skill・Question・Session・QuestionResultの行と列はSQLiteの保存形式に対応します。現行prototypeの41列QuestionResultを再現したエクスポートではありません。

UTF-8 BOM付き。BOOLEANはTRUE/FALSE、INTEGERは整数として復元します。manifest.jsonに各ファイルと元DBのSHA-256、各表の件数を保存しています。.gitattributesでGitによるCSVの改行変換を無効にしています。

8056の学習画面で「CSV（同内容の控え）」を選択できます。標準入力はSQLiteです。CSV切替でも同じ150回答・9大問題・5回の集計・モデル値になることを検証しています。

```sh
# リポジトリルート
python -m sandbox.dashboard.bkt.dashboard_data --export-csv
```

同じ内容なら何も変更せず、差がある既存ファイルは保護します。意図して更新する場合のみ--overwriteを付けます。利用者提供のCSV原本とは分離した合成データです。
