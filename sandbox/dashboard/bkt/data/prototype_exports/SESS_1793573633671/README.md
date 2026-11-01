# 利用者提供の現行prototype出力CSV原本

2026-11-02の依頼「さっきの3つのCSVは念のためGitに保管」に基づいて保存しました。添付原本のバイト列・UTF-8 BOM・改行を維持し、SHA-256とサイズをmanifest.jsonへ記録しています。Gitでの改行変換も.gitattributesで無効にしています。

| ファイル | 内容 |
|---|---|
| Session_SESS_1793573633671.csv | 1回分のサマリー（26列） |
| QuestionResult_SESS_1793573633671.csv | 10問の明細（41列） |
| CBT_RAW_SESS_1793573633671.csv | 上記Session・QuestionResultの統合形式 |

10問すべて未回答で、自信度・解説後理解度も空欄です。これは入力形式・重複除去・未回答処理の確認用として保存し、回答済みデータへ書き換えません。推定用の架空5回分SQLiteは[別フォルダー](../../mock_jlpt_n2_5_sessions/README.md)に置いています。
