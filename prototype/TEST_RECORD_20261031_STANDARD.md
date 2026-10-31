# テスト記録：標準問題実施基盤（2026-10-31）

## 記録の位置付け

次の2つの開発ログに記載した単体テストについて、対象・確認内容・結果を整理し、現行コードでの再実行出力を保存した。

- [2026-10-30〜31の開発記録](DEVELOPMENT_LOG_20261030-20261031.md)
- [2026-10-31のCSS整理記録](DEVELOPMENT_LOG_20261031_CSS.md)

当時の実行出力を後から作り直したものではない。今回保存した生ログは、以下のコミットに対する今回の再実行結果である。各開発時のブラウザ検証については、過去の結果として別に扱う。

| 項目 | 内容 |
| --- | --- |
| 対象コミット | [`3fe9d051e64cf5074516ed8353b625e419098c09`](https://github.com/okamasaya/WBC_LMS/commit/3fe9d051e64cf5074516ed8353b625e419098c09) |
| 実行日時 | 2026-10-31 12:37:15 JST（開始・終了とも同じ秒） |
| 実行環境 | この開発で使用しているクラウド環境、Node.js v24.19.0 |
| 作業ディレクトリ | リポジトリのルート |
| コマンド | `scripts/check-standard.sh` |
| コマンド終了コード | 0 |
| 単体テスト | 12件実行、成功12、失敗0、中断0、スキップ0、todo0 |
| 付随する点検 | 現行ランタイム3入口・33ファイル、参照切れ・旧版への依存なし |
| 今回のブラウザ検証 | 未実行。単体テストの証跡保存を目的とした再確認 |

2つの開発ログの基準である `904a144` と `3fe9d05` の間で、以下の4つの単体テストファイルに差分がないこともGitで確認した。ただし、これは過去と今回の実行環境・所要時間が同一であることを示すものではない。

## 保存した証跡

- [実行出力の生ログ](test-records/20261031_unit_3fe9d05.log)：標準出力・標準エラーを保存。各テスト名・結果・所要時間・ファイルごとの集計を含む。
- [実行メタデータ](test-records/20261031_unit_3fe9d05.json)：対象コミット、日時、Node.js、コマンド、終了コード、集計、各テストソースと生ログのSHA-256。
- [テストソースの案内](../tests/standard/README.md)

生ログの所要時間は、その実行時の計測値である。性能の基準値や保証値としては扱わない。生ログは4回のNode.jsプロセスの出力が連続した形式で、各プロセスの集計は3・4・2・3件、合計12件となる。

## ファイルごとの集計

| テストファイル | 実行 | 成功 | 失敗 | スキップ |
| --- | ---: | ---: | ---: | ---: |
| [examConfig.test.mjs](../tests/standard/examConfig.test.mjs) | 3 | 3 | 0 | 0 |
| [examCore.test.mjs](../tests/standard/examCore.test.mjs) | 4 | 4 | 0 | 0 |
| [runtimeBoundary.test.mjs](../tests/standard/runtimeBoundary.test.mjs) | 2 | 2 | 0 | 0 |
| [sharedResults.test.mjs](../tests/standard/sharedResults.test.mjs) | 3 | 3 | 0 | 0 |
| 合計 | 12 | 12 | 0 | 0 |

ランタイム点検はこの12件とは別のチェックであり、テスト件数に加えていない。

## 12件の確認内容

### A. 共通設定：examConfig.test.mjs（3件）

| ID | ソース内のテスト名 | 確認内容 | 今回の結果 |
| --- | --- | --- | --- |
| CFG-01 | `one config supplies independent Actual quotas and Drill options` | 同じconfからActualの30問・40分・選択肢順維持と、Drillの初期10問・選択肢シャッフルを独立して取得する。スキルIDを共用し、元の設定オブジェクトを変更しない | 成功 |
| CFG-02 | `bad settings fail rather than silently using defaults` | 空の問題数候補、不整合な初期値、文字列の真偽値、不正な難易度、空の問題ファイル、カテゴリ重複、未知のschemaVersionを受け付けない | 成功 |
| CFG-03 | `legacy Actual config is accepted without changing its shape` | Actualは旧schemaVersion: 1を読み込める。新Drillへ旧形式を渡した場合はschemaVersion: 2が必要であることをエラーで示す | 成功 |

### B. 出題・採点・問題変換：examCore.test.mjs（4件）

| ID | ソース内のテスト名 | 確認内容 | 今回の結果 |
| --- | --- | --- | --- |
| CORE-01 | `real bank: exact category quotas, unique IDs, no mutation` | 実際のN2問題データからカテゴリ配分どおり30問を抽出し、問題IDが重複せず、元データを変更しない | 成功 |
| CORE-02 | `validation blocks invalid configuration and insufficient banks` | 制限時間0・文字列時間、不正な真偽値、空の問題ファイル、負の出題数、カテゴリ重複、問題不足、問題ID重複を検出する | 成功 |
| CORE-03 | `unanswered / wrong answers score zero and option shuffling preserves correct answer` | 選択肢を並べ替えても正解が1つ残る。全問正解は30件、1問未回答・1問不正解にすると28件となる | 成功 |
| CORE-04 | `shared loader preserves all existing N2 question conversions` | N2全1,821問を旧ローダーと共通ローダーで変換し、結果全体が一致する。共通ローダーに旧CONFIG依存の起動関数を含めない | 成功 |

### C. 実行用ファイルの境界：runtimeBoundary.test.mjs（2件）

| ID | ソース内のテスト名 | 確認内容 | 今回の結果 |
| --- | --- | --- | --- |
| BND-01 | `current entries reach only their runtime assets and configured questions` | 現行3入口の依存一覧に共通ローダー・Actual JS・現行問題が含まれ、tests・docs・prompt・old・test_versionや旧N2ローダーが混入しない | 成功 |
| BND-02 | `missing transitive assets and dependencies on history fail the audit` | 一時的な検証用ファイル群で、JS import先の欠落、旧資産への依存、CSS欠落を検出する。欠落を直すと必要なファイル一覧を得られる | 成功 |

### D. 集計・AIレポート・CSV：sharedResults.test.mjs（3件）

| ID | ソース内のテスト名 | 確認内容 | 今回の結果 |
| --- | --- | --- | --- |
| RES-01 | `Actual and Drill share scores and typed raw schema; unanswered timestamps stay empty` | 正解・不正解・未回答の3問サンプルで、両モードの集計、時間、スキル、自信度、フラグを確認する。未回答の回答時刻・選択位置・回答文はnullに保つ | 成功 |
| RES-02 | `AI payload includes Actual confidence, zero understanding and review edits; skipped confidence is not fabricated` | Actualの自信度、理解度0、復習フラグ、未回答の表記が本文と分析JSONに反映される。自信度無効時に値を捏造しない | 成功 |
| RES-03 | `CSV schemas, raw sections and escaping are identical for both modes` | Session／QuestionResult／統合Rawの見出し・セクション・拡張子・改行を確認する。引用符・カンマ・問題文中の改行をエスケープし、未知の出力種別は拒否する | 成功 |

## ブラウザ・CSS検証との区別

以下は開発時に別枠で実施して成功したブラウザ検証であり、上記12件の単体テストには含めない。今回の証跡追加では再実行していない。

| ファイル | 開発時に確認した内容 |
| --- | --- |
| [entry.browser.cjs](../tests/standard/entry.browser.cjs) | 現行ファイル一覧だけへのアクセスで、入口から両モードを起動・実施できる。モバイル入口と参照切れも確認 |
| [jsonDrill.browser.cjs](../tests/standard/jsonDrill.browser.cjs) | カテゴリ・難易度・自信度・即時解説・番号移動・共通出力、別conf・相対パス・順序指定、設定／問題取得失敗、モバイル |
| [browser.cjs](../tests/standard/browser.cjs) | Actualの回答変更・フラグ・終了確認・時間切れ・レポート・コピー・CSV3種類、旧drillの回帰確認 |
| [styles.browser.cjs](../tests/standard/styles.browser.cjs) | 両モードの共通描画、320／390／768px幅、テーマ上書き、フォーカス、出力ボタンのホバー色、旧版CSSフォールバック |

特にCSS整理の見た目は、単体テストだけでは確認できない。CSSログに記載した「描画・操作の検証」はstyles.browser.cjs等によるブラウザ検証を指す。過去実行の生出力は今回の保存対象に含めず、既存開発ログと検証ソースを参照する。

## 再実行方法

リポジトリのルートで、依存関係の点検と単体テストを実行する。

```sh
scripts/check-standard.sh
```

単独のテストファイルも実行できる。

```sh
node tests/standard/examConfig.test.mjs
node tests/standard/examCore.test.mjs
node tests/standard/runtimeBoundary.test.mjs
node tests/standard/sharedResults.test.mjs
```

ブラウザ検証も実行する場合は、HTTPサーバーを別ターミナルで起動してから実行する。

```sh
python3 -m http.server 8000 --bind 127.0.0.1
# 別ターミナルで
scripts/check-standard.sh --browser
```

ブラウザ検証にはPlaywrightとChromiumが必要。単体テストはNode.jsの組み込みテスト機能を使用する。

将来別の版で証跡を保存する場合は、対象コミット・日時に対応した別ファイルを作成し、この記録の生ログを上書きしない。

## この記録の範囲

- テストプログラム、アプリ、conf、問題データは変更していない。
- 今回の再実行はN2の既定構成と固定サンプルを対象とする。他試験、全ブラウザ、性能、理解度推定モデルの妥当性は保証しない。
- テスト結果を保存するための文書・証跡ファイルは、現行ランタイム一覧に追加しない。
- 既存2ログの当時の記述は維持し、追記からこの記録へ参照できるようにする。
