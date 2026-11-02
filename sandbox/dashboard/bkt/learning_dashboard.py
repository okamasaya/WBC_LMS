"""N2学習サマリー。SQLiteを主入力にした確認画面。既定ポート8056。"""
import argparse
import csv
from io import StringIO
import json
from pathlib import Path

from dash import Dash, Input, Output, State, ctx, dcc, html, dash_table, no_update
import plotly.graph_objects as go

from .dashboard_data import build_report, filter_records, load_learning_data, summarize

ASSETS = Path(__file__).resolve().parent / 'learning_assets'
app = Dash(__name__, assets_folder=str(ASSETS), title='JLPT N2 学習ダッシュボード')


def graph_layout(figure, height=340):
    figure.update_layout(template='plotly_white', height=height,
                         font={'family':'Arial, "Yu Gothic", "Meiryo", sans-serif','color':'#344258'},
                         paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                         margin={'l':35,'r':18,'t':15,'b':40}, legend={'orientation':'h','y':1.15},
                         hoverlabel={'font_size':13})
    figure.update_xaxes(gridcolor='#edf1f7', zeroline=False)
    figure.update_yaxes(gridcolor='#edf1f7', zeroline=False)
    return figure


def empty_chart(message):
    figure = graph_layout(go.Figure())
    figure.add_annotation(text=message, x=.5,y=.5,xref='paper',yref='paper',showarrow=False)
    figure.update_xaxes(visible=False); figure.update_yaxes(visible=False)
    return figure


def table(identifier, columns, size=8):
    return dash_table.DataTable(id=identifier, columns=[{'id':key,'name':label} for key,label in columns],
                               data=[], page_size=size, sort_action='native',
                               style_table={'overflowX':'auto'}, style_cell={'fontFamily':'inherit','fontSize':13,'padding':'11px 10px','textAlign':'left','minWidth':'85px','maxWidth':'230px','whiteSpace':'normal'},
                               style_header={'backgroundColor':'#f7f9fd','fontWeight':'600','borderBottom':'1px solid #e7edf6'},
                               style_data={'borderBottom':'1px solid #edf1f7'}, style_cell_conditional=[{'if':{'column_id':'SkillName'},'minWidth':'145px'}])


app.layout = html.Div(className='learning-shell', children=[
    dcc.Store(id='learning-data'), dcc.Store(id='learning-report'), dcc.Download(id='learning-download'),
    html.Aside(className='learning-sidebar', children=[
        html.A([html.Span('▰',className='learning-brand-icon'),html.Div([html.Strong('JLPT N2'),html.Small('Learning Dashboard')])],href='#overview',className='learning-brand'),
        html.P('言語知識 · 文字 / 語彙 / 文法',className='learning-sidebar-caption'),
        html.Nav([html.A('◫  ダッシュボード',href='#overview',className='active'),html.A('▥  大問題別の結果',href='#categories'),html.A('◷  実施履歴',href='#history'),html.A('≡  回答明細',href='#details')]),
        html.Div([html.Span('動作確認データ'),html.Strong('5回 · 150回答'),html.P('架空学習者の合成ログです。実際の成績ではありません。')],className='learning-sidebar-note'),
        html.Small('JLPT · ALP–BKT prototype',className='learning-sidebar-footer')]),
    html.Main(className='learning-main',id='overview',children=[
        html.Header(className='learning-header',children=[html.Div([html.Span('LEARNING OVERVIEW',className='learning-eyebrow'),html.H1('JLPT N2 学習ダッシュボード'),html.P('言語知識（文字・語彙・文法）の正解率と、解説後の理解度を振り返ります。')]),html.Div([html.Span('合成データ',className='learning-badge'),html.Span(id='learning-learner-name')],className='learning-person')]),
        html.Section(className='learning-filter-card',children=[
            html.Label(['データ入力',dcc.Dropdown(id='learning-source',options=[{'label':'SQLite（標準）','value':'sqlite'},{'label':'CSV（同内容の控え）','value':'csv'}],value='sqlite',clearable=False)]),
            html.Label(['学習者',dcc.Dropdown(id='learning-student',options=[],value='__all__',clearable=False)]),
            html.Label(['対象期間',dcc.DatePickerRange(id='learning-period',display_format='YYYY/MM/DD',first_day_of_week=1)]),
            html.Label(['大問題',dcc.Dropdown(id='learning-skill',options=[],value='__all__',clearable=False)]),
            html.Button('大問題の選択を解除',id='learning-reset',className='learning-reset')]),
        html.P(id='learning-load-status',role='status',className='learning-source-note'),
        html.Div(id='learning-kpis',className='learning-kpis'),
        html.Div(className='learning-charts',children=[
            html.Section(id='categories',className='learning-card',children=[html.Div([html.H2('大問題別の正解率'),html.Span('直近3回',className='learning-tag')],className='learning-card-heading'),html.P('棒を選ぶと、大問題の条件が全体に反映されます。',className='learning-note'),dcc.Graph(id='learning-category-chart',config={'displaylogo':False})]),
            html.Section(className='learning-card',children=[html.Div([html.H2('実施回ごとの推移'),dcc.RadioItems(id='learning-trend-metric',options=[{'label':'自己申告の理解度','value':'understanding'},{'label':'モデル試算','value':'model'},{'label':'正解率','value':'accuracy'}],value='understanding',inline=True)],className='learning-trend-heading'),dcc.Graph(id='learning-trend-chart',config={'displaylogo':False}),html.P(id='learning-trend-note',className='learning-note')])]),
        html.Div(className='learning-bottom-grid',children=[
            html.Section(className='learning-card',children=[html.Div([html.H2('今回のサマリー'),html.Span('集計による振り返り',className='learning-tag')],className='learning-card-heading'),html.Div(id='learning-summary'),html.Div(id='learning-quality',className='learning-quality')]),
            html.Section(id='history',className='learning-card',children=[html.Div([html.H2('実施履歴'),html.Button('履歴CSV',id='learning-export-history',className='learning-text-button')],className='learning-card-heading'),table('learning-history',[('Date','実施日'),('SessionNumber','回次'),('Answered','回答数'),('AccuracyText','正解率'),('UnderstandingText','理解度 0–3'),('ModelText','モデル試算平均'),('SecondsText','平均回答秒')],5)])]),
        html.Section(className='learning-card',children=[html.Div([html.H2('大問題別の数値'),html.Button('大問題サマリーCSV',id='learning-export-skills',className='learning-text-button')],className='learning-card-heading'),table('learning-skill-table',[('SkillName','大問題'),('Category','領域'),('Answered','回答数'),('AccuracyText','正解率'),('UnderstandingText','理解度 0–3'),('ModelText','モデル試算平均'),('ConfidentWrong','自信ありの誤答数')],10),html.P('「自信ありの誤答」は自信度1・2で不正解だった回答です。回答数と併せて確認してください。',className='learning-note')]),
        html.Section(id='details',className='learning-card',children=[html.Div([html.H2('回答明細と出力'),html.Div([html.Button('回答明細CSV',id='learning-export-details',className='learning-text-button'),html.Button('モデルの仮定JSON',id='learning-export-model',className='learning-text-button')])],className='learning-card-heading'),
            html.Details([html.Summary('選択条件に合う回答を表示'),table('learning-details',[('SessionNumber','回次'),('QuestionSequence','問題順'),('SkillName','大問題'),('IsCorrect','正解'),('ConfidenceLevel','自信度 1–4'),('UnderstandingLevel','理解度 0–3'),('AssistedAfterLearning','モデル試算')],10)]),
            html.P('CSVは表示ページだけでなく、選択条件に合う全行を保存します。理解度0は未入力と区別します。',className='learning-note')]),
        html.Footer([html.Strong('指標の読み方'),html.P('正解率は回答済みの有効な正誤から集計。理解度は解説後の自己申告0〜3の平均です。モデル試算は手動の仮定による独立回答の推定値の平均で、累積した習得率や検証済みの理解度ではありません。'),html.P('推定信頼度・学習の安定性・AI推薦は、定義と検証を決める次の仕様として保留しています。')],className='learning-footer')])])


@app.callback(Output('learning-data','data'),Output('learning-student','options'),Output('learning-student','value'),Output('learning-skill','options'),Output('learning-skill','value'),Output('learning-period','start_date'),Output('learning-period','end_date'),Output('learning-load-status','children'),Input('learning-source','value'))
def load_source(source):
    try:
        records = load_learning_data(source)
        students = {r['StudentID']:r['StudentName'] for r in records}
        skills = {r['SkillID']:r['SkillName'] for r in records}
        student_options = [{'label':name,'value':key} for key,name in sorted(students.items())]
        skill_options = [{'label':'すべての大問題','value':'__all__'}] + [{'label':name,'value':key} for key,name in sorted(skills.items())]
        dates = [r['SessionDate'] for r in records]
        label = 'SQLite（標準）' if source=='sqlite' else 'CSV（同内容の控え）'
        return records,student_options,student_options[0]['value'],skill_options,'__all__',min(dates),max(dates),f'{label}を読込済み · {len(records)}回答 · データは読み取り専用です'
    except (ValueError,OSError,KeyError) as error:
        return [],[],None,[],None,None,None,f'読み込めません: {error}'


def percent(value):
    return '—' if value is None else f'{value:.1%}'


def number(value, suffix=''):
    return '—' if value is None else f'{value:.2f}{suffix}'


def display_rows(rows):
    return [{**r,'AccuracyText':percent(r['Accuracy']),'UnderstandingText':number(r['Understanding']),
             'ModelText':percent(r['ModelMean']),'SecondsText':number(r['AverageSeconds'])} for r in rows]


def category_chart(records, report):
    if not records:
        return empty_chart('対象期間・大問題に合う回答がありません')
    figure = go.Figure()
    names = {r['SkillID']:r['SkillName'] for r in report['skills']}
    recent = report['sessions'][-3:]
    colors = ['#d6e2f7','#88acf6','#2864e9'][-len(recent):]
    for index,session in enumerate(recent):
        groups = []
        for key in names:
            selected = [r for r in records if r['SessionID']==session['SessionID'] and r['SkillID']==key]
            values = summarize(selected) if selected else None
            groups.append(values['Accuracy'] if values else None)
        figure.add_trace(go.Bar(y=list(names.values()),x=groups,name=f"第{session['SessionNumber']}回",orientation='h',marker_color=colors[index],customdata=[[key] for key in names],hovertemplate='%{y}<br>正解率 %{x:.1%}<extra>%{fullData.name}</extra>'))
    graph_layout(figure,390)
    figure.update_layout(barmode='group',margin={'l':15,'r':22,'t':35,'b':40})
    figure.update_xaxes(range=[0,1.05],tickformat='.0%',title='回答済みの正解率')
    figure.update_yaxes(autorange='reversed',automargin=True)
    return figure


def trend_chart(report, metric):
    sessions = report['sessions']
    if not sessions:
        return empty_chart('対象期間・大問題に合う回答がありません')
    key,title,limit,fmt = {'understanding':('Understanding','解説後理解度（自己申告平均）',[0,3],'.1f'),
                           'model':('ModelMean','モデル試算の平均',[0,1],'.0%'),
                           'accuracy':('Accuracy','正解率',[0,1],'.0%')}[metric]
    figure = go.Figure(go.Scatter(x=[s['Date'] for s in sessions],y=[s[key] for s in sessions],mode='lines+markers',line={'color':'#2864e9','width':3},marker={'size':8},name=title,customdata=[[s['SessionNumber'],s['Answered']] for s in sessions],hovertemplate=f'%{{x}}<br>{title} %{{y:{fmt}}}<br>第%{{customdata[0]}}回 · %{{customdata[1]}}回答<extra></extra>'))
    graph_layout(figure,345)
    figure.update_yaxes(range=limit,tickformat=fmt,title=title)
    figure.update_xaxes(title='実施日',tickformat='%m/%d',dtick=86400000*3)
    return figure


@app.callback(Output('learning-kpis','children'),Output('learning-category-chart','figure'),Output('learning-trend-chart','figure'),Output('learning-trend-note','children'),Output('learning-summary','children'),Output('learning-quality','children'),Output('learning-history','data'),Output('learning-skill-table','data'),Output('learning-details','data'),Output('learning-report','data'),Output('learning-learner-name','children'),
              Input('learning-data','data'),Input('learning-student','value'),Input('learning-skill','value'),Input('learning-period','start_date'),Input('learning-period','end_date'),Input('learning-trend-metric','value'))
def render(records,student,skill,start,end,metric):
    try:
        selected = filter_records(records or [],student or '__all__',skill or '__all__',start,end)
        report = build_report(selected)
        metric = metric if metric in ('understanding','model','accuracy') else 'understanding'
        overall = report['overall']
        cards = [('正解率',percent(overall['Accuracy']),f"{overall['Correct']} / {overall['Answered']} 回答",'blue'),
                 ('解説後の理解度',number(overall['Understanding'],' / 3'),f"自己申告 · 有効 {overall['UnderstandingCount']}件",'violet'),
                 ('モデル試算の平均',percent(overall['ModelMean']),'独立回答・手動の仮定','orange'),
                 ('平均回答時間',number(overall['AverageSeconds'],'秒'),'回答操作の記録時間','green'),
                 ('実施回数',f"{overall['Sessions']}回",f"対象 {len(report['skills'])}大問題 · {overall['InputCount']}問",'blue')]
        kpis = [html.Div([html.Span(label),html.Strong(value),html.Small(note)],className=f'learning-kpi {color}') for label,value,note,color in cards]
        sessions = report['sessions']
        summary = []
        if sessions:
            latest = sessions[-1]
            summary.append(html.P([html.Strong('最新回'),f"：{latest['Date']} · {latest['Answered']}回答 · 正解率 {percent(latest['Accuracy'])} · 理解度 {number(latest['Understanding'])} / 3"]))
            if len(sessions)>=2 and latest['Accuracy'] is not None and sessions[-2]['Accuracy'] is not None:
                delta = 100*(latest['Accuracy']-sessions[-2]['Accuracy'])
                summary.append(html.P(f'前回との正解率差：{delta:+.1f}ポイント（選択中の対象内で比較）'))
            ranked = sorted((r for r in report['skills'] if r['Accuracy'] is not None),key=lambda r:(r['Accuracy'],r['SkillID']))
            if ranked:
                weak = ranked[0]
                summary.append(html.P([html.Strong('確認候補'),f"：{weak['SkillName']} · 正解率 {percent(weak['Accuracy'])}（{weak['Answered']}回答）"],className='learning-review-note'))
            summary.append(html.P(f"自信度1・2で不正解だった回答は {overall['ConfidentWrong']}件です。明細で振り返れます。"))
        else:
            summary = [html.P('対象条件に合うデータがありません。期間・大問題を変更してください。')]
        quality = f"未回答 {overall['Unanswered']}件 ／ 理解度の未入力・不正 {overall['UnderstandingUnavailable']}件 ／ 自信度の未入力・不正 {overall['ConfidenceUnavailable']}件 ／ 推定除外 {overall['ModelExcluded']}件"
        notes = {'understanding':'自己申告0〜3の平均です。未入力を分母に含めず、0は有効値として集計します。',
                 'model':'各回の独立回答モデル試算の平均です。履歴による累積学習・信頼区間を表す線ではありません。',
                 'accuracy':'回答済みの有効な正誤を分母にした実測の正解率です。'}
        stored = {**report,'filters':{'student':student,'skill':skill,'start':start,'end':end}}
        name = selected[0]['StudentName'] if selected else '対象データなし'
        return kpis,category_chart(selected,report),trend_chart(report,metric),notes[metric],summary,quality,display_rows(sessions),display_rows(report['skills']),report['details'],stored,name
    except (ValueError,TypeError,KeyError) as error:
        chart = empty_chart('条件を確認してください')
        return [],chart,chart,'',f'集計できません: {error}','',[],[],[],None,'対象データなし'


@app.callback(Output('learning-skill','value',allow_duplicate=True),Input('learning-category-chart','clickData'),Input('learning-reset','n_clicks'),prevent_initial_call=True)
def select_skill(click, reset):
    if ctx.triggered_id=='learning-reset':
        return '__all__'
    try:
        return click['points'][0]['customdata'][0]
    except (KeyError,TypeError,IndexError):
        return no_update


@app.callback(Output('learning-download','data'),Input('learning-export-skills','n_clicks'),Input('learning-export-history','n_clicks'),Input('learning-export-details','n_clicks'),Input('learning-export-model','n_clicks'),State('learning-report','data'),prevent_initial_call=True)
def download(skills, history, details, model, report):
    if not report:
        return no_update
    if ctx.triggered_id=='learning-export-model':
        metadata = {key:report[key] for key in ('parameters','assumptions','model_version','scope','filters')}
        return dcc.send_string(json.dumps(metadata,ensure_ascii=False,indent=2),'learning_model_assumptions.json')
    key = {'learning-export-skills':'skills','learning-export-history':'sessions','learning-export-details':'details'}[ctx.triggered_id]
    rows = report[key]
    if not rows:
        return no_update
    stream = StringIO(newline='')
    fields = list(dict.fromkeys(key for row in rows for key in row))
    writer = csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    return dcc.send_string('\ufeff'+stream.getvalue(),f'learning_{key}.csv')


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8056)
    args = parser.parse_args()
    app.run(host='127.0.0.1',port=args.port,debug=False)
