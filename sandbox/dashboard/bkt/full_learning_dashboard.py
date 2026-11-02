"""全領域15回のN2合成学習ログ。既存8056を保持する追加画面、既定8057。"""
import argparse
import csv
from io import StringIO
import json

from dash import Dash, Input, Output, State, ctx, dcc, html, no_update
import plotly.graph_objects as go

from .dashboard_data import build_report, filter_records, load_learning_data, summarize
from .full_mock_dataset import DATABASE
from .learning_dashboard import ASSETS, display_rows, empty_chart, graph_layout, number, percent, table, trend_chart

ALL = '__all__'
DOMAINS = ['言語知識','読解','聴解']
app = Dash(__name__, assets_folder=str(ASSETS), title='JLPT N2 全領域・15回')


def dropdown(identifier, label, options=None, value=ALL):
    return html.Label([label,dcc.Dropdown(id=identifier,options=options or [],value=value,clearable=False)])


app.layout = html.Div(className='learning-shell',children=[
    dcc.Store(id='full-data'),dcc.Store(id='full-report'),dcc.Download(id='full-download'),
    html.Aside(className='learning-sidebar',children=[
        html.Div([html.Strong('JLPT N2'),html.P('全領域の学習記録')],className='learning-brand'),
        html.Nav([html.A('全体と3領域',href='#full-overview'),html.A('大問・細分類',href='#full-categories'),html.A('回次と回答明細',href='#full-details')]),
        html.Div([html.Span('架空学習者1人'),html.Strong('15回 · 1,605回答'),html.P('言語知識54問・読解21問・聴解32問／回。添付ガイド冊子21ページの目安に沿った合成データです。')],className='learning-sidebar-note')]),
    html.Main(className='learning-main',id='full-overview',children=[
        html.Header(className='learning-header',children=[html.Div([
            html.Span('SYNTHETIC LEARNING LOG',className='learning-eyebrow'),html.H1('JLPT N2 全領域ダッシュボード'),
            html.P('全体 → 領域 → 分類 → 大問 → 回答明細。選択条件は集計・グラフ・CSVに共通です。')]),html.Span('架空データ',className='learning-badge')]),
        html.Section(className='learning-filter-card',children=[
            dropdown('full-source','入力元',[{'label':'SQLite（標準）','value':'sqlite'},{'label':'CSV（同内容の控え）','value':'csv'}],'sqlite'),
            dropdown('full-domain','領域'),dropdown('full-group','分類'),dropdown('full-skill','大問・細分類'),
            dropdown('full-session','実施回'),html.Label(['対象期間',dcc.DatePickerRange(id='full-period',display_format='YYYY/MM/DD')]),
            html.Button('すべての条件を解除',id='full-reset',className='learning-reset')]),
        html.P(id='full-status',role='status',className='learning-source-note'),
        html.P(id='full-selection',role='status'),html.Div(id='full-kpis',className='learning-kpis'),
        html.Div(className='learning-charts',children=[
            html.Section(className='learning-card',children=[html.H2('3領域の正答率'),html.P('棒を選ぶと領域を絞り込みます。正答率は正解数÷回答数です。',className='learning-note'),dcc.Graph(id='full-domain-chart',config={'displaylogo':False})]),
            html.Section(className='learning-card',children=[html.H2('15回の推移'),dcc.RadioItems(id='full-metric',options=[{'label':'正答率','value':'accuracy'},{'label':'自己申告理解度','value':'understanding'},{'label':'モデル試算','value':'model'}],value='accuracy',inline=True),dcc.Graph(id='full-trend',config={'displaylogo':False})])]),
        html.Section(id='full-categories',className='learning-card',children=[html.H2('大問・細分類別の結果'),
            html.P('同名の統合理解も領域別に区別します。棒を選ぶと、その大問の回答へ絞り込みます。',className='learning-note'),
            dcc.Graph(id='full-skill-chart',config={'displaylogo':False}),
            html.Button('領域サマリーCSV',id='full-export-domains',className='learning-text-button'),
            html.Button('大問サマリーCSV',id='full-export-skills',className='learning-text-button'),
            table('full-skills',[('Domain','領域'),('Category','分類'),('SkillName','大問・細分類'),('Correct','正解数'),('Answered','回答数'),('AccuracyText','正答率'),('UnderstandingText','自己申告理解度 0–3'),('ModelText','独立モデル試算')],19)]),
        html.Section(className='learning-card',children=[html.H2('実施回ごとの記録'),
            html.Button('履歴CSV',id='full-export-sessions',className='learning-text-button'),
            table('full-sessions',[('Date','実施日'),('SessionNumber','回次'),('Correct','正解数'),('Answered','回答数'),('AccuracyText','正答率'),('UnderstandingText','自己申告理解度'),('ModelText','モデル試算')],15)]),
        html.Section(id='full-details',className='learning-card',children=[html.H2('回答明細'),
            html.Button('回答明細CSV',id='full-export-details',className='learning-text-button'),
            html.Button('モデル仮定JSON',id='full-export-model',className='learning-text-button'),
            table('full-answers',[('SessionNumber','回次'),('QuestionSequence','問題順'),('CategoryLevel1','領域'),('CategoryLevel2','分類'),('SkillName','大問・細分類'),('IsCorrect','正解'),('ConfidenceLevel','自信度 1高–4低'),('UnderstandingLevel','解説後理解度 0–3'),('AssistedAfterLearning','独立モデル試算')],10),
            html.P('CSVは選択条件に合う全回答を保存します。表示中のページだけではありません。',className='learning-note')]),
        html.Footer(className='learning-footer',children=[html.Strong('指標と資料の位置づけ'),
            html.P('正答率・自己申告理解度・独立回答モデル試算は別の指標です。モデルは手動の仮定による未校正の試算で、累積習得率ではありません。自信度は1が最も高く4が最も低い、解説後理解度は0が低く3が高い定義です。'),
            html.P('添付「新しい日本語能力試験ガイドブック」（2009年作成）冊子21ページを参照。小問数は目安で、現行試験の固定配分ではありません。公式尺度得点・合否判定は行いません。問題文・音声・教材そのものは含みません。')])])])


def load_full(source='sqlite'):
    return load_learning_data(source,database=DATABASE,csv_folder=DATABASE.parent/'csv')


@app.callback(Output('full-data','data'),Output('full-domain','options'),Output('full-domain','value'),
              Output('full-session','options'),Output('full-session','value'),Output('full-period','start_date'),
              Output('full-period','end_date'),Output('full-status','children'),Input('full-source','value'))
def load_source(source):
    try:
        records = load_full(source)
        sessions = {r['SessionID']:r['SessionNumber'] for r in records}
        dates = [r['SessionDate'] for r in records]
        return (records,[{'label':'全領域','value':ALL}]+[{'label':d,'value':d} for d in DOMAINS],ALL,
                [{'label':'全15回','value':ALL}]+[{'label':f'第{n}回','value':sid} for sid,n in sessions.items()],ALL,
                min(dates),max(dates),f'{source.upper()} 読込済み · {len(records):,}回答 · 読み取り専用')
    except (OSError,ValueError,KeyError) as error:
        return [],[],ALL,[],ALL,None,None,f'読み込めません: {error}'


@app.callback(Output('full-group','options'),Output('full-group','value'),Input('full-data','data'),Input('full-domain','value'))
def groups(records,domain):
    selected = filter_records(records or [],domain=domain or ALL)
    names = list(dict.fromkeys(r['CategoryLevel2'] for r in selected))
    return [{'label':'すべての分類','value':ALL}]+[{'label':n,'value':n} for n in names],ALL


@app.callback(Output('full-skill','options'),Output('full-skill','value'),Input('full-data','data'),Input('full-domain','value'),Input('full-group','value'))
def skills(records,domain,group):
    selected = filter_records(records or [],domain=domain or ALL,group=group or ALL)
    choices = {r['SkillID']:f"{r['CategoryLevel1']} · {r['SkillName']}" for r in selected}
    return [{'label':'すべての大問','value':ALL}]+[{'label':n,'value':sid} for sid,n in choices.items()],ALL


def full_report(records):
    report = build_report(records)
    domains = [{'Domain':d,**summarize([r for r in records if r['CategoryLevel1']==d])} for d in DOMAINS]
    names = {r['SkillID']:r['CategoryLevel1'] for r in records}
    order = {key:index for index,key in enumerate(names)}
    report['skills'] = sorted([{**s,'Domain':names[s['SkillID']]} for s in report['skills']],
                             key=lambda s:order[s['SkillID']])
    report['domains'] = domains
    return report


def bars(rows, domain=False):
    if not rows:
        return empty_chart('対象の回答がありません')
    labels = [r['Domain'] if domain else f"{r['Domain']} · {r['SkillName']}" for r in rows]
    identifiers = [r['Domain'] if domain else r['SkillID'] for r in rows]
    fig = go.Figure(go.Bar(y=labels,x=[r['Accuracy'] for r in rows],orientation='h',
        customdata=identifiers,marker_color='#2864e9',hovertemplate='%{y}<br>正答率 %{x:.1%}<extra></extra>'))
    graph_layout(fig,max(300,len(rows)*34+65))
    fig.update_xaxes(range=[0,1.05],tickformat='.0%')
    fig.update_yaxes(autorange='reversed',automargin=True)
    return fig


@app.callback(Output('full-kpis','children'),Output('full-domain-chart','figure'),Output('full-skill-chart','figure'),
              Output('full-trend','figure'),Output('full-skills','data'),Output('full-sessions','data'),
              Output('full-answers','data'),Output('full-report','data'),Output('full-selection','children'),
              Input('full-data','data'),Input('full-domain','value'),Input('full-group','value'),Input('full-skill','value'),
              Input('full-session','value'),Input('full-period','start_date'),Input('full-period','end_date'),Input('full-metric','value'))
def render(records,domain,group,skill,session,start,end,metric):
    try:
        records = records or []
        selected = filter_records(records,domain=domain or ALL,group=group or ALL,skill=skill or ALL,
                                  session=session or ALL,start=start,end=end)
        report = full_report(selected)
        overall = report['overall']
        cards = [('正答率',percent(overall['Accuracy']),f"正解 {overall['Correct']} / {overall['Answered']}回答"),
                 ('解説後理解度',number(overall['Understanding'],' / 3'),'自己申告の平均'),
                 ('モデル試算',percent(overall['ModelMean']),'独立回答・手動仮定'),
                 ('実施回数',str(overall['Sessions'])+'回',f"{len(report['skills'])}大問・{overall['InputCount']}回答"),
                 ('自信ありの誤答',str(overall['ConfidentWrong'])+'件','自信度1・2で不正解')]
        kpis = [html.Div([html.Span(label),html.Strong(value),html.Small(note)],className='learning-kpi blue') for label,value,note in cards]
        report['filters'] = dict(domain=domain,group=group,skill=skill,session=session,start=start,end=end)
        domain_label = domain if domain!=ALL else '全領域'
        label = f"{domain_label} · {overall['InputCount']:,}回答 · {overall['Sessions']}回"
        if not selected:
            label += ' · 条件に合う回答がありません'
        return (kpis,bars(report['domains'],True),bars(report['skills']),trend_chart(report,metric),
                display_rows(report['skills']),display_rows(report['sessions']),report['details'],report,label)
    except (ValueError,TypeError,KeyError) as error:
        chart = empty_chart('条件を確認してください')
        return [],chart,chart,chart,[],[],[],None,f'集計できません: {error}'


@app.callback(Output('full-domain','value',allow_duplicate=True),Input('full-domain-chart','clickData'),prevent_initial_call=True)
def select_domain(click):
    try:
        value = click['points'][0]['customdata']
        return value if value in DOMAINS else no_update
    except (KeyError,TypeError,IndexError):
        return no_update


@app.callback(Output('full-skill','value',allow_duplicate=True),Input('full-skill-chart','clickData'),prevent_initial_call=True)
def select_skill(click):
    try:
        return click['points'][0]['customdata']
    except (KeyError,TypeError,IndexError):
        return no_update


@app.callback(Output('full-domain','value',allow_duplicate=True),Output('full-group','value',allow_duplicate=True),
              Output('full-skill','value',allow_duplicate=True),Output('full-session','value',allow_duplicate=True),
              Output('full-period','start_date',allow_duplicate=True),Output('full-period','end_date',allow_duplicate=True),
              Input('full-reset','n_clicks'),State('full-data','data'),prevent_initial_call=True)
def reset(_,records):
    dates = [r['SessionDate'] for r in records or []]
    return ALL,ALL,ALL,ALL,min(dates) if dates else None,max(dates) if dates else None


@app.callback(Output('full-download','data'),
              Input('full-export-domains','n_clicks'),Input('full-export-skills','n_clicks'),
              Input('full-export-sessions','n_clicks'),Input('full-export-details','n_clicks'),Input('full-export-model','n_clicks'),
              State('full-report','data'),prevent_initial_call=True)
def download(domains,skills,sessions,details,model,report):
    if not report:
        return no_update
    key = ctx.triggered_id.removeprefix('full-export-')
    if key=='model':
        metadata = {k:report[k] for k in ('parameters','assumptions','model_version','scope','filters')}
        return dcc.send_string(json.dumps(metadata,ensure_ascii=False,indent=2),'n2_full_model_assumptions.json')
    rows = report[key]
    if not rows:
        return no_update
    stream = StringIO(newline='')
    writer = csv.DictWriter(stream,fieldnames=list(rows[0]))
    writer.writeheader(); writer.writerows(rows)
    return dcc.send_string('\ufeff'+stream.getvalue(),f'n2_full_{key}.csv')


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8057)
    args = parser.parse_args()
    app.run(host='127.0.0.1',port=args.port,debug=False)
