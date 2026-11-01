"""正誤中心・補助2項目の独立回答モデル。python -m sandbox.dashboard.bkt.flat_app"""
import csv
from functools import lru_cache
from io import StringIO
import json
from pathlib import Path
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, ctx, dcc, html, dash_table, no_update
from .model import BKTParameters
from .assisted_model import (AuxiliaryAssumptions, CONFIDENCE_LABELS, UNDERSTANDING_LABELS,
                             combinations, estimate_flat, update_flat)
from .demo_data import sample_records
from .csv_inference import import_uploads, estimate_import

ROOT = Path(__file__).resolve().parent
app = Dash(__name__, assets_folder=str(ROOT / 'assets'), title='BKT・3項目フラット試作')


def picker(identifier, label, options, value, clearable=False):
    return html.Label([label, dcc.Dropdown(id=identifier, options=[{'label': text, 'value': key} for key, text in options.items()], value=value, clearable=clearable)])


app.layout = html.Main(className='alp-dashboard flat-dashboard', children=[
    dcc.Store(id='flat-analysis'), dcc.Store(id='flat-uploaded', storage_type='memory'),
    dcc.Download(id='flat-download'),
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
    html.Section(className='alp-card',children=[html.H2('3. 学習ログの取込・明細と出力'),
        dcc.Upload(id='flat-upload', children=html.Div(['実施結果のCSVを選択・ドロップ', html.Small('UTF-8、複数選択可。QuestionResultまたは統合Raw CSV。Sessionを一緒に選んでも構いません。')]), multiple=True, accept='.csv', className='alp-upload'),
        html.P(id='flat-selected-files'),
        html.Div(className='alp-actions', children=[html.Button('CSVを取り込む', id='flat-import'), html.Button('取込データをクリア', id='flat-clear-upload')]),
        html.P(id='flat-import-status', role='status'),
        html.P('点数は推定に使いません。未回答は除外し、RawとQuestionResultに含まれる同じ回答は一度だけ扱います。StudentIDが空欄でも各回答を独立に評価します。取込データはファイルへ保存せず、この画面のメモリーで扱います。', className='alp-note'),
        picker('flat-dataset','データの種類',{'patterns':'全32パターン（合成データ）','demo':'既存の架空ログ24回答（各回答は独立に評価）','n2-mock':'JLPT N2・20回分のモック','uploaded':'取り込んだ実施結果CSV'},'patterns'),
        picker('flat-filter','正誤の絞り込み',{'all':'すべて','correct':'正解','wrong':'不正解'},'all'),
        html.P(id='flat-summary',role='status'),
        dash_table.DataTable(id='flat-table',page_size=12,sort_action='native',style_table={'overflowX':'auto'},style_cell={'fontFamily':'inherit','minWidth':'100px','padding':'8px'}),
        html.Details([html.Summary('未回答・重複・不正な行の理由'), dash_table.DataTable(id='flat-excluded-table', columns=[{'id':key,'name':label} for key,label in [('Row','入力行'),('ResultID','回答ID'),('Reason','理由')]], data=[], page_size=10, style_table={'overflowX':'auto'}, style_cell={'fontFamily':'inherit','whiteSpace':'normal','padding':'8px'})]),
        html.Div(className='alp-actions',children=[html.Button('表示対象をCSV保存',id='flat-export',disabled=True),html.Button('モデルの仮定をJSON保存',id='flat-export-model',disabled=True),html.Button('除外・重複の理由をCSV保存',id='flat-export-excluded',disabled=True)]),
        html.P('CSVは表示ページだけでなく、選択した正誤条件に合う全行を保存します。問題文・解説・点数は取込対象から外し、識別情報と推定に必要な項目を保持します。Django連携と永続保存は次段階です。',className='alp-note')])])


@app.callback(Output('flat-selected-files','children'), Input('flat-upload','filename'))
def selected_files(filenames):
    if isinstance(filenames, str):
        filenames = [filenames]
    return '選択済み: ' + ' / '.join(filenames) if filenames else 'CSVはまだ選択されていません。'


@app.callback(Output('flat-uploaded','data'), Output('flat-import-status','children'), Output('flat-dataset','value'), Output('flat-upload','contents'), Output('flat-upload','filename'),
              Input('flat-import','n_clicks'), Input('flat-clear-upload','n_clicks'), State('flat-upload','contents'), State('flat-upload','filename'), prevent_initial_call=True)
def load_upload(import_clicks, clear_clicks, contents, filenames):
    if ctx.triggered_id == 'flat-clear-upload':
        return None, '取込データをクリアしました。', 'uploaded', None, None
    try:
        data = import_uploads(contents, filenames)
        files = ' / '.join(f"{item['name']} [{item['kind']}]" for item in data['files'])
        message = f"取込完了: {files}。回答入力 {data['input_count']}行 ／ 重複を除く {data['unique_input_count']}行 ／ 重複 {len(data['duplicates'])}行。"
        return data, message, 'uploaded', None, None
    except ValueError as error:
        return None, f'取り込めません: {error}。前の取込結果はクリアしました。', 'uploaded', no_update, no_update


@lru_cache(maxsize=2)
def _mock_records(mtime_ns):
    # 同梱の公開合成データだけを再利用。アップロード内容は共有キャッシュへ入れない。
    with (ROOT/'data/mock_jlpt_n2_20_sessions/prototype_csv/QuestionResult.csv').open(encoding='utf-8-sig',newline='') as stream:
        return tuple(csv.DictReader(stream))


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


@app.callback(Output('flat-status','children'),Output('flat-single','children'),Output('flat-stages','figure'),Output('flat-wrong','figure'),Output('flat-right','figure'),Output('flat-summary','children'),Output('flat-table','data'),Output('flat-table','columns'),Output('flat-analysis','data'),Output('flat-export','disabled'),Output('flat-export-model','disabled'),Output('flat-excluded-table','data'),Output('flat-export-excluded','disabled'),
              Input('flat-correct','value'),Input('flat-confidence','value'),Input('flat-understanding','value'),Input('flat-l0','value'),Input('flat-t','value'),Input('flat-g','value'),Input('flat-s','value'),Input('flat-dataset','value'),Input('flat-filter','value'),Input('flat-uploaded','data'))
def render(correct,confidence,understanding,p_l0,p_t,p_g,p_s,dataset,selection,uploaded=None):
    try:
        if correct not in (0,1):
            raise ValueError('正誤を選択してください。')
        parameters=BKTParameters(p_l0,p_t,p_g,p_s)
        single=update_flat(correct==1,confidence,understanding,parameters)
        patterns=estimate_flat(combinations(),parameters)
        if dataset=='n2-mock':
            raw_records=_mock_records((ROOT/'data/mock_jlpt_n2_20_sessions/prototype_csv/QuestionResult.csv').stat().st_mtime_ns)
            result=estimate_flat(raw_records,parameters)
        elif dataset=='uploaded':
            result=estimate_import(uploaded,parameters) if uploaded else estimate_flat([],parameters)
        else:
            raw_records=sample_records() if dataset=='demo' else combinations()
            result=estimate_flat(raw_records,parameters)
    except (ValueError,TypeError,OSError,csv.Error) as error:
        chart=blank('入力パラメータを確認してください')
        return str(error),[],chart,chart,chart,'推定結果をクリアしました。',[],[],None,True,True,[],True
    stages=go.Figure()
    for name,values in [('正誤のみ・標準BKT',[single['PBefore'],single['ClassicPosterior'],single['ClassicAfterLearning']]),('自信度・理解度の補助あり',[single['PBefore'],single['AssistedPosterior'],single['AssistedAfterLearning']])]:
        stages.add_trace(go.Scatter(x=['初期','正誤観測後','学習遷移後'],y=values,mode='lines+markers',name=name))
    stages.update_layout(template='plotly_white',height=360,yaxis={'range':[0,1],'title':'仮定したモデル内の確率'},legend={'orientation':'h'},margin={'l':55,'r':20,'t':30,'b':70})
    metrics=[('標準BKT・正誤更新後',single['ClassicPosterior']),('補助あり・正誤更新後',single['AssistedPosterior']),('補助あり・学習遷移後',single['AssistedAfterLearning']),('同一スキルを仮定した次問正答確率',single['NextCorrect'])]
    kpis=[html.Div([html.Span(label),html.Strong(f'{value:.4f}')],className='alp-kpi') for label,value in metrics]
    rows=[r for r in result['records'] if selection=='all' or r['IsCorrect']==(selection=='correct')]
    columns=[{'id':key,'name':label} for key,label in [('Row','入力行'),('SessionID','実施ID'),('QuestionSequence','問題順'),('SkillName','スキル'),('ResultID','回答ID'),('IsCorrect','正誤'),('ConfidenceLevel','自信度（1=高）'),('UnderstandingLevel','解説理解度（3=高）'),('ObservationWeight','自信度の重み'),('EffectiveLearning','有効P(T)'),('ClassicPosterior','標準・観測後'),('AssistedPosterior','補助・観測後'),('AssistedAfterLearning','補助・遷移後'),('NextCorrect','同一スキルを仮定した次問正答確率')]]
    status=f"各回答はP(L0)={p_l0}から独立評価。自信度の重み={single['ObservationWeight']}、解説後の有効P(T)={single['EffectiveLearning']:.4f}。未校正の仮説モデルです。"
    source={'demo':'既存の架空ログ','n2-mock':'JLPT N2・20回分の合成ログ','uploaded':'取り込んだ実施結果CSV'}.get(dataset,'設計用の合成32パターン')
    summary=f"{source}：評価可能 {len(result['records'])}行 ／ 表示対象 {len(rows)}行 ／ 除外 {len(result['excluded'])}行。履歴による累積更新はしていません。"
    if dataset=='uploaded':
        summary += f" 重複を除去 {len(result.get('duplicates',[]))}行。"
        if not result['records']:
            summary += ' 推定対象の回答がありません。CSVを取り込み、IsAnsweredと除外理由を確認してください。'
    stored={**result,'records':rows,'source':source,'scope':'independent_answers_same_prior'}
    excluded=result['excluded']+result.get('duplicates',[])
    return status,kpis,stages,heatmap(patterns['records'],False),heatmap(patterns['records'],True),summary,rows,columns,stored,not bool(rows),not bool(result['records']),excluded,not bool(excluded)


@app.callback(Output('flat-correct','value'),Output('flat-confidence','value'),Output('flat-understanding','value'),Input('flat-wrong','clickData'),Input('flat-right','clickData'),prevent_initial_call=True)
def select_pattern(wrong,right):
    payload=right if ctx.triggered_id=='flat-right' else wrong
    if not payload or not payload.get('points'):
        return no_update,no_update,no_update
    point=payload['points'][0]
    return int(ctx.triggered_id=='flat-right'),int(point['x']),int(point['y'])


@app.callback(Output('flat-download','data'),Input('flat-export','n_clicks'),Input('flat-export-model','n_clicks'),Input('flat-export-excluded','n_clicks'),State('flat-analysis','data'),prevent_initial_call=True)
def export_results(csv_clicks,model_clicks,excluded_clicks,data):
    if not data:
        return no_update
    if ctx.triggered_id=='flat-export-model':
        metadata={key:data[key] for key in ['model_version','parameter_source','parameters','assumptions','scope','source']}
        return dcc.send_string(json.dumps(metadata,ensure_ascii=False,indent=2),'bkt_assisted_flat_assumptions.json')
    records=data['excluded']+data.get('duplicates',[]) if ctx.triggered_id=='flat-export-excluded' else data.get('records')
    if not records:
        return no_update
    stream=StringIO(newline='');fields=list(dict.fromkeys(key for row in records for key in row))
    writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(records)
    filename='bkt_assisted_flat_excluded.csv' if ctx.triggered_id=='flat-export-excluded' else 'bkt_assisted_flat_results.csv'
    return dcc.send_string('\ufeff'+stream.getvalue(),filename)


if __name__=='__main__':
    app.run(host='127.0.0.1',port=8055,debug=False)
