# 正誤中心・補助2項目モデルのテスト記録（2026-11-02）

## 対象と前提

assisted_model.py、flat_app.py（8055）、assets/flat.cssと追加テスト。正誤が中心で、自信度は正誤観測の重み、解説後の理解度はその後の学習遷移の倍率とする。各回答を同じ事前確率から独立に計算し、履歴をつなげない。

旧model.py・learning_data.py・bkt_parameters.jsonは基点とバイト単位で一致。標準BKTや既存のCSV取込仕様は変更せず、実験モデルとして追加した。数式・手動仮定・未検証事項は[モデル仕様](ASSISTED_MODEL.md)を参照。

## 実行証跡

- 基点コミット: `f10cb02b478082edb8898e1f967228b36984f097`。追加ソースはSHA-256で特定。
- 開始（実行環境JST）: 2026-11-02T05:58:05.717790+09:00
- 終了（実行環境JST）: 2026-11-02T05:58:14.931057+09:00
- 実行場所: /workspace/WBC_LMS。既存Python仮想環境、Dash 4.4.1、Plotly 7.1.0、Playwright 1.62.1、Chromium 154.0.8037.57。
- Python：今回追加17件。BKTだけ30件（既存13＋追加17）、全体64件（既存47＋追加17）。30件は64件に含まれる。

| 検証 | 終了コード | 生ログ |
|---|---:|---|
| bkt_python | 0 | [ログ](test-records/20261102_205805_assisted_bkt_python.log) |
| all_python | 0 | [ログ](test-records/20261102_205805_assisted_all_python.log) |
| flat_browser | 0 | [ログ](test-records/20261102_205805_assisted_flat_browser.log) |
| model_only | 0 | [ログ](test-records/20261102_205805_assisted_model_only.log) |

[コマンド・実行時間・ソースハッシュ](test-records/20261102_205805_assisted_metadata.json)

## 確認項目

| 項目 | 期待する動作 | 方法 |
|---|---|---|
| 標準BKTとの一致 | 補助2項目が未入力なら、同じ1回答に対する標準BKTと一致 | Python |
| 手計算 | 正解・自信度1・理解度3で、重み1.5の式と一致 | Python |
| 自信度の向き | 1が高く4が低い。高自信の正解で上方更新が、高自信の誤答で下方更新が強い | Python／ブラウザ |
| 時点の分離 | 理解度を変えても正誤観測後・回答前予測は変わらず、学習遷移後だけが変わる | Python／ブラウザ |
| 全32パターン | 2×4×4で32行。全出力が有限かつ0〜1 | Python／ブラウザ |
| 欠損と0 | 理解度0は有効な低段階、空欄は補助なし。画面でクリアして標準BKTへ復帰 | Python／ブラウザ |
| 入力検証 | 範囲外・小数段階・boolの段階値・NaN/Inf・不正な重み・未回答を適切に拒否／除外 | Python |
| 境界と安定性 | 事前0/1、極端な正の重みでも有限。不可能な観測は拒否 | Python |
| 独立性 | 入力順や学習者・スキルを変えても同じ3項目なら同じ確率。原本は不変 | Python |
| 重複・版競合 | 同じIDと3項目は重複除外。理解度・自信度等が違う版は競合として拒否 | Python |
| 画面のセル選択 | ヒートマップを実クリックし、正誤・自信度・理解度へ反映 | Flask HTTP／ブラウザ |
| CSV・仮定JSON | 不正解16行＋見出しを保存、補助設定とモデル版・評価範囲をJSONへ記録 | Flask HTTP／ブラウザ |
| 合成データ切替 | 32パターンから架空24回答へ切替。不正解の抽出は10行 | ブラウザ |
| エラー復帰 | 不正パラメータで古い表・推定・出力をクリア。復帰後に再計算 | Flask HTTP／ブラウザ |
| 画面幅・例外 | 390px幅で横にはみ出さず、JS例外・HTTP400以上なし | ブラウザ |
| 依存の分離 | -Sで追加モデルをimport・32パターン評価。Dash・pandasを読まない | model_only |

## 結果と意味

BKT30件・全体64件が成功（失敗・エラー・スキップ0）、新しいブラウザ検証とモデル単体も成功。

初版の式と画面の挙動が仕様に一致することを確認した。実ログから学習・校正した結果や、習得状態・次問正答の予測精度を実証したものではない。標準BKTと同じ学術モデルであることの検証でもない。

開発時にFlaskのCSSレスポンスを閉じていないResourceWarningが出たため、テスト側でresponseをcloseする形へ修正。最終採取では警告を隠す設定は使っていない。

## 再実行

```sh
# リポジトリルート。先に別ターミナルで8055を起動
/workspace/.venvs/wbc-lms/bin/python -m sandbox.dashboard.bkt.flat_app

/workspace/.venvs/wbc-lms/bin/python -m unittest discover -s sandbox/dashboard/bkt/tests -p 'test_*.py' -v
/workspace/.venvs/wbc-lms/bin/python -m unittest discover -s sandbox/dashboard/tests -p 'test_*.py' -v
node sandbox/dashboard/bkt/tests/flat.browser.cjs
```

ブラウザテストは/tmp/bkt_assisted_flat_patterns.pngへ32パターンの画像を出力する。

## 未実施

- 実学習者データ、パラメータの学習・校正、予測精度の評価、履歴をつないだ推定、論文本文との照合。
- 新画面からの外部ファイルアップロード・Django接続・永続保存。
- 既存ALP・Iris・Bike・JLPTのブラウザ検証（今回は既存Pythonテストで回帰確認）。

ユーザーが入力する自信度・理解度は自己申告であり、実測の潜在習得状態へ置き換えない。現在の仮定はモデルJSONと仕様書で再現可能な状態にしている。

[全32パターンの画面出力](test-records/20261102_205805_assisted_patterns.png)（開発時に日本語ラベルと軸の向きを目視確認）。
