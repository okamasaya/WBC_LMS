ADR-0003

Title:
Hide Question URL

Current
GitHub PagesではHTMLへ直接遷移するため、
URLから問題番号が判別できる。

Decision
Version 0.xでは対応しない。

Reason
・GitHub Pages/NAS/USBの互換性を優先
・構成を複雑にしない
・機能追加より保守性を優先

Future
Version 1.x以降、
iframeまたはSPA(JavaScript描画)へ移行した際に対応する。
