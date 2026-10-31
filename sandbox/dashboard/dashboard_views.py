"""Dashboard presentation functions; inference lives in bkt.py."""
import pandas as pd
import plotly.graph_objects as go


def empty_figure(message):
    figure = go.Figure()
    figure.add_annotation(text=message, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
    figure.update_layout(template="plotly_white", height=360, xaxis={"visible": False}, yaxis={"visible": False})
    return figure


def mastery_figure(states):
    if not states:
        return empty_figure("推定対象の回答がありません")
    frame = pd.DataFrame(states).sort_values("PMastery")
    figure = go.Figure(go.Bar(
        x=frame["PMastery"], y=frame["StudentID"] + " / " + frame["SkillName"], orientation="h",
        marker_color="#285caa", customdata=frame[["Attempts", "PAfterObservation"]],
        hovertemplate="%{y}<br>学習遷移後 %{x:.1%}<br>事後確率 %{customdata[1]:.1%}<br>回答数 %{customdata[0]}<extra></extra>",
    ))
    figure.update_layout(template="plotly_white", xaxis={"range": [0, 1], "tickformat": ".0%", "title": "学習遷移後の習得確率（仮設定）"}, height=max(360, 50 * len(frame)), margin={"l": 20, "r": 20, "t": 30, "b": 60})
    return figure


def history_figure(history):
    if not history:
        return empty_figure("CSVを取り込むか、サンプルを読み込んでください")
    frame = pd.DataFrame(history)
    figure = go.Figure()
    colors = ["#285caa", "#aa5428", "#198065", "#8056ae"]
    for index, ((student, skill), group) in enumerate(frame.groupby(["StudentID", "SkillID"], sort=True)):
        group = group.sort_values("AttemptIndex")
        label = f"{student} / {group.iloc[0]['SkillName']}"
        color = colors[index % len(colors)]
        for column, suffix, dash in [("PAfterLearning", "学習遷移後", "solid"), ("PAfterObservation", "正誤更新後", "dot")]:
            figure.add_trace(go.Scatter(
                x=pd.to_datetime(group["AnsweredAt"], utc=True).dt.tz_convert("Asia/Tokyo").dt.strftime("%Y-%m-%d %H:%M:%S"), y=group[column], name=f"{label} · {suffix}", mode="lines+markers",
                line={"color": color, "dash": dash},
                customdata=group[["ResultID", "IsCorrect", "AttemptIndex"]],
                hovertemplate="%{x}<br>習得確率 %{y:.1%}<br>回答順 %{customdata[2]} / 正解 %{customdata[1]}<br>%{customdata[0]}<extra>%{fullData.name}</extra>",
            ))
    figure.update_layout(template="plotly_white", yaxis={"range": [0, 1], "tickformat": ".0%"}, xaxis_title="回答時刻（日本時間）", height=420, legend={"orientation": "h", "y": -0.3}, margin={"l": 50, "r": 20, "t": 20, "b": 100})
    return figure


def self_report_figure(records):
    figure = go.Figure()
    total = 0
    for field, labels, name in [
        ("ConfidenceLevel", ["1 自信あり", "2 少し自信", "3 やや不安", "4 直感"], "回答時の自信度"),
        ("UnderstandingLevel", ["0 分からない", "1 まだ少し", "2 だいたい", "3 理解できた"], "解説後の理解度"),
    ]:
        counts = [sum(str(record.get(field, "")).strip() == str(index if field == "UnderstandingLevel" else index + 1) for record in records) for index in range(4)]
        total += sum(counts)
        figure.add_trace(go.Bar(y=labels, x=counts, name=name, orientation="h"))
    if not total:
        return empty_figure("自己申告の記録がありません（未入力は集計対象外）")
    figure.update_layout(template="plotly_white", height=460, xaxis_title="回答件数", xaxis={"dtick": 1}, yaxis={"autorange": "reversed", "automargin": True}, legend={"orientation": "h"}, margin={"l": 20, "r": 20, "t": 20, "b": 70})
    return figure
