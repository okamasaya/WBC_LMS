"""Stable row-ID selections and contextual charts for the Iris BI exercise."""
import math
from pathlib import Path
import pandas as pd
import plotly.express as px

MEASUREMENTS = ["sepal_length", "sepal_width", "petal_length", "petal_width"]
SOURCES = ("scatter", "line", "bar")
LABELS = {"scatter": "散布図", "line": "折れ線", "bar": "棒グラフ"}


def load_iris():
    frame = pd.read_csv(Path(__file__).with_name("iris.csv"))
    frame["sample_no"] = range(1, len(frame) + 1)
    return frame


def selection_from_event(frame, source, payload):
    """None is a missing/malformed event; [] is a valid empty selection."""
    if source not in SOURCES or not isinstance(payload, dict) or not isinstance(payload.get("points"), list):
        return None
    if not payload["points"]:
        return []
    allowed = set(frame["species"] if source == "bar" else frame["sample_no"])
    values = set()
    for point in payload["points"]:
        if not isinstance(point, dict):
            continue
        custom = point.get("customdata")
        value = custom[0] if isinstance(custom, (list, tuple)) and custom else custom
        if value is None:
            value = point.get("id")
        if source == "bar":
            value = value if value is not None else point.get("x")
            if isinstance(value, str) and value in allowed:
                values.add(value)
        elif isinstance(value, str) and value.isdecimal() and int(value) in allowed:
            values.add(int(value))
        elif isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value == int(value) and int(value) in allowed:
            values.add(int(value))
    return sorted(values) if values else None


def update_selection(frame, state, source=None, payload=None, clicked=False, clear=False, reset=False):
    state = state or {"filters": {}, "revision": 0}
    filters = {key: list(values) for key, values in state.get("filters", {}).items() if key in SOURCES}
    if reset:
        filters = {}
    elif source in SOURCES:
        if clear:
            filters.pop(source, None)
        else:
            values = selection_from_event(frame, source, payload)
            if values is None:
                return state
            if clicked and filters.get(source) == values:
                filters.pop(source)
            else:
                filters[source] = values
    else:
        return state
    return {"filters": filters, "revision": state.get("revision", 0) + 1}


def filtered_rows(frame, species="all", state=None, exclude_source=None):
    mask = pd.Series(True, index=frame.index)
    if species != "all":
        mask &= frame["species"].eq(species)
    for source, values in (state or {}).get("filters", {}).items():
        if source == exclude_source or source not in SOURCES:
            continue
        mask &= frame["species" if source == "bar" else "sample_no"].isin(values)
    return frame.loc[mask].copy()


def figures(frame, species, state):
    results = []
    active = (state or {}).get("filters", {})
    for source in SOURCES:
        # Keep the source dimension available for changing/expanding its own selection.
        context = filtered_rows(frame, species, state, exclude_source=source)
        if source == "scatter":
            figure = px.scatter(context, x="sepal_length", y="sepal_width", color="species", custom_data=["sample_no"], title="Iris Scatter Plot")
        elif source == "line":
            figure = px.line(context, x="sample_no", y=["sepal_length", "petal_length"], markers=True, custom_data=["sample_no"], title="Sample Measurement Trend", labels={"sample_no": "サンプル番号", "value": "Length", "variable": "Measurement"})
        else:
            means = context.groupby("species")[MEASUREMENTS].mean().reset_index().melt(id_vars="species", var_name="measurement", value_name="mean_value")
            figure = px.bar(means, x="species", y="mean_value", color="measurement", barmode="group", custom_data=["species"], title="Average Measurements by Species")
        for trace in figure.data:
            # String IDs avoid binary encoding of numeric customdata, which can
            # omit row identity from browser click/selection events in Dash.
            values = [str(item[0]) if source == "bar" else int(item[0]) for item in trace.customdata] if trace.customdata is not None else []
            trace.customdata = [[str(value)] for value in values]
            trace.ids = [str(value) for value in values]
            selected = [index for index, value in enumerate(values) if value in active.get(source, [])] if source in active else None
            trace.update(selectedpoints=selected, selected={"marker": {"opacity": 1}}, unselected={"marker": {"opacity": 0.22}})
        figure.update_layout(
            template="plotly_white", height=420, dragmode="select", clickmode="event",
            uirevision=f"iris-{species}", selectionrevision=(state or {}).get("revision", 0),
            margin={"l": 50, "r": 20, "t": 60, "b": 70}, legend={"orientation": "h", "y": -0.22},
        )
        if context.empty:
            figure.add_annotation(text="条件に合うデータがありません。選択を解除してください。", x=.5, y=.5, xref="paper", yref="paper", showarrow=False)
        results.append(figure)
    return results


def dashboard_values(frame, species, state):
    selected = filtered_rows(frame, species, state)
    mean = f"{selected['sepal_length'].mean():.2f}" if len(selected) else "—"
    std = f"{selected['sepal_length'].std():.2f}" if len(selected) > 1 else "—"
    descriptions = []
    if species != "all":
        descriptions.append(f"Species: {species}")
    for source, values in (state or {}).get("filters", {}).items():
        label = ", ".join(values) if source == "bar" else f"{len(values)}行"
        descriptions.append(f"{LABELS[source]}: {label or '0行'}")
    summary = " ／ ".join(descriptions) or "選択条件なし（全件）"
    return len(selected), mean, std, summary, selected.to_dict("records")
