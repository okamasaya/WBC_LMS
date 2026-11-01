"""Dash入門・時系列編。起動: python sample_dsbd_bike.py（ポート8053）。"""
from datetime import datetime, timezone, timedelta
from math import ceil
from time import perf_counter
from bike_data_service import BikeDataService
import sqlite3
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, ctx, dcc, html, dash_table, no_update
from bike_timeseries import (filter_rows, aggregate, previous_year, quality, bounds,
                             drill_period, METRICS, LEVELS, WEATHER, MIN_DATE, MAX_DATE)

app = Dash(__name__, title='Bike時系列BIサンプル')
SERVICE = BikeDataService()
INITIAL_DATA = SERVICE.reload('csv')


def graph(identifier):
    return dcc.Graph(id=identifier, config={'displaylogo': False, 'scrollZoom': True,
        'displayModeBar': True, 'toImageButtonOptions': {'format': 'png', 'filename': identifier, 'scale': 2}})



def dropdown(identifier, label, options, value):
    return html.Label([label, dcc.Dropdown(id=identifier, options=[{'label': v, 'value': k} for k, v in options.items()], value=value, clearable=False)])


app.layout = html.Main(className='bike-dashboard', children=[
    dcc.Store(id='bike-history', data=[]),
    dcc.Store(id='bike-data', data=INITIAL_DATA),
    dcc.Store(id='bike-print-signal'),
    dcc.Interval(id='bike-refresh-clock', interval=60000, disabled=True),
    html.H1('Bike時系列BIサンプル'),
    html.P('集計 → 期間指定 → 詳細確認。グラフのズームは表示だけを変え、「表示期間を全体に適用」でKPI・明細も絞り込みます。'),
    html.Section(className='bike-panel', children=[
        dropdown('bike-backend', 'データ接続先', {'csv': 'CSV', 'sqlite': 'SQLite（ローカルDB）'}, 'csv'),
        html.Button('データを再読込', id='bike-refresh'),
        dcc.Checklist(id='bike-auto-refresh', options=[{'label': '60秒ごとに再読込', 'value': 'auto'}], value=[]),
        html.P(id='bike-refresh-status', role='status'),
        html.Button('印刷・PDF保存', id='bike-print'),
        html.P('グラフ右上のカメラでPNG保存できます。PDFはブラウザの印刷先で選びます。印刷する表は表示中のページのみ、全明細はCSVをご利用ください。'),
        html.Label(['期間', dcc.DatePickerRange(id='bike-dates', min_date_allowed=MIN_DATE, max_date_allowed=MAX_DATE, start_date='2012-01-01', end_date=MAX_DATE, display_format='YYYY-MM-DD')]),
        dropdown('bike-source', '集計元（日別と時間別を重複加算しません）', {'day': '日別データ', 'hour': '時間別データ'}, 'day'),
        dropdown('bike-level', '表示粒度', LEVELS, 'M'),
        dropdown('bike-metric', '指標', METRICS, 'cnt'),
        dropdown('bike-statistic', '集計方法', {'sum': '貸出回数の合計', 'mean': '観測1行あたりの平均'}, 'sum'),
        html.Label(['天候', dcc.Dropdown(id='bike-weather', options=[{'label': v, 'value': k} for k, v in WEATHER.items()], value=list(WEATHER), multi=True)]),
        dropdown('bike-working', '勤務日', {'all': 'すべて', '1': '勤務日', '0': '休日・週末'}, 'all'),
        html.Div(className='bike-actions', children=[html.Button('表示期間を全体に適用', id='bike-apply'), html.Button('ひとつ戻る', id='bike-back'), html.Button('初期表示に戻す', id='bike-reset')]),
        html.P(id='bike-navigation', role='status'),
    ]),
    dcc.Loading(type='circle', children=html.Div([
        html.P(id='bike-kpi', className='bike-panel', role='status'),
        html.P(id='bike-quality'),
        html.P('主グラフの点をクリックすると、月・週→日→時間帯へ進みます。時間別表示は時間別CSVを使用します。戻るボタンで前の期間と粒度へ戻れます。'),
        graph('bike-series'),
        graph('bike-comparison'),
        html.P('前年は同じ月日を対応させ、同じ天候・勤務日条件を適用します。曜日は一致しません。前年に存在しない2月29日や未収録期間は空白です。'),
        graph('bike-moving'),
        html.P('移動平均は直近7暦日がすべて観測されている場所だけを表示します。条件による除外や未観測の時間・日を0で補完しません。破線は抽出された日別値の平均です。'),
        html.H2('根拠となる明細'),
        html.Button('抽出明細をCSV保存', id='bike-export'), dcc.Download(id='bike-download'),
        html.P(id='bike-export-status', role='status'),
        dash_table.DataTable(id='bike-table', page_current=0, page_size=15, page_action='custom', page_count=0, sort_action='custom', sort_by=[], style_table={'overflowX': 'auto'}),
    ])),
    html.Details([html.Summary('開発用の処理情報'), html.P(id='bike-processing')]),
    html.Footer('データ: Fanaee-T & Gama (2013), DOI:10.1007/s13748-013-0040-3。列定義・出典はdata/bike/Readme.txt。ズーム、凡例、表の並べ替えはKPIへ影響しません。'),
])


# 1. Inputは操作のきっかけ。Stateは押下時点の期間・履歴・ズーム範囲。
@app.callback(
    Output('bike-dates', 'start_date'), Output('bike-dates', 'end_date'), Output('bike-level', 'value'),
    Output('bike-history', 'data'), Output('bike-navigation', 'children'),
    Output('bike-series', 'clickData'), Output('bike-series', 'relayoutData'),
    Output('bike-source', 'value'), Output('bike-metric', 'value'), Output('bike-statistic', 'value'), Output('bike-weather', 'value'), Output('bike-working', 'value'),
    Input('bike-apply', 'n_clicks'), Input('bike-back', 'n_clicks'), Input('bike-reset', 'n_clicks'), Input('bike-series', 'clickData'),
    Input('bike-dates', 'start_date'), Input('bike-dates', 'end_date'), Input('bike-level', 'value'),
    State('bike-history', 'data'), State('bike-series', 'relayoutData'), prevent_initial_call=True,
)
def navigate(apply, back, reset, click, start, end, level, history, zoom):
    trigger = ctx.triggered_id
    history = list(history or [])
    unchanged = [no_update] * 12
    if trigger == 'bike-reset':
        return '2012-01-01', MAX_DATE, 'M', [], '初期表示に戻しました。', None, None, 'day', 'cnt', 'sum', list(WEATHER), 'all'
    if trigger == 'bike-back':
        if not history:
            unchanged[4] = '戻れる操作履歴がありません。'
            return unchanged
        prior = history.pop()
        return prior['start'], prior['end'], prior['level'], history, '前の期間・粒度へ戻りました。', None, None, *([no_update] * 5)
    if trigger in ('bike-dates', 'bike-level'):
        # 手動で期間や粒度を変えた後、古いズーム範囲を適用しない。
        return no_update, no_update, no_update, [], '期間・粒度を変更しました。', None, None, *([no_update] * 5)
    try:
        if trigger == 'bike-series' and click:
            target = drill_period(click['points'][0]['x'], level, start, end)
            if not target:
                return unchanged
            left, right, next_level = target
        elif trigger == 'bike-apply':
            zoom = zoom or {}
            selected = zoom.get('xaxis.range')
            if not selected and 'xaxis.range[0]' in zoom:
                selected = [zoom['xaxis.range[0]'], zoom['xaxis.range[1]']]
            if not selected or zoom.get('xaxis.autorange'):
                unchanged[4] = '先に主グラフをズームしてください。'
                return unchanged
            left, right = sorted(pd.Timestamp(date).normalize() for date in selected)
            old_left, old_right = bounds(start, end)
            left, right = max(old_left, left), min(old_right, right)
            if right < left:
                raise ValueError('表示範囲が現在の期間と重なりません。')
            left, right, next_level = left.strftime('%Y-%m-%d'), right.strftime('%Y-%m-%d'), level
        else:
            return unchanged
    except (ValueError, KeyError, IndexError, TypeError):
        unchanged[4] = '期間を読み取れませんでした。グラフを選択し直してください。'
        return unchanged
    history.append({'start': start, 'end': end, 'level': level})
    return left, right, next_level, history, f'{left}〜{right} / {LEVELS[next_level]}。境界を含む日単位で全体に適用。', None, None, *([no_update] * 5)


def figure(title):
    result = go.Figure()
    result.update_layout(title=title, template='plotly_white', height=390, margin={'l': 55, 'r': 20, 't': 60, 'b': 65}, legend={'orientation': 'h'})
    return result


# 2. すべての表示とCSVが同じ抽出関数を使う。
def selected_rows(source, start, end, weather, working, level, frames=None):
    return filter_rows('hour' if level == 'H' else source, start, end, weather, working, frames=frames)


def _render(source, start, end, weather, working, level, metric, statistic, frames):
    charts = [figure(title) for title in ['選択期間の推移', '前年同月日との比較（日別）', '日別値と7日移動平均']]
    try:
        frame = selected_rows(source, start, end, weather, working, level, frames=frames)
        values = aggregate(frame, start, end, level, metric, statistic)
    except (ValueError, TypeError):
        for chart in charts:
            chart.add_annotation(text='有効な開始日・終了日を指定してください。', x=.5, y=.5, xref='paper', yref='paper', showarrow=False)
        return '期間の指定を確認してください。', '', *charts, [], []
    effective_source = 'hour' if level == 'H' else source
    unit = '時間' if effective_source == 'hour' else '日'
    mean = f'{frame[metric].mean():,.2f}' if len(frame) else '—'
    kpi = f'抽出 {len(frame):,}行 ｜ {METRICS[metric]} {frame[metric].sum():,}回 ｜ 観測1{unit}平均 {mean}回 ｜ 表示 {LEVELS[level]}'
    charts[0].add_trace(go.Scatter(x=values.index, y=values.value, mode='lines+markers', name=METRICS[metric], connectgaps=False))
    charts[0].update_layout(dragmode='zoom', uirevision=str((start, end, level, source, metric, statistic)), title=f'{LEVELS[level]} / {METRICS[metric]} / {"合計" if statistic == "sum" else "観測行平均"}')
    charts[0].update_xaxes(type='date', rangeslider={'visible': True})
    comparison = previous_year(frame, effective_source, start, end, weather, working, metric, statistic, frames=frames)
    for name in comparison:
        charts[1].add_trace(go.Scatter(x=comparison.index, y=comparison[name], name=name, connectgaps=False))
    if not comparison['前年の同月日'].notna().any():
        charts[1].add_annotation(text='対応する前年データがありません。', x=.5, y=.9, xref='paper', yref='paper', showarrow=False)
    daily = comparison['今回']
    for name, series in [('日別値', daily), ('7日移動平均', daily.rolling(7, min_periods=7).mean())]:
        charts[2].add_trace(go.Scatter(x=daily.index, y=series, name=name, connectgaps=False))
    if daily.notna().any():
        charts[2].add_hline(y=float(daily.mean()), line_dash='dash', annotation_text='抽出日別値の平均')
    if frame.empty:
        for chart in charts:
            chart.add_annotation(text='条件に合うデータがありません。', x=.5, y=.5, xref='paper', yref='paper', showarrow=False)
    for chart in charts:
        chart.update_yaxes(title='貸出回数（平均指定時は観測行平均）')
    missing = quality(start, end, frames=frames)
    message = f'元の時間別CSVで未観測の時間枠：{missing:,}。天候・勤務日フィルターによる除外とは別に計算。欠損を0に置換しません。'
    rows = frame.drop(columns='timestamp').to_dict('records')
    columns = [{'id': name, 'name': name} for name in frame.columns if name != 'timestamp']
    return kpi, message, *charts, rows, columns


# 3. データ版と条件をキャッシュキーに含める。選択状態そのものは共有しない。
def render(source, start, end, weather, working, level, metric, statistic, reset_count=0, data_token=None):
    token = data_token or INITIAL_DATA
    frames = SERVICE.frames(token)
    key = (token['version'], source, start, end, tuple(sorted(weather or [])), working, level, metric, statistic)
    result = SERVICE.cached(key, lambda: _render(source, start, end, weather, working, level, metric, statistic, frames))
    result[2].update_layout(uirevision=str((*key, reset_count)))
    return result


def page_rows(rows, current, size, sort_by):
    frame = pd.DataFrame(rows)
    valid = [item for item in (sort_by or []) if item.get('column_id') in frame.columns]
    if valid:
        frame = frame.sort_values([item['column_id'] for item in valid], ascending=[item.get('direction') != 'desc' for item in valid], kind='stable')
    size = max(1, min(int(size or 15), 100))
    pages = max(1, ceil(len(frame) / size))
    current = max(0, min(int(current or 0), pages - 1))
    return frame.iloc[current * size:(current + 1) * size].to_dict('records'), pages, current


@app.callback(Output('bike-kpi', 'children'), Output('bike-quality', 'children'), Output('bike-series', 'figure'), Output('bike-comparison', 'figure'), Output('bike-moving', 'figure'), Output('bike-table', 'data'), Output('bike-table', 'columns'), Output('bike-table', 'page_count'), Output('bike-table', 'page_current'), Output('bike-processing', 'children'),
              Input('bike-source', 'value'), Input('bike-dates', 'start_date'), Input('bike-dates', 'end_date'), Input('bike-weather', 'value'), Input('bike-working', 'value'), Input('bike-level', 'value'), Input('bike-metric', 'value'), Input('bike-statistic', 'value'), Input('bike-reset', 'n_clicks'), Input('bike-data', 'data'), Input('bike-table', 'page_current'), Input('bike-table', 'page_size'), Input('bike-table', 'sort_by'))
def update_view(source, start, end, weather, working, level, metric, statistic, reset_count, token, current, size, sort_by):
    before = perf_counter()
    try:
        result = list(render(source, start, end, weather, working, level, metric, statistic, reset_count, token))
    except ValueError as error:
        charts = [figure('データの再読込が必要です') for _ in range(3)]
        return str(error), '', *charts, [], [], 1, 0, ''
    if ctx.triggered_id != 'bike-table':
        current = 0
    rows, pages, current = page_rows(result[5], current, size, sort_by)
    result[5] = rows
    info = f"処理 {(perf_counter() - before) * 1000:.1f} ms / キャッシュ hit={SERVICE.hits}, miss={SERVICE.misses} / データ版 {token['version'][:20]} / 表は最大{size}行ずつ転送"
    return *result, pages, current, info


@app.callback(Output('bike-refresh-clock', 'disabled'), Input('bike-auto-refresh', 'value'))
def toggle_refresh(enabled):
    return 'auto' not in (enabled or [])


@app.callback(Output('bike-data', 'data'), Output('bike-refresh-status', 'children'),
              Input('bike-refresh', 'n_clicks'), Input('bike-refresh-clock', 'n_intervals'), Input('bike-backend', 'value'))
def refresh_data(clicks, ticks, backend):
    try:
        token = SERVICE.reload(backend)
    except (ValueError, OSError, pd.errors.ParserError, sqlite3.Error) as error:
        return no_update, f'再読込に失敗しました。前回のデータを保持しています。理由: {error}'
    checked = datetime.fromisoformat(token['checked_at']).astimezone(timezone(timedelta(hours=9)))
    return token, f"{backend.upper()} 読込確認: {checked:%Y-%m-%d %H:%M:%S} JST。内容が同じなら計算結果を再利用します。"


app.clientside_callback("""function(clicks) { if (!clicks) return window.dash_clientside.no_update;
    window.print(); return Date.now(); }""", Output('bike-print-signal', 'data'), Input('bike-print', 'n_clicks'), prevent_initial_call=True)


def export(_, source, start, end, weather, working, level, data_token=None):
    try:
        frame = selected_rows(source, start, end, weather, working, level, frames=SERVICE.frames(data_token or INITIAL_DATA)).drop(columns='timestamp')
    except (ValueError, TypeError):
        return no_update
    return dcc.send_data_frame(frame.to_csv, 'bike_timeseries_details.csv', index=False)


@app.callback(Output('bike-download', 'data'), Output('bike-export-status', 'children'), Input('bike-export', 'n_clicks'), State('bike-source', 'value'), State('bike-dates', 'start_date'), State('bike-dates', 'end_date'), State('bike-weather', 'value'), State('bike-working', 'value'), State('bike-level', 'value'), State('bike-data', 'data'), prevent_initial_call=True)
def download_data(*args):
    result = export(*args)
    if result is no_update:
        return no_update, 'CSVを保存できません。期間を確認し、必要ならデータを再読込してください。'
    return result, '抽出した全明細のCSVを保存しました。'


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8053, debug=False)
