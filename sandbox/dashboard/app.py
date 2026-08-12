from dash import Dash, html, dcc
import plotly.express as px

# -------------------------
# Sample Data
# -------------------------

df = px.data.iris()

fig = px.scatter(
    df,
    x="sepal_length",
    y="sepal_width",
    color="species",
    title="Iris Scatter Plot"
)

# -------------------------
# Dash App
# -------------------------

app = Dash(__name__)

app.layout = html.Div([

    html.H1("Iris Dashboard"),

    html.P("GitHub Codespaces + Dash 動作確認"),

    dcc.Graph(
        id="iris-scatter",
        figure=fig
    )

])

# -------------------------
# Run
# -------------------------

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8050,
        debug=True
    )
