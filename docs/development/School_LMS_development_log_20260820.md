# School LMS 開発ログ

## 複数JSON読込対応・問題選択UI改修・次期出力設計

- 対象期間：2026-08-18 ～ 2026-08-20
- 対象機能：JLPT Drill / Actual CBT
- 主な対象ファイル：`questionLoader.js`、`Edit_drill.html`、`config.js`
- 状態：本ログ記載の実装済み項目は動作確認・Gitコミット済み

---

## 1. 今回の目的

従来の単一JSON読込方式を、複数の問題JSONをまとめて読み込める方式へ変更した。

併せて、約2,000問規模の問題ライブラリを前提として、次の操作性を改善した。

- デフォルト出題数の見直し
- テスト終了後の再挑戦処理の修正
- Category Lv2 / Lv3の表示順指定
- 将来のAL-BKTに接続する出力データの整理方針策定
- AIレポートの目的・文体・生成AI依存方式の見直し

---

## 2. 実装済み項目

### 2.1 `questionLoader.js` の複数JSON読込対応

`CONFIG.questionFiles` に複数の問題ファイルを設定し、各JSONを並行して読み込んだ後、1つの問題配列へ統合する方式へ変更した。

```javascript
questionFiles: [
    "./data/JLPT_N2_LK_Ch.json",
    "./data/JLPT_N2_LK_Vo.json"
]
```

主な実装内容は次のとおり。

- `Promise.all()` による複数JSONの並行読込
- `flat()` による問題配列の統合
- `CONFIG.questionFile` による従来の単一ファイル設定も後方互換として維持
- ファイルごとの読込件数と統合後件数をConsoleへ出力
- ファイル名を含むエラーメッセージへ改善
- JSON読込・検証・Quiz Engine形式への変換処理を分離

対応するJSON形式は次の2種類。

#### pandas `orient="records"` 形式

```json
[
    { "question_id": "Q001" },
    { "question_id": "Q002" }
]
```

#### `questions` プロパティ形式

```json
{
    "questions": [
        { "question_id": "Q001" },
        { "question_id": "Q002" }
    ]
}
```

#### 改修途中で発生した問題

- `loadQuestionData()` がコメントアウトされ、`loadMultipleQuestionData()` から呼び出せない状態だった
- `createQuestionSet()` 内で `questions` と `rawQuestions` が混在していた
- `CONFIG.questionFiles` が未定義の状態で `.map()` を実行し、例外が発生した

最終版では、設定値を必ず配列へ正規化し、`rawQuestions` へ統一して解消した。

---

### 2.2 `questionLoader.js` の責任範囲

今回の改修により、`questionLoader.js` の責任を次の範囲に限定した。

1. JSONファイルの取得
2. JSON形式の正規化
3. 複数ファイルの統合
4. 問題データの検証
5. School LMS標準形式からQuiz Engine形式への変換

次の処理はQuiz Engine側、主に `Edit_drill.html` の責任とする。

- Categoryフィルタ
- 出題数制限
- ランダム抽選
- 回答処理
- 結果表示
- AIレポート生成
- Session / Answerログ生成

この分離は、将来のソースコード分割時にも維持する。

---

### 2.3 ローカル実行時のCORS問題

HTMLを `file://` で直接開いた場合、ブラウザのCORS制約により `fetch()` でJSONを読み込めなかった。

代表的なエラー：

```text
Access to fetch at 'file:///...' from origin 'null'
has been blocked by CORS policy
```

複数JSON設定自体は認識され、各ファイルの読込開始ログまで進んでいたため、原因は `questionLoader.js` ではなく実行方法だった。

#### Windows / Cygwin

```bash
cd /home/oka/git/WBC_LMS
python -m http.server 8000
```

#### macOS / Terminal

```bash
cd /path/to/WBC_LMS
python3 -m http.server 8000
```

#### 起動ディレクトリを明示する方法

```bash
python3 -m http.server 8000 --directory /path/to/WBC_LMS
```

ブラウザからは次の形式で開く。

```text
http://localhost:8000/prototype/language/JLPT_N2/Edit_drill.html
```

注意点：`http.server` を起動したディレクトリがWebサーバーのルートになる。起動場所が異なると、正しい相対パスでも404になる。

オフライン運用とは、必ずしも `file://` で開くことを意味しない。ローカルHTTPサーバーはインターネット接続なしでも利用できる。

---

### 2.4 出題数の変更

約2,000問を「全問出題」する状態を避けるため、問題数選択を次の仕様へ変更した。

- デフォルト：10問
- 選択肢：10問 / 30問 / 50問
- 「全問出題」を削除
- Category絞込後の問題数が指定数未満の場合は、存在する問題のみ出題

例：

```html
<option value="10" selected>10問</option>
<option value="30">30問</option>
<option value="50">50問</option>
```

問題ファイル全体は読み込むが、実際に受験する問題数をQuiz Engine側で制限する。

---

### 2.5 「もう一度最初から挑戦する」ボタンの修正

テスト終了後の再挑戦ボタンが機能していなかったため、現在のページをリロードする方式へ変更した。

```html
onclick="window.location.reload();"
```

このページでは、初期画面からテストを開始するときに問題を再抽選する。そのため、複雑な状態初期化処理を追加せず、リロードで次を満たせる。

- 初期設定画面へ戻る
- 前回の得点・回答状態を破棄する
- 次回開始時に問題を再抽選する

ボタンは、背景色 `#718096` と黒文字の組み合わせが見づらかったため、明るい背景色へ調整した。将来はインラインCSSを外部CSSへ分離する。

---

### 2.6 Category Lv2 / Lv3の表示順指定

従来は、JSONから抽出したカテゴリをJavaScript標準の `.sort()` で並べていたため、教材として意図した順番にならなかった。

次の構成を追加した。

```text
CATEGORY_ORDER
    ↓
sortCategoriesByOrder()
    ↓
generateCategoryLv1Options()
    ↓
updateCategoryLv2Options()
    ↓
updateCategoryLv3Options()
```

#### 設定構造

```javascript
const CATEGORY_ORDER = {

    lv2: {

        "言語知識": [
            "語彙",
            "文法"
        ]

    },

    lv3: {

        "言語知識": {

            "語彙": [
                "語形成",
                "文脈規定",
                "言い換え類義",
                "用法"
            ]

        }

    }

};
```

#### 並び替え方針

- 設定配列にあるカテゴリは指定順で表示
- 設定にない新規カテゴリは末尾へ追加
- 指定外カテゴリ同士は `localeCompare(..., "ja")` で並べる
- JSON側の前後空白は除去して比較
- Category名は、句読点や表記を含めて設定値とJSON値を一致させる

#### 発生した不具合：JavaScriptオブジェクトの重複キー

`CATEGORY_ORDER.lv3` 内で同じ `"言語知識"` キーを複数回定義したため、後に書いた値で前の値が上書きされた。

誤った例：

```javascript
lv3: {
    "言語知識": {
        "語彙": [/* ... */]
    },

    "言語知識": {
        "文法": [/* ... */]
    }
}
```

正しい例：

```javascript
lv3: {
    "言語知識": {
        "語彙": [/* ... */],
        "文法": [/* ... */]
    }
}
```

JavaScriptはオブジェクトの重複キーをエラーにせず、後の値で静かに上書きする。今回、語彙だけ指定順にならなかった原因はこの仕様だった。

---

## 3. Git運用上のメモ

今回の作業は、機能ごとに動作確認後コミットした。

コミットメッセージは、変更内容に応じて動詞を使い分ける。

| 目的 | 動詞 | 例 |
|---|---|---|
| 新機能・設定の追加 | `Add` | `Add custom ordering for category Lv2 and Lv3` |
| 不具合修正 | `Fix` | `Fix restart button` |
| 初期値設定 | `Set` | `Set default question count to 10` |
| 振る舞い変更 | `Change` | `Change question count options` |
| 内部構造整理 | `Refactor` | `Refactor category selector logic` |
| 不要機能削除 | `Remove` | `Remove all-question option` |
| 文書・データ更新 | `Update` | `Update development log` |

`Update` でも誤りではないが、用途が広いため、機能追加・修正・削除を具体的な動詞で表すと `git log` を追いやすい。

---

## 4. 現在の完了状態

| 項目 | 状態 |
|---|---|
| 複数JSON読込 | 完了・コミット済み |
| pandas `orient="records"` 対応 | 完了 |
| 単一JSON後方互換 | 完了 |
| GitHub Pagesでの動作確認 | 完了 |
| ローカルHTTP実行確認 | 完了 |
| デフォルト10問 | 完了・コミット済み |
| 10 / 30 / 50問選択 | 完了 |
| 全問出題削除 | 完了 |
| 再挑戦ボタン | 完了・コミット済み |
| Category Lv2指定順 | 完了・コミット済み |
| Category Lv3指定順 | 完了・コミット済み |
| テスト終了後の出力整理 | 次スレッド |
| AIレポート再設計 | 次スレッド |

---

## 5. 次スレッドの作業：テスト終了後の出力整理

次の作業では、AL-BKT向けER図を基準として、テスト終了後の出力を次の3種類へ整理する。

1. AIレポート：学生・教員が読んだり生成AIへ渡したりする文章
2. `Session_Summary`：1回のテストにつき1行のセッション情報
3. `Answer_Log`：解答した問題につき1行の明細情報

重要：テスト終了時に作る「問題単位の結果」は、問題マスターではなく `Answer_Log` として扱う。問題本文・選択肢・正解・解説は問題JSONまたは将来の `QuestionMaster` が保持する。

### 5.1 出力名とAL-BKT側の対応

| CBT出力 | 用途 | AL-BKT / ER上の対応 |
|---|---|---|
| AIレポート | 学生向けフィードバック、生成AI入力 | AI Mentor Analysis |
| `Session_Summary` | 受験1回の集計 | `Session` / `SessionLog` |
| `Answer_Log` | 問題ごとの解答記録 | `AnswerLog` |
| 問題JSON | 問題マスター | `QuestionMaster` |

### 5.2 `Session_Summary` の候補項目

```text
Session ID
Student ID
Mode
Start Time
End Time
Total Time (sec)
Question Count
Score
Correct Count
Wrong Count
Accuracy
```

将来の物理カラム名候補：

```text
session_id
student_id
mode
start_at
end_at
total_duration_sec
total_questions
score
correct_count
wrong_count
score_rate
```

### 5.3 `Answer_Log` の候補項目

```text
Log ID
Session ID
Question Order
Question ID
Answer
Correct
Response Time (ms)
Confidence
ExplanationComprehension
Review
Answer Time
```

カテゴリ・難易度を分析用スナップショットとして保持する場合の追加候補：

```text
category_lv1
category_lv2
category_lv3
difficulty
```

将来の物理カラム名候補：

```text
log_id
session_id
question_order
question_id
answer
correct
response_time_ms
confidence
explanation_comprehension
review
answer_time
category_lv1
category_lv2
category_lv3
difficulty
```

### 5.4 モード差分

- `Drill`：回答直後の採点、自信度、解説理解度、復習フラグを観測データとして重視
- `Actual`：試験単位の得点・正答率・所要時間を重視
- `Review`：将来、復習対象問題の再回答を区別するための候補モード
- `Actual` で取得しない項目は、空欄または `null` として扱う
- BKTパラメータや理解度推定値は、初期ログへ無理に埋め込まず後段で計算する

### 5.5 次スレッドの実装順

1. `Edit_drill.html` のテスト終了処理を確認
2. セッション生成処理を1か所へ集約
3. `Session_Summary` オブジェクトを生成
4. `Answer_Log` 配列を生成
5. CSVの列順・文字コード・エスケープ処理を統一
6. AIレポートを新しいデータ構造から生成
7. コピーボタンとダウンロードボタンの役割を整理
8. Drill / Actualの両モードで動作確認

確認すべき関数名・検索語の例：

```text
showResult
finishTest
generateReport
report-text
SUMMARY_LOG
DRILL_RAW_LOG
Session_Summary
Answer_Log
downloadCSV
copyReport
```

---

## 6. AIレポートの再設計

### 6.1 背景

他の日本語教員から、外国人学生は「褒められたい」という傾向が強く、正答時だけでなく誤答時にも前向きな言葉が必要という意見があった。

方針案：

> 正答は素晴らしい成果として明確に褒める。誤答でも、考えたこと・挑戦したこと・今回の経験から覚えられることを肯定する。

AIレポートは、単なる採点結果や弱点一覧ではなく、次の学習行動へつなげる「AI Mentor」の入口として再設計する。

### 6.2 レポート文体の原則

- 正解は、何ができたのかを具体的に褒める
- 不正解でも、挑戦・思考・振り返りを肯定する
- 「できていない」より「今回覚えられる」「次はここを確認する」と表現する
- 誤答を隠さず、正答・根拠・次の行動を短く示す
- 同じ定型句の連続を避け、カテゴリ・難易度・回答状況に応じて変化させる
- 外国人学習者向けに、短く明確で理解しやすい日本語を優先する
- 人格ではなく、具体的な行動・工夫・進歩を褒める
- 点数が低い場合でも、空疎な称賛にならないよう根拠を添える

### 6.3 コメント例

#### 正答時

```text
正解です。文脈から言葉の意味を正しく判断できました。素晴らしいです。
```

```text
応用問題に正解できました。基礎知識を使って答えを選べています。
```

#### 誤答時

```text
最後まで考えて答えを選べたことが大切です。今回、正しい使い方を確認できたので、次は同じ形を見つけやすくなります。
```

```text
今回は不正解でしたが、迷った点が分かったことは大きな前進です。正解と選んだ答えの違いを1つ確認しましょう。
```

#### 全体コメント

```text
10問すべてに取り組めました。正解した分野は自信を持ってよいところです。間違えた問題も、今日覚えた内容として次の学習につながっています。
```

### 6.4 AIレポートの構成案

1. 最初の肯定メッセージ
2. 得点・正答率・所要時間
3. よくできたカテゴリ
4. 今回覚えられるポイント
5. 復習優先問題
6. 次に行う学習を1～3件
7. 前向きな締めの言葉

「弱点」ではなく「次に伸ばす分野」、「間違い一覧」ではなく「今回覚えられるポイント」と表現する案を検討する。

### 6.5 AIへコピーする情報と内部ログを分離する

AIレポートへコピーする文章と、学校内部で保存するログは分ける。

- AIコピー用：Student IDなどの個人識別情報を原則として含めない
- 内部保存用：Session ID / Student ID / Answer Logを保持
- AIへ渡す場合：必要最小限のカテゴリ、正誤、回答時間、自信度、解説理解度だけを使用
- 第三者生成AIへ入力する情報について、学校の情報管理方針を確認する

---

## 7. Gemini Canvas以外で簡易CBTを動かす方法

### 7.1 結論

簡易CBTの作成・実行はGemini Canvas専用ではない。

次の2つを分けて考える。

1. 生成AIにHTML / CSS / JavaScriptを書かせる
2. 生成されたCBTをブラウザで実行・共有する

1は主要な生成AIで可能。2はサービスごとに方法が異なる。

### 7.2 選択肢

| 方法 | アプリ生成 | その場で実行・プレビュー | 共有 | 本システムでの位置づけ |
|---|---:|---:|---:|---|
| Gemini Canvas | 可能 | 可能 | 公開リンク | 現在の試作方法 |
| Claude Artifacts | 可能 | 可能 | 公開・組織内共有 | Gemini Canvasに近い代替候補 |
| ChatGPT Sites | 可能 | 可能 | ホスト・共有 | Webアプリとして公開する候補 |
| HTMLを生成してGitHub Pagesへ配置 | 可能 | ブラウザで実行 | URL共有 | 現行School LMSの標準方式 |
| HTMLをローカルHTTPで実行 | 可能 | ブラウザで実行 | 原則ローカル | NAS・USB・オフライン運用 |

Gemini Canvasは、アプリやクイズの作成、コード編集、プレビュー、Console確認、共有リンク作成に対応している。

Claude Artifactsは、説明から共有可能なアプリ・ツール・体験を作成し、公開リンクから他者が操作できる。Gemini Canvasに最も近い代替候補である。

ChatGPT Sitesは、ChatGPTからWebサイト・Webアプリ・ゲームを作成、ホスト、改修、共有できる。2026-08-20時点ではPublic Betaで、Plus / Pro / Business / Enterprise / Eduで利用可能と公式資料に記載されている。ただし、アカウントや組織設定、利用上限を確認する必要がある。

### 7.3 推奨方針

School LMSのCBT本体は、特定の生成AIサービスへ依存させない。

```text
問題JSON
    ↓
School LMS標準HTML / CSS / JavaScript
    ↓
GitHub Pages / NAS / ローカルHTTP
```

生成AIごとのCanvas / Artifacts / Sitesは次の用途に限定する。

- 試作品を短時間で作る
- UI案を比較する
- 教員へデモを共有する
- 新しい問題形式を検証する

正式な教材は、生成されたコードをSchool LMSへ取り込み、Gitで版管理する。

AIレポートも特定モデル専用の命令文にせず、一般的な日本語プロンプトと構造化データを組み合わせる。ChatGPT、Gemini、Claudeなど複数の生成AIへ渡せる形式を目標とする。

---

## 8. 次スレッド開始時の確認事項

### 必要なソースコード

`Edit_drill.html` から、次の処理を含む部分を確認する。

- テスト終了処理
- 結果画面生成
- AIレポート生成
- コピー処理
- CSV生成・ダウンロード処理
- `Session_Summary` / `Answer_Log` / `SessionLog` / `AnswerLog` 生成処理

### 最初に確定する仕様

1. 画面上に表示する結果
2. AIへコピーする文章
3. 教員がダウンロードするCSV
4. AL-BKTへ取り込むデータ
5. Drill / Actualで取得する項目の差
6. CSVファイル名と列名
7. Student IDなどの個人情報をAIコピーへ含めるか
8. AIコメントをCBT内部のテンプレートで作るか、生成AIへ渡して作るか

### 推奨する実装単位

```text
Step 1: Session_Summaryのデータ構造を確定
Step 2: Answer_Logのデータ構造を確定
Step 3: CSV出力を統一
Step 4: AIレポート用データを分離
Step 5: 称賛中心のAIレポートを実装
Step 6: Drill / Actualで総合テスト
```

---

## 9. 参考資料

- [Gemini Canvas：Create docs, apps & more with Canvas](https://support.google.com/gemini/answer/16047321?co=GENIE.Platform%3DDesktop&hl=en)
- [Claude：What are artifacts and how do I use them?](https://support.claude.com/en/articles/9487310-what-are-artifacts-and-how-do-i-use-them)
- [Claude：Publish and share artifacts](https://support.claude.com/en/articles/9547008-publish-and-share-artifacts)
- [OpenAI Docs：Sites](https://learn.chatgpt.com/docs/sites)

---

## 10. 次回作業のゴール

次回は、現在混在している結果表示・AIレポート・ログ出力を分離し、次の状態を完成条件とする。

- 学生は、前向きで分かりやすいAIレポートをコピーできる
- 教員は、`Session_Summary` と `Answer_Log` を扱いやすいCSVで取得できる
- 将来のAL-BKTは、同じデータ構造を大きく変更せず取り込める
- CBT本体とAI分析を疎結合にする
- Gemini Canvas以外の生成AIでも利用できる
- GitHub Pages / NAS / ローカルHTTPの既存運用を維持する

以上。
