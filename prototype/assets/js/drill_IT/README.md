# IT用プール型Drill

本格教材の入口は[Drill_GenAI-pp_261111.html](../../../it/GenAI_Passport/Drill_GenAI-pp_261111.html)。旧サンプルの[index.html](../../../it/GenAI_Passport/index.html)も維持しています。
v0.2.0の切り替えを体験する[5問デモ](../../../it/GenAI_Passport/Drill_GenAI-pp_polarity_demo.html)も同じJSで動作します。専用設定・専用教材を使い、全問polarity、初期方式は混在、自信度なしです。
教材の型に応じたプールから、その回の4択を作る練習エンジンです。JavaScriptと専用CSSはこのディレクトリに置き、N2用の`drill/`・`shared/`は変更していません。

| ファイル | 役割 |
| --- | --- |
| `bank.mjs` | 設定・バンク読込、構造・一意性検証、テーマ抽出、4択への変換 |
| `session.mjs` | 固定出題・回答確定・移動・思考時間の管理。DOM非依存 |
| `results.mjs` | 共通集計への接続、IT固有の出題スナップショット・CSV・AIレポート |
| `app.mjs` | 設定画面、問題・解説・理解度・出力UI。教材は`textContent`で表示 |
| `drill.css` | IT用の追加スタイル。共通のlearning・結果用CSSと併用 |

`shared/resultData.js`と`shared/resultReport.js`の既存の集計・CSVエスケープ・レポート処理を使います。N2用の設定ローダーには接続しません。追加のnpmパッケージ、ビルド、外部API・DBは不要です。

作問仕様は[v0.2.0の問題作成キット](../../../it/GenAI_Passport/README.md)を参照してください。エンジンはv0.1.0・v0.2.0の両方を読み込み、同じ演習に両型・両バージョンを含められます。全体でIDが重複しないことが前提です。

## 読込・出題

- 対応教材は`it-polarity-pool` / `schema_version: "0.1.0"`または`"0.2.0"`。設定は教材とは別のJSON。
- 設定の`bankFiles`は設定ファイルの場所から解決。設定と教材はHTMLと同じHTTPオリジンに置く。
- 全バンクを検証した後、章・テーマ・問題数を絞り込む。無効な問題を黙って飛ばさない。
- 必須キー・型・空白だけの本文／解説・未知のキー・型別最低件数・全バンクのID重複・テーマ内本文重複（NFKC正規化と前後空白除去後）を検証する。v0.2.0の指示文配列も1件以上・正規化後の重複なしを検証する。
- 適切を問う回は適切1＋不適切3、不適切を問う回は適切3＋不適切1。各プールで重複なし抽出後、4候補をシャッフルする。IDのA/Iは解釈しない。
- 両プールの件数一致は不要。候補不足を複製・他テーマからの補充で埋めない。
- v0.2.0の`polarity`は共通文へ抽選した末尾表現を直接連結。v0.1.0は保存された完成文を使う。
- v0.2.0の`standard`は`correct`1件以上、`incorrect`3件以上が必要。正解1＋不正解3を抽出し、完成文を変更しない。適否の切り替えは行わない。
- 通常型だけの範囲では選択方式を`standard`として表示・記録する。両型がある場合も、適切／不適切／混在の指定で通常型の正解を反転しない。
- 混在は各テーマで独立に50%ずつ方式を選択する。半数ずつの件数は保証しない。
- テーマもランダム抽出・並べ替え。同じテーマは一演習内に一度だけ。出題した設問・方式・候補・順序を凍結し、再訪時も変えない。

ランタイムはSchemaに相当する必須構造と追加の一意性を検証します。教材の文意・出典・シラバス適合や、「候補の適否が文脈に依存せず安定しているか」は内容レビューが必要です。

## 回答・時間

自信度ありでは、選択肢を選んでから自信度1〜4を入力した時点で確定します。確定前は選択肢を変更でき、別の問題へ移動して戻ることもできます。自信度なしでは選択直後に確定します。確定後は変更できず、正誤・共通解説・表示した4候補すべての適否と理由を表示します。

回答時間は、その問題を表示していて未確定だった時間の合計です。自信度入力・終了確認中の時間を含み、確定後の解説閲覧は含みません。バックグラウンドタブでの経過時間も含みます。終了時の未確定選択は未回答として扱い、選択ID・回答位置・回答時刻・自信度を捏造しません。`answeredAt`は確定した時刻です。

自信度・解説理解度は自己申告です。スキルや難易度は元教材に存在しないため、勝手に推定して付与しません。学生IDも未設定です。

本格教材用の設定は`conf_GenAI_pp_1-2-4.json`です。現在の収録数は59問。開始画面は不足1問を表示し、60問へ複製補完しません。60問目をデータへ追加すれば60問も選択できます。問題一覧からの移動は本格教材用HTMLで利用できます。

## 保存契約：it-polarity-result/1.1.0

IT用CSVの`DataSchemaVersion`は`it-polarity-result/1.1.0`です。1.0.0から型・末尾表現の情報を追加しました。JSONの`schema_version`も`1.1.0`で、教材バージョンとは別です。既存のBKT・CSV取込画面への接続は今回の対象外です。

| 出力 | 内容 |
| --- | --- |
| 演習スナップショットJSON | `format: "it-polarity-result"`, `schema_version: "1.1.0"`, `summary`, `records`。教材改訂後も出題内容を確認するための主記録 |
| IT Session.csv | 共通集計列＋選択した出題方式・テーマ・バンク一覧・型別出題件数 |
| IT QuestionResult.csv | 共通回答列＋各問の型・方式・共通文・選んだ末尾表現・章・テーマ・バンク識別・選択候補ID・所属・正解ID・表示した全候補 |
| IT DisplayedOptions.csv | 実際に出た候補1件につき1行。4行／問。ID・本文・順序・所属・解説・この回の正解か・選択されたか |
| AIレポート | 共通レポートの分析JSONに各問の`questionMode`と、完全な`itSnapshot`を追加。APIへ自動送信しない |

`records[].displayedOptions`は表示順の配列で、各候補の`displayedPosition`（1始まり）・`optionId`・`text`・`pool`・`explanation`・`isCorrect`を持ちます。`isCorrect`はその回の正解で、`pool`とは別です。問題の共通解説も`commonExplanation`に保存します。バンクのURL・形式バージョンを記録し、ファイル全体の改訂番号・ハッシュはまだ導入していません。未出題の候補は保存しません。

各問は`questionType`（polarity／standard）と`questionMode`（appropriate／inappropriate／standard）を持ちます。v0.2.0の切り替え型では`questionPrefix`・`selectedInstruction`・`instructionPosition`（配列中の1始まりの位置）も保存します。旧版と通常型ではこの3項目はnullです。`questionText`は実際に表示した完成文です。通常型の`correct`は問いへの正解であり、候補内容そのものが適切な行為・説明とは限りません。

CSVの複合値（`bankSources`・`displayedOptions`）はJSON文字列のセルです。CSVパーサーで読み込んだ後にJSONとして解釈してください。すべての出力は同じ確定スナップショットから作り、理解度0と未入力nullを区別します。理解度・復習フラグを変更したら出力を無効化し、再確定します。

現時点では自動保存・演習の復元・ログJSONの再取込はありません。再読み込みで演習状態は失われます。終了後にJSON等をダウンロードしてください。

## 検証

リポジトリルートから:

```sh
bash scripts/check-it-drill.sh
python3 -m http.server 8000 --bind 127.0.0.1
# 別のターミナルで。PlaywrightとChromiumが必要。
bash scripts/check-it-drill.sh --browser
# N2の回帰確認
bash scripts/check-standard.sh --browser
```

`CBT_TEST_BASE_URL`・`CBT_TEST_CHROMIUM`でサーバーURL・Chromiumを変更できます。旧版ブラウザテストの画像・ダウンロードは`IT_DRILL_TEST_DIR`（既定`/tmp/it-drill-browser`）、新Drillのものは`GENAI_DRILL_TEST_DIR`（既定`/tmp/genai-drill-261111`）へ保存します。ユニットテストは21件。ブラウザ検証は旧版と新Drillの両方を実行し、新Drillでは実データ59問の全回答・採点・出力、両型、再訪、異常系、狭い画面、テスト専用60問構成を確認します。

`node tests/drill_IT/polarity_demo.browser.cjs`で5問デモの適切・不適切・混在、両方向のプール構成・正誤・再訪・JSON記録・モバイル表示を確認できます。画像とログは`POLARITY_DEMO_TEST_DIR`（既定`/tmp/genai-polarity-demo`）へ保存します。
