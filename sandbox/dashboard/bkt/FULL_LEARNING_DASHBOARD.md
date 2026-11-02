# N2言語知識・読解・聴解の学習画面

既存8055モデル検証画面・8056言語知識画面を保持し、**8057**に全領域版を追加しました。

リポジトリルート`/workspace/WBC_LMS`から:

```sh
PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/wbc-lms/bin/python -m sandbox.dashboard.bkt.full_learning_dashboard
```

`--port`でポート変更可。依存関係は従来の`sandbox/dashboard/requirements.txt`のまま、外部DBや認証は不要です。クラウド内の動作確認はローカルHTTP要求とPlaywrightを使います。

## 操作

1. 初期表示は架空学習者1人・15回・1,605回答、主入力はSQLite。
2. 「領域」か3領域の棒で言語知識・読解・聴解を選択。
3. 「分類」で文字・語彙／文法／内容理解等を選び、「大問・細分類」で漢字読み／短文／中文等へ絞る。大問の棒でも選択できます。
4. 「実施回」と対象期間を組み合わせて回答明細を確認。
5. 親の領域・分類を変えると子の条件は解除。「すべての条件を解除」は回次・期間も戻します。
6. SQLite／同内容CSVの切替では全条件を初期化。KPI・グラフ・表・CSVは共通条件で集計します。

正答率は全正解数÷全有効回答数。問題数が異なる領域の正答率を単純平均しません。解説後理解度は自己申告0〜3、モデル試算は各回答を同じ事前確率から独立評価する手動仮定の値です。自信度は1高〜4低。公式尺度得点・合否判定・累積習得率とは区別します。

領域サマリー・大問サマリー・履歴・回答明細CSVは表示ページではなく選択に合う全行が対象。モデル仮定JSONにはパラメータ・モデル版・選択条件を含みます。

資料・生成条件・問題本文と音声を含まない等の制約は[データREADME](data/mock_jlpt_n2_full_15_sessions/README.md)を参照。

## 検証

リポジトリルートから:

```sh
PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/wbc-lms/bin/python -m unittest discover -s sandbox/dashboard/tests -p 'test_*.py' -v
# 8057を起動後
node sandbox/dashboard/bkt/tests/full_learning.browser.cjs
```

Playwrightと`/usr/bin/chromium`を使用。`BKT_FULL_TEST_URL`・`CBT_TEST_CHROMIUM`で変更可、画像保存先は`BKT_FULL_TEST_DIR`（既定`/tmp/bkt_full_learning`）。既存8056は同サーバー起動後`node sandbox/dashboard/bkt/tests/learning_dashboard.browser.cjs`で回帰検証します。

[開発ログ](DEVELOPMENT_LOG_FULL_N2_20261102.md)／[検証結果](TEST_RECORD_FULL_N2_20261102.md)
