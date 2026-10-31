"""Iris BI exercise: clicking/brush selection links KPIs, charts and the row table."""
from pathlib import Path
from dash import Dash, Input, Output, State, ctx, dcc, html, dash_table, no_update
from iris_crossfilter import load_iris, update_selection, figures, dashboard_values, SOURCES

DF = load_iris()
EMPTY_SELECTION = {"filters": {}, "revision": 0}
app = Dash(__name__, assets_folder=str(Path(__file__).resolve().parent / "assets"), title="Iris BI Dashboard")


def graph_card(source, label, figure):
    return html.Section(className="iris-card", children=[
        html.Div(className="iris-chart-heading", children=[html.H2(label), html.Button("この選択を解除", id=f"clear-{source}")]),
        dcc.Graph(id=f"iris-{source}", figure=figure, config={"displaylogo": False, "modeBarButtonsToAdd": ["select2d", "lasso2d"]}),
    ])


initial_figures = figures(DF, "all", EMPTY_SELECTION)
app.layout = html.Div(className="iris-dashboard", children=[
    dcc.Store(id="iris-selection", data=EMPTY_SELECTION),
    html.Header([html.H1("Iris BI Dashboard"), html.P("グラフをクリック・範囲選択して、KPI・他のグラフ・データ表を絞り込みます。")]),
    html.Section(className="iris-card", children=[
        html.Label(["Species", dcc.Dropdown(id="species-dropdown", options=[{"label": "すべて", "value": "all"}] + [{"label": species.title(), "value": species} for species in DF["species"].unique()], value="all", clearable=False)]),
        html.Div(className="iris-actions", children=[html.Button("すべてリセット", id="reset-iris"), html.Strong(id="selection-summary", role="status")]),
        html.P("クリックは1点・1品種、ドラッグは複数行を選択します。同じ要素の再クリック、または各グラフのボタンで解除できます。複数の選択は共通する行へ絞り込みます。Speciesを変更するとグラフ選択はリセットされます。", className="iris-note"),
        html.P("各グラフは自身の選択を変更できる範囲を残します。KPIと表は、すべての条件を適用した結果です。", className="iris-note"),
    ]),
    html.Div(className="iris-kpis", children=[html.Div(className="iris-kpi", children=[html.Span(label), html.Strong(id=identifier)]) for identifier, label in [("kpi-count", "抽出件数"), ("kpi-mean", "Sepal Length 平均"), ("kpi-std", "Sepal Length 標準偏差")]]),
    html.Div(className="iris-chart-grid", children=[graph_card("scatter", "散布図", initial_figures[0]), graph_card("line", "折れ線", initial_figures[1])]),
    graph_card("bar", "品種別平均", initial_figures[2]),
    html.Section(className="iris-card", children=[
        html.H2("抽出したデータ"),
        dash_table.DataTable(id="iris-table", data=DF.to_dict("records"), columns=[{"id": name, "name": name, "type": "text" if name == "species" else "numeric"} for name in ["sample_no", "species", "sepal_length", "sepal_width", "petal_length", "petal_width"]], page_size=12, sort_action="native", style_table={"overflowX": "auto"}, style_cell={"fontFamily": "inherit", "textAlign": "left", "padding": "10px", "minWidth": "90px"}, style_header={"backgroundColor": "#edf2fa", "fontWeight": "bold"}),
    ]),
])

# Clear native event payloads after handling them. Stable row-ID filters in the store
# remain authoritative and let the same point be clicked again after a reset.
EVENT_OUTPUTS = [Output(f"iris-{source}", property) for source in SOURCES for property in ("clickData", "selectedData")]


@app.callback(
    Output("iris-selection", "data"), *EVENT_OUTPUTS, Output("species-dropdown", "value"),
    *[Input(f"iris-{source}", property) for source in SOURCES for property in ("clickData", "selectedData")],
    *[Input(f"clear-{source}", "n_clicks") for source in SOURCES], Input("reset-iris", "n_clicks"), Input("species-dropdown", "value"),
    State("iris-selection", "data"), prevent_initial_call=True,
)
def handle_selection(*args):
    state = args[-1] or EMPTY_SELECTION
    trigger = ctx.triggered_id
    if trigger == "reset-iris":
        return update_selection(DF, state, reset=True), *([None] * 6), "all"
    if trigger == "species-dropdown":
        return update_selection(DF, state, reset=True), *([None] * 6), no_update
    if trigger and trigger.startswith("clear-"):
        updated = update_selection(DF, state, source=trigger[6:], clear=True)
    elif trigger and trigger.startswith("iris-"):
        source = trigger[5:]
        property = next(iter(ctx.triggered_prop_ids)).split(".")[-1]
        index = SOURCES.index(source) * 2 + (1 if property == "selectedData" else 0)
        payload = args[index]
        if payload is None:
            return (no_update,) * 8
        updated = update_selection(DF, state, source=source, payload=payload, clicked=property == "clickData")
        if updated == state:
            return (no_update,) * 8
    else:
        return (no_update,) * 8
    return updated, *([None] * 6), no_update


@app.callback(
    Output("kpi-count", "children"), Output("kpi-mean", "children"), Output("kpi-std", "children"), Output("selection-summary", "children"),
    Output("iris-scatter", "figure"), Output("iris-line", "figure"), Output("iris-bar", "figure"), Output("iris-table", "data"),
    Input("species-dropdown", "value"), Input("iris-selection", "data"),
)
def update_dashboard(selected_species="all", state=None):
    count, mean, std, summary, rows = dashboard_values(DF, selected_species, state)
    charts = figures(DF, selected_species, state)
    return count, mean, std, summary, *charts, rows


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8050, debug=False)
