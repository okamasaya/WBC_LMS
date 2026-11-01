"""モックを現行prototypeの出力処理へ渡し、列が完全一致する互換CSVを作る。

python -m sandbox.dashboard.bkt.prototype_csv
Node.jsが必要。既存のSQL用モックは変更しない。
"""
import argparse
import csv
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
from .mock_dataset import ROOT, REPO, DEFAULT_OUTPUT, generate

OUTPUT=DEFAULT_OUTPUT/'prototype_csv'
JS=ROOT/'tools/prototype_exports.cjs'


def prototype_payload(identity='synthetic', tables=None):
    if identity not in ('synthetic','anonymous'):
        raise ValueError('identityはsyntheticまたはanonymousです。')
    if tables is None:
        tables,_=generate()
    process=subprocess.run(['node',str(JS)],input=json.dumps({'tables':tables,'identity':identity},ensure_ascii=False),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env={**os.environ,'TZ':'Asia/Tokyo'},check=True)
    return json.loads(process.stdout)


def combined_csv(columns, rows):
    # 行の値はResultData/ResultReportと同じオブジェクトから列定義で抽出する。
    stream=StringIO(newline='');writer=csv.writer(stream,lineterminator='\r\n',quoting=csv.QUOTE_ALL)
    writer.writerow([column['header'] for column in columns])
    for row in rows:
        values=[]
        for column in columns:
            value=row.get(column['key'])
            values.append('' if value is None else ('TRUE' if value else 'FALSE') if isinstance(value,bool) else value)
        writer.writerow(values)
    return ('\ufeff'+stream.getvalue()).encode('utf-8')


def write_exports(output=OUTPUT, overwrite=False):
    payload=prototype_payload();sessions=payload['sessions']
    files={
        'Session.csv':combined_csv(payload['schema']['Session'],[s['session'] for s in sessions]),
        'QuestionResult.csv':combined_csv(payload['schema']['QuestionResult'],[r for s in sessions for r in s['records']]),
    }
    sample=sessions[0]
    for exported in sample['exports'].values():
        files['sample_session/'+exported['name']]=('\ufeff'+exported['content']).encode('utf-8')
    files['sample_session/AI_Report.txt']=sample['report'].encode('utf-8')
    mapping=StringIO(newline='');writer=csv.writer(mapping,lineterminator='\r\n')
    writer.writerow(['MockResultID','PrototypeResultID','MockSessionID','PrototypeSessionID','SessionNumber','IsSynthetic'])
    for session in sessions:
        for original,row in zip(session['mock_result_ids'],session['records']):
            writer.writerow([original,row['resultId'],session['mock_session_id'],session['session']['sessionId'],session['session_number'],'TRUE'])
    files['ResultMapping.csv']=('\ufeff'+mapping.getvalue()).encode('utf-8')
    sources=[JS]+[REPO/f'prototype/assets/js/shared/{name}.js' for name in ['questionLoader','examConfig','resultData','resultReview','resultReport']]
    manifest={'is_synthetic':True,'purpose':'current prototype export compatibility','identity':'synthetic learner ID explicitly supplied; default production conf has no studentId','schema':{key:[col['header'] for col in cols] for key,cols in payload['schema'].items()},'session_count':len(sessions),'question_count':sum(len(s['records']) for s in sessions),'source_sha256':{str(path.relative_to(REPO)):hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},'files_sha256':{name:hashlib.sha256(content).hexdigest() for name,content in files.items()},'notes':['aggregate Session/QuestionResult retain the exact current columns and order','sample_session contains the three actual export formats and report from one snapshot','mock-only timestamps and flags are in the original storage CSVs, not added to prototype columns','real current exports may have empty StudentID; never silently combine unidentified learners']}
    files['manifest.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    output=Path(output)
    for name,content in files.items():
        path=output/name
        if path.exists() and path.read_bytes()!=content and not overwrite:
            raise FileExistsError(f'{path}は内容が異なります。別の出力先か--overwriteを指定してください。')
    for name,content in files.items():
        path=output/name;path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists() or path.read_bytes()!=content:path.write_bytes(content)
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    parser.add_argument('--overwrite',action='store_true')
    args=parser.parse_args();manifest=write_exports(args.output,args.overwrite)
    print(json.dumps({'output':str(args.output),'sessions':manifest['session_count'],'answers':manifest['question_count'],'columns':{key:len(cols) for key,cols in manifest['schema'].items()}},ensure_ascii=False))
