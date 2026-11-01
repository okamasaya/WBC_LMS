"""正誤中心・補助2項目の独立回答モデル。python -m sandbox.dashboard.bkt.flat_app"""
import csv
from io import StringIO
import json
from pathlib import Path
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, ctx, dcc, html, dash_table, no_update
from .model import BKTParameters
from .assisted_model import (AuxiliaryAssumptions, CONFIDENCE_LABELS, UNDERSTANDING_LABELS,
                             combinations, estimate_flat, update_flat)
from .demo_data import sample_records

ROOT = Path(__file__).resolve().parent
app = Dash(__name__, assets_folder=str(ROOT / 'assets'), title='BKT・3項目フラット試作')


def picker(identifier, label, options, value, clearable=False):
    return html.Label([label, dcc.Dropdown(id=identifier, options=[{'label': text, 'value': key} for key, text in options.items()], value=value, clearable=clearable)])


app.layout = html.Main(className='alp-dashboard flat-dashboard', children=[
    dcc.Store(id='flat-analysis'), dcc.Download(id='flat-download'),
    html.Header([html.Span('実験モデル・未校正', className='alp-badge'), html.H1('正誤を中心にした3項目のフラット試作'),
        html.P('各回答を同じ初期値から評価します。学習者・スキルの履歴はまだつなぎません。実測の理解度や、検証済みの予測精度を示すものではありません。')]),
    html.Section(className='alp-card', children=[
        html.H2('1. 1回答の条件を変える'),
        html.Div(className='alp-filter-grid', children=[
            picker('flat-correct','問題の正誤',{0:'不正解',1:'正解'},1),
            picker('flat-confidence','回答時の自信度（空欄は補助なし）',CONFIDENCE_LABELS,2,True),
            picker('flat-understanding','解説後の理解度（空欄は補助なし）',UNDERSTANDING_LABELS,3,True)]),
        html.P('自信度は1が高く4が低い、理解度は0が低く3が高い。未入力は0と区別します。',className='alp-note'),
        html.Details([html.Summary('仮パラメータと補助項目の扱い'),
            html.Div(className='alp-parameter-grid', children=[html.Label([label,dcc.Input(id=identifier,type='number',min=0,max=1,step=.01,value=value,debounce=True)]) for identifier,label,value in [('flat-l0','初期習得 P(L0)',.2),('flat-t','学習遷移 P(T)',.1),('flat-g','当て推量 P(G)',.25),('flat-s','うっかり誤答 P(S)',.1)]]),
            html.P('自信度1〜4の観測重み＝1.5, 1.0, 0.75, 0.5。理解度0〜3の学習遷移倍率＝0.25, 0.5, 0.75, 1.0。未入力は倍率1。すべて手動の仮定です。'),
            html.P('正誤で事後更新 → 解説後の理解度で学習遷移を調整。解説後の理解度を、その問題の正答予測へさかのぼって使用しません。')]),
        html.P(id='flat-status',role='status'),
        html.Div(id='flat-single',className='flat-kpis'),
        dcc.Graph(id='flat-stages',config={'displaylogo':False}),
        html.P('標準BKTとの段階比較です。横軸はモデル内の処理順で、実測時刻・連続した学習履歴ではありません。',className='alp-note')]),
    html.Section(className='alp-card',children=[html.H2('2. 全32通りの設計確認（実測データではありません）'),
        html.P('2種類の正誤×自信度4段階×理解度4段階。色は補助ありモデルの学習遷移後の仮の習得確率です。セルをクリックすると上の1回答へ反映します。'),
        html.Div(className='flat-heatmaps',children=[dcc.Graph(id='flat-wrong'),dcc.Graph(id='flat-right')])]),
    html.Section(className='alp-card',children=[html.H2('3. 架空データの明細と出力'),
        picker('flat-dataset','データの種類',{'patterns':'全32パターン（合成データ）','demo':'既存の架空ログ24回答（各回答は独立に評価）'},'patterns'),
        picker('flat-filter','正誤の絞り込み',{'all':'すべて','correct':'正解','wrong':'不正解'},'all'),
        html.P(id='flat-summary',role='status'),
        dash_table.DataTable(id='flat-table',page_size=12,sort_action='native',style_table={'overflowX':'auto'},style_cell={'fontFamily':'inherit','minWidth':'100px','padding':'8px'}),
        html.Div(className='alp-actions',children=[html.Button('表示対象をCSV保存',id='flat-export',disabled=True),html.Button('モデルの仮定をJSON保存',id='flat-export-model',disabled=True)]),
        html.P('CSVは表示ページだけでなく、選択した正誤条件に合う全行を保存します。実ファイルの取込とDjango接続は次段階です。',className='alp-note')])])


def blank(text):
    chart=go.Figure();chart.add_annotation(text=text,x=.5,y=.5,xref='paper',yref='paper',showarrow=False)
    chart.update_layout(template='plotly_white',height=360)
    return chart


def heatmap(records,correct):
    selected={(r['ConfidenceLevel'],r['UnderstandingLevel']):r for r in records if r['IsCorrect'] is correct}
    z=[[selected[(c,u)]['AssistedAfterLearning'] for c in range(1,5)] for u in range(4)]
    chart=go.Figure(go.Heatmap(x=[1,2,3,4],y=[0,1,2,3],z=z,zmin=0,zmax=1,colorscale='Viridis',texttemplate='%{z:.3f}',hovertemplate='自信度 %{x}<br>解説理解度 %{y}<br>仮の習得確率 %{z:.3f}<extra></extra>'))
    chart.update_layout(title='正解' if correct else '不正解',template='plotly_white',height=360,margin={'l':65,'r':35,'t':55,'b':70})
    chart.update_xaxes(title='自信度（1=高、4=低）',dtick=1)
    chart.update_yaxes(title='理解度（0=低、3=高）',dtick=1)
    return chart


@app.callback(Output('flat-status','children'),Output('flat-single','children'),Output('flat-stages','figure'),Output('flat-wrong','figure'),Output('flat-right','figure'),Output('flat-summary','children'),Output('flat-table','data'),Output('flat-table','columns'),Output('flat-analysis','data'),Output('flat-export','disabled'),Output('flat-export-model','disabled'),
              Input('flat-correct','value'),Input('flat-confidence','value'),Input('flat-understanding','value'),Input('flat-l0','value'),Input('flat-t','value'),Input('flat-g','value'),Input('flat-s','value'),Input('flat-dataset','value'),Input('flat-filter','value'))
def render(correct,confidence,understanding,p_l0,p_t,p_g,p_s,dataset,selection):
    try:
        if correct not in (0,1):
            raise ValueError('正誤を選択してください。')
        parameters=BKTParameters(p_l0,p_t,p_g,p_s)
        single=update_flat(correct==1,confidence,understanding,parameters)
        patterns=estimate_flat(combinations(),parameters)
        result=estimate_flat(sample_records() if dataset=='demo' else combinations(),parameters)
    except (ValueError,TypeError) as error:
        chart=blank('入力パラメータを確認してください')
        return str(error),[],chart,chart,chart,'推定結果をクリアしました。',[],[],None,True,True
    stages=go.Figure()
    for name,values in [('正誤のみ・標準BKT',[single['PBefore'],single['ClassicPosterior'],single['ClassicAfterLearning']]),('自信度・理解度の補助あり',[single['PBefore'],single['AssistedPosterior'],single['AssistedAfterLearning']])]:
        stages.add_trace(go.Scatter(x=['初期','正誤観測後','学習遷移後'],y=values,mode='lines+markers',name=name))
    stages.update_layout(template='plotly_white',height=360,yaxis={'range':[0,1],'title':'仮定したモデル内の確率'},legend={'orientation':'h'},margin={'l':55,'r':20,'t':30,'b':70})
    metrics=[('標準BKT・正誤更新後',single['ClassicPosterior']),('補助あり・正誤更新後',single['AssistedPosterior']),('補助あり・学習遷移後',single['AssistedAfterLearning']),('同一スキルを仮定した次問正答確率',single['NextCorrect'])]
    kpis=[html.Div([html.Span(label),html.Strong(f'{value:.4f}')],className='alp-kpi') for label,value in metrics]
    rows=[r for r in result['records'] if selection=='all' or r['IsCorrect']==(selection=='correct')]
    columns=[{'id':key,'name':label} for key,label in [('Row','入力行'),('ResultID','回答ID'),('IsCorrect','正誤'),('ConfidenceLevel','自信度（1=高）'),('UnderstandingLevel','解説理解度（3=高）'),('ObservationWeight','自信度の重み'),('EffectiveLearning','有効P(T)'),('ClassicPosterior','標準・観測後'),('AssistedPosterior','補助・観測後'),('AssistedAfterLearning','補助・遷移後'),('NextCorrect','同一スキルを仮定した次問正答確率')]]
    status=f"各回答はP(L0)={p_l0}から独立評価。自信度の重み={single['ObservationWeight']}、解説後の有効P(T)={single['EffectiveLearning']:.4f}。未校正の仮説モデルです。"
    source='既存の架空ログ' if dataset=='demo' else '設計用の合成32パターン'
    summary=f"{source}：評価可能 {len(result['records'])}行 ／ 表示対象 {len(rows)}行 ／ 除外 {len(result['excluded'])}行。履歴による累積更新はしていません。"
    stored={**result,'records':rows,'source':source,'scope':'independent_answers_same_prior'}
    return status,kpis,stages,heatmap(patterns['records'],False),heatmap(patterns['records'],True),summary,rows,columns,stored,not bool(rows),False


@app.callback(Output('flat-correct','value'),Output('flat-confidence','value'),Output('flat-understanding','value'),Input('flat-wrong','clickData'),Input('flat-right','clickData'),prevent_initial_call=True)
def select_pattern(wrong,right):
    payload=right if ctx.triggered_id=='flat-right' else wrong
    if not payload or not payload.get('points'):
        return no_update,no_update,no_update
    point=payload['points'][0]
    return int(ctx.triggered_id=='flat-right'),int(point['x']),int(point['y'])


@app.callback(Output('flat-download','data'),Input('flat-export','n_clicks'),Input('flat-export-model','n_clicks'),State('flat-analysis','data'),prevent_initial_call=True)
def export_results(csv_clicks,model_clicks,data):
    if not data:
        return no_update
    if ctx.triggered_id=='flat-export-model':
        metadata={key:data[key] for key in ['model_version','parameter_source','parameters','assumptions','scope','source']}
        return dcc.send_string(json.dumps(metadata,ensure_ascii=False,indent=2),'bkt_assisted_flat_assumptions.json')
    if not data.get('records'):
        return no_update
    stream=StringIO(newline='');fields=list(dict.fromkeys(key for row in data['records'] for key in row))
    writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(data['records'])
    return dcc.send_string('\ufeff'+stream.getvalue(),'bkt_assisted_flat_results.csv')


if __name__=='__main__':
    app.run(host='127.0.0.1',port=8055,debug=False)
