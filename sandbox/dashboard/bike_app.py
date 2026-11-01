"""Bike Sharing Dataset: basic Dash controls, linked charts and CSV export."""
from pathlib import Path
import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, State, dcc, html, dash_table

DATA = Path(__file__).resolve().parent / 'data' / 'bike'
FRAMES = {name: pd.read_csv(DATA / f'{name}.csv') for name in ('day', 'hour')}
WEATHER = {1: '晴れ・薄曇り', 2: '霧・曇り', 3: '小雨・小雪', 4: '強い雨・雪'}
app = Dash(__name__, title='Bike Sharing Dashboard')
app.layout = html.Main(style={'maxWidth': '1200px', 'margin': 'auto', 'padding': '20px', 'fontFamily': 'sans-serif'}, children=[
    html.H1('Bike Sharing Dashboard'),
    html.P('2011–2012年・Washington D.C.の貸出回数。期間や条件を変えると、KPI・グラフ・表が連動します。'),
    html.Label('集計元'), dcc.RadioItems(id='bike-grain', options=[{'label': '日別', 'value': 'day'}, {'label': '時間別', 'value': 'hour'}], value='day', inline=True),
    html.Label('期間'), dcc.DatePickerRange(id='bike-dates', min_date_allowed='2011-01-01', max_date_allowed='2012-12-31', start_date='2011-01-01', end_date='2012-12-31'),
    html.Label('天候'), dcc.Dropdown(id='bike-weather', options=[{'label': v, 'value': k} for k, v in WEATHER.items()], value=list(WEATHER), multi=True),
    html.Label('勤務日'), dcc.Dropdown(id='bike-working', options=[{'label': 'すべて', 'value': 'all'}, {'label': '勤務日', 'value': '1'}, {'label': '休日・週末', 'value': '0'}], value='all', clearable=False),
    html.Button('条件をリセット', id='bike-reset'),
    html.P(id='bike-kpi', role='status'),
    html.P('日別と時間別は同じ貸出の異なる集計です。両方を足し合わせません。平均は選択中の集計元1行あたりです。'),
    dcc.Graph(id='bike-trend'), dcc.Graph(id='bike-pattern'), dcc.Graph(id='bike-temperature'),
    html.H2('抽出データ'),
    html.Button('抽出結果をCSVで保存', id='bike-export'), dcc.Download(id='bike-download'),
    dash_table.DataTable(id='bike-table', page_size=15, sort_action='native', filter_action='native', export_format='none', style_table={'overflowX': 'auto'}),
    html.P('表の列フィルターは表内のみ。CSVは上部の条件で抽出した全行を保存します。時間別データの欠けた時間は0として補完しません。'),
    html.Footer('出典: Fanaee-T & Gama (2013), Event labeling combining ensemble detectors and background knowledge. DOI: 10.1007/s13748-013-0040-3。元データの説明はdata/bike/Readme.txtを参照。'),
])


def filtered(grain, start, end, weather, working):
    frame = FRAMES[grain]
    mask = frame['weathersit'].isin(weather or [])
    if start:
        mask &= frame['dteday'].ge(start[:10])
    if end:
        mask &= frame['dteday'].le(end[:10])
    if working != 'all':
        mask &= frame['workingday'].eq(int(working))
    return frame.loc[mask].copy()


@app.callback(Output('bike-grain', 'value'), Output('bike-dates', 'start_date'), Output('bike-dates', 'end_date'), Output('bike-weather', 'value'), Output('bike-working', 'value'), Input('bike-reset', 'n_clicks'), prevent_initial_call=True)
def reset(_):
    return 'day', '2011-01-01', '2012-12-31', list(WEATHER), 'all'


@app.callback(Output('bike-kpi', 'children'), Output('bike-trend', 'figure'), Output('bike-pattern', 'figure'), Output('bike-temperature', 'figure'), Output('bike-table', 'data'), Output('bike-table', 'columns'), Input('bike-grain', 'value'), Input('bike-dates', 'start_date'), Input('bike-dates', 'end_date'), Input('bike-weather', 'value'), Input('bike-working', 'value'))
def render(grain, start, end, weather, working):
    frame = filtered(grain, start, end, weather, working)
    mean = f"{frame['cnt'].mean():,.1f}" if len(frame) else '—'
    kpi = f"抽出 {len(frame):,}行 ｜ 貸出合計 {frame['cnt'].sum():,}回 ｜ 1行平均 {mean}回 ｜ 登録利用者 {frame['registered'].sum():,}回 ｜ 一般利用者 {frame['casual'].sum():,}回"
    daily = frame.groupby('dteday', as_index=False)[['casual', 'registered']].sum()
    trend = px.line(daily, x='dteday', y=['casual', 'registered'], title='日ごとの貸出回数（選択条件適用後）')
    dimension = 'hr' if grain == 'hour' else 'weekday'
    pattern = frame.groupby(dimension, as_index=False)['cnt'].mean()
    bars = px.bar(pattern, x=dimension, y='cnt', title='時間帯別の平均貸出回数' if grain == 'hour' else '曜日別の平均貸出回数（日曜=0）')
    bars.update_xaxes(dtick=1)
    frame['temperature_c'] = frame['temp'] * 41
    scatter = px.scatter(frame, x='temperature_c', y='cnt', color='weathersit', title='気温と貸出回数（相関であり因果関係ではありません）', render_mode='webgl')
    columns = [{'name': name, 'id': name, 'type': 'text' if name == 'dteday' else 'numeric'} for name in frame.columns]
    return kpi, trend, bars, scatter, frame.to_dict('records'), columns


@app.callback(Output('bike-download', 'data'), Input('bike-export', 'n_clicks'), State('bike-grain', 'value'), State('bike-dates', 'start_date'), State('bike-dates', 'end_date'), State('bike-weather', 'value'), State('bike-working', 'value'), prevent_initial_call=True)
def export(_, grain, start, end, weather, working):
    frame = filtered(grain, start, end, weather, working)
    return dcc.send_data_frame(frame.to_csv, f'bike_{grain}_filtered.csv', index=False)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8051, debug=False)
