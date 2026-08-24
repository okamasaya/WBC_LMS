from dash import Dash, html, dcc, Input, Output
import pandas as pd
import plotly.express as px



# =========================
# Data
# =========================

df = pd.read_csv("iris.csv")

# 折れ線グラフ用のサンプル番号
df["sample_no"] = range(1, len(df) + 1)

measurement_columns = [
    "sepal_length",
    "sepal_width",
    "petal_length",
    "petal_width"
]


# =========================
# KPI
# =========================

sepal_length_mean = df["sepal_length"].mean()
sepal_length_std = df["sepal_length"].std()


# =========================
# Figures
# =========================

# 散布図
scatter_fig = px.scatter(
    df,
    x="sepal_length",
    y="sepal_width",
    color="species",
    title="Iris Scatter Plot",
    labels={
        "sepal_length": "Sepal Length",
        "sepal_width": "Sepal Width",
        "species": "Species"
    }
)


# 折れ線グラフ
line_fig = px.line(
    df,
    x="sample_no",
    y=[
        "sepal_length",
        "petal_length"
    ],
    title="Sample Measurement Trend",
    labels={
        "sample_no": "Sample Number",
        "value": "Length",
        "variable": "Measurement"
    }
)


# 品種別平均値を計算
species_mean_df = (
    df.groupby("species")[measurement_columns]
    .mean()
    .reset_index()
)

# 棒グラフで扱いやすい縦長形式に変換
species_mean_long_df = species_mean_df.melt(
    id_vars="species",
    value_vars=measurement_columns,
    var_name="measurement",
    value_name="mean_value"
)

bar_fig = px.bar(
    species_mean_long_df,
    x="species",
    y="mean_value",
    color="measurement",
    barmode="group",
    title="Average Measurements by Species",
    labels={
        "species": "Species",
        "mean_value": "Mean Value",
        "measurement": "Measurement"
    }
)


# =========================
# Dash App
# =========================

app = Dash(__name__)

app.layout = html.Div(

    style={
        "backgroundColor": "#f4f6f9",
        "minHeight": "100vh",
        "padding": "24px",
        "fontFamily": "Arial, sans-serif"
    },

    children=[

        html.H1(
            "Iris Dashboard",
            style={
                "textAlign": "center",
                "color": "#2d3748"
            }
        ),

        html.Div(
            id="kpi-mean",
            style={
                "fontSize": "36px",
                "fontWeight": "bold",
                "color": "#3182ce"
            }
        ),

        html.Div(
            id="kpi-std",
            style={
                "fontSize": "36px",
                "fontWeight": "bold",
                "color": "#e53e3e"
            }
        ),

        html.P(
            "Dash主要コンポーネントの動作確認",
            style={
                "textAlign": "center",
                "color": "#718096"
            }
        ),


        html.Div(
            style={
                "backgroundColor": "white",
                "padding": "20px",
                "marginBottom": "20px",
                "borderRadius": "10px"
            },
            children=[
                html.Label(
                    "Species",
                    style={
                        "fontWeight": "bold",
                        "marginBottom": "8px",
                        "display": "block"
                    }
                ),

            dcc.Dropdown(
                id="species-dropdown",
                    options=[
                        {"label": "すべて", "value": "all"},
                        *[
                            {"label": species.title(), "value": species}
                            for species in df["species"].unique()
                        ]
                    ],
                    value="all",
                        clearable=False
                )
            ]
        ),



        # =====================
        # KPI Area
        # =====================

        html.Div(

            style={
                "display": "flex",
                "gap": "20px",
                "marginBottom": "20px"
            },

            children=[

                html.Div(

                    style={
                        "backgroundColor": "white",
                        "padding": "20px",
                        "borderRadius": "10px",
                        "boxShadow": "0 2px 6px rgba(0, 0, 0, 0.1)",
                        "flex": "1",
                        "textAlign": "center"
                    },

                    children=[

                        html.H3(
                            "Sepal Length 平均",
                            style={
                                "color": "#718096",
                                "marginBottom": "10px"
                            }
                        ),

                        html.Div(
                            f"{sepal_length_mean:.2f}",
                            style={
                                "fontSize": "36px",
                                "fontWeight": "bold",
                                "color": "#3182ce"
                            }
                        )
                    ]
                ),

                html.Div(

                    style={
                        "backgroundColor": "white",
                        "padding": "20px",
                        "borderRadius": "10px",
                        "boxShadow": "0 2px 6px rgba(0, 0, 0, 0.1)",
                        "flex": "1",
                        "textAlign": "center"
                    },

                    children=[

                        html.H3(
                            "Sepal Length 標準偏差",
                            style={
                                "color": "#718096",
                                "marginBottom": "10px"
                            }
                        ),

                        html.Div(
                            f"{sepal_length_std:.2f}",
                            style={
                                "fontSize": "36px",
                                "fontWeight": "bold",
                                "color": "#e53e3e"
                            }
                        )
                    ]
                )
            ]
        ),

        # =====================
        # Graph Area 1
        # =====================

        html.Div(

            style={
                "display": "flex",
                "gap": "20px",
                "marginBottom": "20px"
            },

            children=[

                html.Div(
                    dcc.Graph(
                        id="iris-scatter",
                        figure=scatter_fig
                    ),
                    style={
                        "backgroundColor": "white",
                        "borderRadius": "10px",
                        "flex": "1"
                    }
                ),

                html.Div(
                    dcc.Graph(
                        id="iris-line",
                        figure=line_fig
                    ),
                    style={
                        "backgroundColor": "white",
                        "borderRadius": "10px",
                        "flex": "1"
                    }
                )
            ]
        ),

        # =====================
        # Graph Area 2
        # =====================

        html.Div(

            style={
                "backgroundColor": "white",
                "borderRadius": "10px"
            },

            children=[

                dcc.Graph(
                    id="iris-bar",
                    figure=bar_fig
                )
            ]
        )
    ]
)

# =========================
# callback
# =========================


@app.callback(
    Output("kpi-mean", "children"),
    Output("kpi-std", "children"),
    Output("iris-scatter", "figure"),
    Output("iris-line", "figure"),
    Output("iris-bar", "figure"),
    Input("species-dropdown", "value")
)
def update_dashboard(selected_species):

    # Speciesによる絞り込み
    if selected_species == "all":
        filtered_df = df.copy()
        selection_label = "すべて"
    else:
        filtered_df = df[
            df["species"] == selected_species
        ].copy()

        selection_label = selected_species.title()

    # -------------------------
    # KPI
    # -------------------------

    mean_value = filtered_df["sepal_length"].mean()
    std_value = filtered_df["sepal_length"].std()

    mean_text = f"{mean_value:.2f}"
    std_text = f"{std_value:.2f}"

    # -------------------------
    # Scatter Plot
    # -------------------------

    scatter_fig = px.scatter(
        filtered_df,
        x="sepal_length",
        y="sepal_width",
        color="species",
        title=f"Scatter Plot：{selection_label}",
        labels={
            "sepal_length": "Sepal Length",
            "sepal_width": "Sepal Width",
            "species": "Species"
        }
    )

    # -------------------------
    # Line Graph
    # -------------------------

    line_fig = px.line(
        filtered_df,
        x="sample_no",
        y=[
            "sepal_length",
            "petal_length"
        ],
        title=f"Measurement Trend：{selection_label}",
        labels={
            "sample_no": "Sample Number",
            "value": "Length",
            "variable": "Measurement"
        }
    )

    # -------------------------
    # Bar Graph
    # -------------------------

    species_mean_df = (
        filtered_df
        .groupby("species")[measurement_columns]
        .mean()
        .reset_index()
    )

    species_mean_long_df = species_mean_df.melt(
        id_vars="species",
        value_vars=measurement_columns,
        var_name="measurement",
        value_name="mean_value"
    )

    bar_fig = px.bar(
        species_mean_long_df,
        x="species",
        y="mean_value",
        color="measurement",
        barmode="group",
        title=f"Average Measurements：{selection_label}",
        labels={
            "species": "Species",
            "mean_value": "Mean Value",
            "measurement": "Measurement"
        }
    )

    return (
        mean_text,
        std_text,
        scatter_fig,
        line_fig,
        bar_fig
    )



# =========================
# Run
# =========================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=8050,
        debug=True
    )
