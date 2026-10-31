"""Local CSV -> classic BKT -> Dash prototype. Uploaded records are memory-only."""
import base64
import binascii
import csv
from io import StringIO
import json
from pathlib import Path

from dash import Dash, Input, Output, State, ctx, dcc, html, dash_table, no_update

from bkt import BKTParameters, MODEL_VERSION, estimate
from learning_data import normalize_records, parse_question_csv
from demo_data import sample_records
from dashboard_views import empty_figure, mastery_figure, history_figure, self_report_figure

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "bkt_parameters.json").read_text(encoding="utf-8"))
if CONFIG["modelVersion"] != MODEL_VERSION or CONFIG["parameterSource"] != "manual_assumption":
    raise ValueError("未対応のBKT設定です。")
DEFAULTS = BKTParameters(**CONFIG["defaults"])
SKILL_PARAMETERS = {skill: BKTParameters(**values) for skill, values in CONFIG["bySkill"].items()}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024


def csv_text(rows):
    if not rows:
        return ""
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return "\ufeff" + stream.getvalue()


def import_uploads(contents, filenames, fallback_student="", confirmed=False):
    if not contents:
        raise ValueError("CSVファイルを選んでください。")
    raw = []
    if isinstance(contents, str):
        contents, filenames = [contents], [filenames]
    if not isinstance(contents, list) or not isinstance(filenames, list) or len(contents) != len(filenames):
        raise ValueError("選択ファイルとアップロード内容が一致しません。")
    for content, name in zip(contents, filenames):
        if not str(name).lower().endswith(".csv"):
            raise ValueError("CSVファイルを指定してください。")
        try:
            payload = content.split(",", 1)[1]
            if len(payload) > (MAX_UPLOAD_BYTES * 4 // 3 + 8):
                raise ValueError("1ファイルは8MB以下にしてください。")
            decoded = base64.b64decode(payload, validate=True)
            if len(decoded) > MAX_UPLOAD_BYTES:
                raise ValueError("1ファイルは8MB以下にしてください。")
            text = decoded.decode("utf-8-sig")
        except (IndexError, binascii.Error, UnicodeDecodeError) as error:
            raise ValueError("UTF-8のCSVファイルを指定してください。") from error
        raw.extend(parse_question_csv(text))
    result = normalize_records(raw, fallback_student, confirmed)
    return {**result, "source": "uploaded"}


def table(identifier, columns):
    return dash_table.DataTable(
        id=identifier, columns=columns, data=[], page_size=12, sort_action="native",
        style_table={"overflowX": "auto"},
        style_cell={"fontFamily": "inherit", "textAlign": "left", "minWidth": "90px", "maxWidth": "300px", "whiteSpace": "normal", "padding": "10px"},
        style_header={"backgroundColor": "#edf2fa", "fontWeight": "bold"},
    )


def probability_column(name, label):
    return {"id": name, "name": label, "type": "numeric", "format": {"specifier": ".1%"}}


app = Dash(__name__, assets_folder=str(ROOT / "assets"), title="ALP–BKT 開発用")
app.layout = html.Div(className="alp-dashboard", children=[
    dcc.Store(id="raw-data", data={"records": [], "excluded": [], "source": "empty", "input_count": 0}),
    dcc.Store(id="bkt-estimates"), dcc.Download(id="bkt-download"),
    html.Header([html.Span("開発中", className="alp-badge"), html.H1("ALP–BKT 学習ダッシュボード"), html.P("正誤の記録と、仮パラメータによる推定を確認します。")]),
    html.Section(className="alp-card", children=[
        html.H2("1. 学習ログを読み込む"),
        dcc.Upload(id="csv-upload", children=html.Div(["QuestionResult.csv または統合Raw CSVを選択・ドロップ", html.Small("UTF-8・複数ファイル可。アップロード内容はファイルへ保存しません。")]), multiple=True, accept=".csv", className="alp-upload"),
        html.Div(id="selected-files"),
        html.Div(className="alp-controls", children=[
            html.Label(["StudentIDが空欄の行に適用するID（任意）", dcc.Input(id="fallback-student", type="text", placeholder="例: learner-001", debounce=True)]),
            dcc.Checklist(id="confirm-single", options=[{"label": "空欄の行は、すべて同じ1人のログです", "value": "confirmed"}], value=[]),
        ]),
        html.P("ID未設定・スキル未設定・時刻不正・未回答の行は推定から除外します。同じResultIDの回答は重複更新せず、競合する場合は取り込みを止めます。", className="alp-note"),
        html.Div(className="alp-actions", children=[html.Button("CSVを取り込む", id="import-data"), html.Button("サンプルで試す", id="sample-data"), html.Button("データをクリア", id="clear-data")]),
        html.Div(id="import-status", role="status"),
        html.Details([html.Summary("除外した行・理由"), table("excluded-table", [{"id": key, "name": label} for key, label in [("Row", "取込行"), ("ResultID", "ResultID"), ("Reason", "除外理由")]])]),
    ]),
    html.Section(className="alp-card", children=[
        html.H2("2. 対象と仮パラメータ"),
        html.Div(className="alp-filter-grid", children=[
            html.Label(["学習者", dcc.Dropdown(id="student-filter", options=[], clearable=False)]),
            html.Label(["スキル", dcc.Dropdown(id="skill-filter", options=[], clearable=False)]),
            html.Label(["モード", dcc.Dropdown(id="mode-filter", options=[], clearable=False)]),
        ]),
        html.Details([html.Summary("BKTパラメータを調整する（未校正の仮設定）"),
            html.Div(className="alp-parameter-grid", children=[html.Label([label, dcc.Input(id=identifier, type="number", min=0, max=1, step=0.01, value=value, debounce=True)]) for identifier, label, value in [
                ("p-l0", "P(L0) 初期習得確率", DEFAULTS.p_l0), ("p-t", "P(T) 学習遷移確率", DEFAULTS.p_t),
                ("p-g", "P(G) 未習得でも正解する確率", DEFAULTS.p_g), ("p-s", "P(S) 習得済みでも誤答する確率", DEFAULTS.p_s)]]),
            html.P(f"スキル別の設定がある場合はそちらを優先します（現在 {len(SKILL_PARAMETERS)} スキル）。", className="alp-note"),
        ]),
        html.P("標準BKTの仮設定です。各回答で正誤による事後更新と学習遷移を行い、忘却は仮定しません。Actualを含め、対象にした全回答へ同じ遷移規則を適用します。自信度・解説理解度・難易度・回答時間は推定に使いません。", className="alp-note"),
        html.P("対象を絞ると、その対象の回答だけで初期値から再計算します。正解率と推定習得確率、自己申告の理解度は別の指標です。", className="alp-note"),
        html.Div(id="model-status", role="status"),
    ]),
    html.Div(id="kpis", className="alp-kpis"),
    html.Div(className="alp-chart-grid", children=[
        html.Section(className="alp-card", children=[html.H2("スキル別の推定状態"), dcc.Graph(id="mastery-chart", figure=empty_figure("学習ログを読み込んでください"))]),
        html.Section(className="alp-card", children=[html.H2("回答ごとの推移"), html.P("実線：学習遷移後 ／ 破線：正誤による事後更新", className="alp-note"), dcc.Graph(id="history-chart", figure=empty_figure("学習ログを読み込んでください"))]),
    ]),
    html.Section(className="alp-card", children=[html.H2("自己申告の記録（BKT入力には未使用）"), dcc.Graph(id="self-report-chart", figure=empty_figure("学習ログを読み込んでください"))]),
    html.Section(className="alp-card", children=[
        html.H2("推定結果の確認・出力"),
        html.P("次回時点の確率は学習遷移を仮定した値です。成績・合否や実測の理解度として扱わず、パラメータと併せて確認してください。", className="alp-note"),
        table("state-table", [{"id": "StudentID", "name": "学習者"}, {"id": "SkillName", "name": "スキル"}, probability_column("PMastery", "学習遷移後"), probability_column("PAfterObservation", "正誤更新後"), probability_column("PNextCorrect", "次回正解確率"), {"id": "Attempts", "name": "回答数"}]),
        html.Details([html.Summary("回答ごとの推定履歴"), table("history-table", [{"id": key, "name": label} for key, label in [("StudentID", "学習者"), ("SkillName", "スキル"), ("ResultID", "ResultID"), ("AnsweredAt", "回答時刻（UTC）"), ("AttemptIndex", "回答順"), ("IsCorrect", "正解")]] + [probability_column(key, label) for key, label in [("PBefore", "事前"), ("PAfterObservation", "正誤更新後"), ("PAfterLearning", "学習遷移後")]])]),
        html.Div(className="alp-actions", children=[html.Button(label, id=identifier, disabled=True) for identifier, label in [("export-state", "KnowledgeState.csv"), ("export-history", "KnowledgeStateHistory.csv"), ("export-parameters", "BKTParameter.csv")]]),
    ]),
])


@app.callback(Output("selected-files", "children"), Input("csv-upload", "filename"))
def show_files(filenames):
    if isinstance(filenames, str):
        filenames = [filenames]
    return "選択済み: " + " / ".join(filenames) if filenames else "まだファイルは選択されていません。"


@app.callback(Output("raw-data", "data"), Output("import-status", "children"), Output("excluded-table", "data"), Output("csv-upload", "contents"), Output("csv-upload", "filename"),
              Input("import-data", "n_clicks"), Input("sample-data", "n_clicks"), Input("clear-data", "n_clicks"),
              State("csv-upload", "contents"), State("csv-upload", "filename"), State("fallback-student", "value"), State("confirm-single", "value"), prevent_initial_call=True)
def load_data(import_clicks, sample_clicks, clear_clicks, contents, filenames, fallback, confirmed):
    trigger = ctx.triggered_id
    if trigger == "clear-data":
        return {"records": [], "excluded": [], "source": "empty", "input_count": 0}, "データをクリアしました。", [], None, None
    try:
        if trigger == "sample-data":
            data = {**normalize_records(sample_records()), "source": "demo"}
        else:
            data = import_uploads(contents, filenames, fallback or "", "confirmed" in (confirmed or []))
        label = "サンプル（架空データ）" if data["source"] == "demo" else "アップロードしたログ"
        message = f"{label}: 入力 {data['input_count']}件 ／ 推定対象 {len(data['records'])}件 ／ 除外 {len(data['excluded'])}件。"
        return data, message, data["excluded"], None if trigger == "sample-data" else no_update, None if trigger == "sample-data" else no_update
    except ValueError as error:
        # Clear previous results so a failed upload cannot be mistaken for new estimates.
        return {"records": [], "excluded": [], "source": "empty", "input_count": 0}, f"取り込めません: {error}", [], no_update, no_update


@app.callback(Output("student-filter", "options"), Output("student-filter", "value"), Output("skill-filter", "options"), Output("skill-filter", "value"), Output("mode-filter", "options"), Output("mode-filter", "value"), Input("raw-data", "data"))
def filter_options(data):
    records = (data or {}).get("records", [])
    students = sorted({r["StudentID"] for r in records})
    skills = {r["SkillID"]: r.get("SkillName") or r["SkillID"] for r in records}
    modes = sorted({r["Mode"] for r in records})
    def options(values, labels=None):
        return [{"label": "すべて", "value": "__all__"}] + [{"label": labels[value] if labels else value, "value": value} for value in values]
    return options(students), students[0] if students else "__all__", options(sorted(skills), skills), sorted(skills)[0] if skills else "__all__", options(modes), "__all__"


@app.callback(Output("bkt-estimates", "data"), Output("model-status", "children"), Output("kpis", "children"),
              Output("mastery-chart", "figure"), Output("history-chart", "figure"), Output("self-report-chart", "figure"),
              Output("state-table", "data"), Output("history-table", "data"), Output("export-state", "disabled"), Output("export-history", "disabled"), Output("export-parameters", "disabled"),
              Input("raw-data", "data"), Input("student-filter", "value"), Input("skill-filter", "value"), Input("mode-filter", "value"),
              Input("p-l0", "value"), Input("p-t", "value"), Input("p-g", "value"), Input("p-s", "value"))
def calculate(data, student, skill, mode, p_l0, p_t, p_g, p_s):
    records = (data or {}).get("records", [])
    selected = [r for r in records if (student == "__all__" or r["StudentID"] == student) and (skill == "__all__" or r["SkillID"] == skill) and (mode == "__all__" or r["Mode"] == mode)]
    try:
        parameters = BKTParameters(p_l0=p_l0, p_t=p_t, p_g=p_g, p_s=p_s)
        result = estimate(selected, parameters, SKILL_PARAMETERS)
    except ValueError as error:
        empty = empty_figure("パラメータを確認してください")
        return None, str(error), [], empty, empty, empty, [], [], True, True, True
    counts = [("回答数", len(selected)), ("学習者", len({r['StudentID'] for r in selected})), ("スキル", len({r['SkillID'] for r in selected})), ("正解率（実測）", f"{sum(r['IsCorrect'] for r in selected) / len(selected):.0%}" if selected else "—")]
    kpis = [html.Div([html.Span(label), html.Strong(value)], className="alp-kpi") for label, value in counts]
    status = "未校正の仮パラメータによる推定です。" if selected else "学習ログと対象を選択してください。"
    disabled = not bool(result["history"])
    return result, status, kpis, mastery_figure(result["states"]), history_figure(result["history"]), self_report_figure(selected), result["states"], result["history"], disabled, disabled, disabled


@app.callback(Output("bkt-download", "data"), Input("export-state", "n_clicks"), Input("export-history", "n_clicks"), Input("export-parameters", "n_clicks"), State("bkt-estimates", "data"), prevent_initial_call=True)
def download_results(state_clicks, history_clicks, parameter_clicks, data):
    if not data or not data.get("history"):
        return no_update
    key, filename = {"export-state": ("states", "KnowledgeState.csv"), "export-history": ("history", "KnowledgeStateHistory.csv"), "export-parameters": ("parameters", "BKTParameter.csv")}[ctx.triggered_id]
    return dcc.send_string(csv_text(data[key]), filename, type="text/csv;charset=utf-8")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8051, debug=False)
