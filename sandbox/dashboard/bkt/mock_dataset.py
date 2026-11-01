"""JLPT N2言語知識：1人×20回の合成ログ。標準ライブラリだけで再生成する。

python -m sandbox.dashboard.bkt.mock_dataset
CSVが同じなら再実行は何も変更しない。異なる既存ファイルの更新には--overwrite。
"""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timedelta, timezone
import hashlib
from io import StringIO
import json
from pathlib import Path
import random

from .assisted_model import CONFIDENCE_LABELS, UNDERSTANDING_LABELS

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
CONFIG = REPO / 'prototype/language/JLPT_N2/conf_JLPT_N2_LK.json'
DEFAULT_OUTPUT = ROOT / 'data/mock_jlpt_n2_20_sessions'
GENERATOR_VERSION = 'jlpt-n2-mock-v1'
DEFAULT_SEED = 20261102
JST = timezone(timedelta(hours=9))

# 列はここで管理する。IDと時点を分け、SQLite移行時の型と外部キーを明示。
COLUMNS = {
 'Student': [('StudentID','TEXT','PK','架空学習者ID'),('DisplayName','TEXT','','架空の表示名'),('IsSynthetic','BOOLEAN','','常にTRUE'),('DatasetID','TEXT','','合成データセットID')],
 'Skill': [('SkillID','TEXT','PK','既存confのスキルID'),('SkillName','TEXT','','既存confのスキル名'),('CategoryLevel1','TEXT','','言語知識'),('CategoryLevel2','TEXT','','文字・語彙・文法'),('CategoryLevel3','TEXT','','下位カテゴリ'),('QuestionsPerSession','INTEGER','','開発用の1回あたり出題数')],
 'Question': [('QuestionID','TEXT','PK','既存問題のID'),('SkillID','TEXT','FK:Skill.SkillID','スキル'),('Difficulty','INTEGER','','既存の難易度1〜5'),('QuestionText','TEXT','','既存問題文、HTMLタグを含む場合あり'),('Option1','TEXT','','選択肢1'),('Option2','TEXT','','選択肢2'),('Option3','TEXT','','選択肢3'),('Option4','TEXT','','選択肢4'),('CorrectOptionPosition','INTEGER','','正解位置1〜4'),('SourceQuestionFile','TEXT','','問題定義のリポジトリ相対パス')],
 'Session': [('SessionID','TEXT','PK','1回の受験ID'),('StudentID','TEXT','FK:Student.StudentID','架空学習者'),('SessionNumber','INTEGER','','1〜20の回次'),('ExamID','TEXT','','試験ID'),('ExamType','TEXT','','JLPT'),('ExamLevel','TEXT','','N2'),('ExamTitle','TEXT','','JLPT N2 言語知識'),('Mode','TEXT','','Actual'),('StartAt','DATETIME','','開始、JSTオフセット付きISO8601'),('EndAt','DATETIME','','試験終了、解説閲覧より前'),('ReviewEndAt','DATETIME','','解説理解度の記録完了'),('TotalTimeSec','INTEGER','','試験終了−開始の秒数'),('TotalQuestions','INTEGER','','出題数'),('AnsweredQuestions','INTEGER','','回答数'),('UnansweredQuestions','INTEGER','','v1は0'),('CorrectCount','INTEGER','','正答数'),('IncorrectCount','INTEGER','','回答済み誤答数'),('ScoreRate','INTEGER','','正答数÷出題数×100の四捨五入、0〜100'),('IsSynthetic','BOOLEAN','','常にTRUE'),('DatasetID','TEXT','','合成データセットID'),('MockSchemaVersion','TEXT','','モック独自のスキーマ版。公式出力スキーマ版とは別')],
 'QuestionResult': [('ResultID','TEXT','PK','回答レコードの一意ID'),('SessionID','TEXT','FK:Session.SessionID','受験ID'),('StudentID','TEXT','FK:Student.StudentID','架空学習者'),('SessionNumber','INTEGER','','回次、Sessionと一致'),('ExamID','TEXT','','試験ID'),('ExamType','TEXT','','JLPT'),('ExamLevel','TEXT','','N2'),('Mode','TEXT','','Actual'),('QuestionSequence','INTEGER','','回内の出題順1〜30'),('QuestionID','TEXT','FK:Question.QuestionID','既存問題ID'),('SkillID','TEXT','FK:Skill.SkillID','スキルID'),('SkillName','TEXT','','スキル名'),('CategoryLevel1','TEXT','','大分類'),('CategoryLevel2','TEXT','','中分類'),('CategoryLevel3','TEXT','','小分類'),('Difficulty','INTEGER','','既存問題の難易度1〜5'),('UserAnswerDisplayedPosition','INTEGER','','選択位置1〜4、選択肢シャッフルなし'),('CorrectAnswerDisplayedPosition','INTEGER','','正解位置1〜4'),('IsAnswered','BOOLEAN','','v1は全行TRUE'),('IsCorrect','BOOLEAN','','正誤、TRUE/FALSE'),('ConfidenceLevel','INTEGER','','1が高く4が低い、未入力は空欄。v1は欠損なし'),('ConfidenceLabel','TEXT','','自信度の日本語ラベル'),('UnderstandingLevel','INTEGER','','解説後の理解度、0が低く3が高い。v1は欠損なし'),('UnderstandingLabel','TEXT','','理解度の日本語ラベル'),('ResponseTimeMs','INTEGER','','提示から自信度記録まで、ミリ秒'),('QuestionPresentedAt','DATETIME','','問題提示時刻'),('AnsweredAt','DATETIME','','回答選択時刻'),('ConfidenceRecordedAt','DATETIME','','回答時の自信度記録時刻'),('ExplanationViewedAt','DATETIME','','試験終了後の解説閲覧時刻、追加モック項目'),('UnderstandingRecordedAt','DATETIME','','解説後の理解度記録時刻、追加モック項目'),('IsSynthetic','BOOLEAN','','常にTRUE'),('DatasetID','TEXT','','合成データセットID'),('MockSchemaVersion','TEXT','','モック独自のスキーマ版')],
}


def iso(value):
    return value.isoformat(timespec='seconds')


def csv_bytes(table, rows):
    stream = StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=[column[0] for column in COLUMNS[table]], lineterminator='\r\n')
    writer.writeheader()
    for row in rows:
        writer.writerow({key: ('TRUE' if value else 'FALSE') if isinstance(value, bool) else value for key,value in row.items()})
    return ('\ufeff' + stream.getvalue()).encode('utf-8')


def schema_sql():
    statements=['PRAGMA foreign_keys = ON;']
    for table,columns in COLUMNS.items():
        definitions=[];relations=[]
        for name,kind,key,_ in columns:
            sql_type='INTEGER' if kind in ('INTEGER','BOOLEAN') else 'TEXT'
            constraint=' PRIMARY KEY' if key=='PK' else ''
            constraint+=' NOT NULL'
            if kind=='BOOLEAN': constraint+=f' CHECK ("{name}" IN (0,1))'
            definitions.append(f'"{name}" {sql_type}{constraint}')
            if key.startswith('FK:'):
                parent,parent_column=key[3:].split('.')
                relations.append(f'FOREIGN KEY ("{name}") REFERENCES "{parent}" ("{parent_column}")')
        definitions.extend(relations)
        if table=='Question':
            definitions+=['UNIQUE (QuestionID, SkillID)','CHECK (Difficulty BETWEEN 1 AND 5)','CHECK (CorrectOptionPosition BETWEEN 1 AND 4)']
        if table=='Session':
            definitions+=['UNIQUE (SessionID, StudentID)','UNIQUE (StudentID, SessionNumber)','CHECK (TotalQuestions = AnsweredQuestions + UnansweredQuestions)','CHECK (AnsweredQuestions = CorrectCount + IncorrectCount)']
        if table=='QuestionResult':
            definitions+=['UNIQUE (SessionID, QuestionSequence)','UNIQUE (SessionID, QuestionID)',
                'FOREIGN KEY (SessionID, StudentID) REFERENCES Session (SessionID, StudentID)',
                'FOREIGN KEY (QuestionID, SkillID) REFERENCES Question (QuestionID, SkillID)',
                'CHECK (ConfidenceLevel BETWEEN 1 AND 4)','CHECK (UnderstandingLevel BETWEEN 0 AND 3)',
                'CHECK (ResponseTimeMs > 0)','CHECK (IsCorrect = (UserAnswerDisplayedPosition = CorrectAnswerDisplayedPosition))']
        statements.append('CREATE TABLE "'+table+'" (\n  '+',\n  '.join(definitions)+'\n);')
    return '\n\n'.join(statements)+'\n'


def generate(seed=DEFAULT_SEED, sessions=20, start_date='2026-09-01'):
    if not 1 <= sessions <= 100:
        raise ValueError('回数は1〜100で指定してください。')
    start=datetime.fromisoformat(start_date)
    if start.tzinfo is not None or start.time()!=datetime.min.time():
        raise ValueError('開始日はYYYY-MM-DDで指定してください。')
    start=start.replace(hour=19,tzinfo=JST)
    conf=json.loads(CONFIG.read_text(encoding='utf-8'))
    source_hashes={str(CONFIG.relative_to(REPO)):hashlib.sha256(CONFIG.read_bytes()).hexdigest()}
    categories=conf['categories'];mapping={(c['categoryLv1'],c['categoryLv2'],c['categoryLv3']):c for c in categories}
    pools=defaultdict(list)
    for name in conf['questionFiles']:
        path=(CONFIG.parent/name).resolve();source_hashes[str(path.relative_to(REPO))]=hashlib.sha256(path.read_bytes()).hexdigest()
        for q in json.loads(path.read_text(encoding='utf-8')):
            category=mapping.get((q['category_lv1'],q['category_lv2'],q['category_lv3']))
            if category:
                options=[q[f'option_{i}'] for i in range(1,5)]
                if options.count(q['correct_answer'])!=1:
                    raise ValueError(f"正解位置を特定できません: {q['question_id']}")
                pools[category['skillId']].append({'QuestionID':q['question_id'],'SkillID':category['skillId'],'Difficulty':q['difficulty'],'QuestionText':q['question_text'],**{f'Option{i}':option for i,option in enumerate(options,1)},'CorrectOptionPosition':options.index(q['correct_answer'])+1,'SourceQuestionFile':str(path.relative_to(REPO))})
    settings={'generator_version':GENERATOR_VERSION,'seed':seed,'sessions':sessions,'start_date':start_date,'spacing_days':3,'source_sha256':source_hashes}
    dataset_id='SYNTH_N2_'+hashlib.sha256(json.dumps(settings,sort_keys=True).encode()).hexdigest()[:10]
    student_id=dataset_id+'_L001';rng=random.Random(seed)
    tables={name:[] for name in COLUMNS}
    tables['Student']=[{'StudentID':student_id,'DisplayName':'架空学習者001','IsSynthetic':True,'DatasetID':dataset_id}]
    tables['Skill']=[{'SkillID':c['skillId'],'SkillName':c['skillName'],'CategoryLevel1':c['categoryLv1'],'CategoryLevel2':c['categoryLv2'],'CategoryLevel3':c['categoryLv3'],'QuestionsPerSession':c['actualCount']} for c in categories]
    selected_questions={}
    # 独立の合成生成規則。BKTの推定値を正解・真値として生成しない。
    skill_offsets={c['skillId']:offset for c,offset in zip(categories,[.04,.00,-.06,.02,-.02,-.05,.03,-.08,-.10])}
    for number in range(1,sessions+1):
        session_id=f'{dataset_id}_S{number:02d}';started=start+timedelta(days=3*(number-1));cursor=started
        progress=(number-1)/max(1,sessions-1);daily_jitter=rng.uniform(-.07,.07)
        selected=[]
        for category in categories:
            picked=rng.sample(pools[category['skillId']],category['actualCount'])
            selected.extend((q,category) for q in picked)
        rows=[]
        for sequence,(q,category) in enumerate(selected,1):
            probability=max(.15,min(.9,.40+.30*progress+skill_offsets[q['SkillID']]+daily_jitter-.055*(q['Difficulty']-3)))
            correct=rng.random()<probability
            confidence=rng.choices([1,2,3,4],weights=[.38,.32,.20,.10] if correct else [.12,.20,.33,.35])[0]
            understanding=rng.choices([0,1,2,3],weights=[.06,.14,.34,.46] if correct else [.14,.24,.36,.26])[0]
            confidence_seconds=rng.randint(2,6)
            response_seconds=rng.randint(18,47)+3*(confidence-1)+max(0,q['Difficulty']-3)*2
            confidence_at=cursor+timedelta(seconds=response_seconds)
            answered=confidence_at-timedelta(seconds=confidence_seconds)
            wrong_positions=[value for value in range(1,5) if value!=q['CorrectOptionPosition']]
            answer_position=q['CorrectOptionPosition'] if correct else rng.choice(wrong_positions)
            rows.append({'ResultID':f'{session_id}_Q{sequence:03d}','SessionID':session_id,'StudentID':student_id,'SessionNumber':number,'ExamID':conf['examId'],'ExamType':conf['examType'],'ExamLevel':conf['examLevel'],'Mode':'Actual','QuestionSequence':sequence,'QuestionID':q['QuestionID'],'SkillID':q['SkillID'],'SkillName':category['skillName'],'CategoryLevel1':category['categoryLv1'],'CategoryLevel2':category['categoryLv2'],'CategoryLevel3':category['categoryLv3'],'Difficulty':q['Difficulty'],'UserAnswerDisplayedPosition':answer_position,'CorrectAnswerDisplayedPosition':q['CorrectOptionPosition'],'IsAnswered':True,'IsCorrect':correct,'ConfidenceLevel':confidence,'ConfidenceLabel':CONFIDENCE_LABELS[confidence],'UnderstandingLevel':understanding,'UnderstandingLabel':UNDERSTANDING_LABELS[understanding],'ResponseTimeMs':response_seconds*1000,'QuestionPresentedAt':iso(cursor),'AnsweredAt':iso(answered),'ConfidenceRecordedAt':iso(confidence_at),'IsSynthetic':True,'DatasetID':dataset_id,'MockSchemaVersion':'1.0'})
            cursor=confidence_at+timedelta(seconds=rng.randint(2,5))
            selected_questions[q['QuestionID']]=q
        ended=cursor
        if (ended-started).total_seconds()>conf['actual']['timeLimitMinutes']*60:
            raise ValueError('生成した解答時間が設定の制限時間を超えています。生成規則を見直してください。')
        for row in rows:
            viewed=cursor+timedelta(seconds=rng.randint(3,8))
            cursor=viewed+timedelta(seconds=rng.randint(25,100))
            row['ExplanationViewedAt']=iso(viewed);row['UnderstandingRecordedAt']=iso(cursor)
        correct_count=sum(row['IsCorrect'] for row in rows)
        tables['Session'].append({'SessionID':session_id,'StudentID':student_id,'SessionNumber':number,'ExamID':conf['examId'],'ExamType':conf['examType'],'ExamLevel':conf['examLevel'],'ExamTitle':conf['examTitle'],'Mode':'Actual','StartAt':iso(started),'EndAt':iso(ended),'ReviewEndAt':iso(cursor),'TotalTimeSec':int((ended-started).total_seconds()),'TotalQuestions':len(rows),'AnsweredQuestions':len(rows),'UnansweredQuestions':0,'CorrectCount':correct_count,'IncorrectCount':len(rows)-correct_count,'ScoreRate':int(correct_count/len(rows)*100+.5),'IsSynthetic':True,'DatasetID':dataset_id,'MockSchemaVersion':'1.0'})
        tables['QuestionResult'].extend(rows)
    tables['Question']=[selected_questions[key] for key in sorted(selected_questions)]
    results=tables['QuestionResult']
    manifest={**settings,'dataset_id':dataset_id,'mock_schema_version':'1.0','is_synthetic':True,'student_count':1,'rows':{name:len(rows) for name,rows in tables.items()},'questions_per_session':sum(c['actualCount'] for c in categories),'all_answered':True,'missing_auxiliaries':0,'confidence_direction':'1=high,4=low','understanding_direction':'0=low,3=high','source_question_definitions':'existing repository, not synthetic performance','generation_rules':{'correct_probability':'clip(0.40+0.30*progress+skill_offset+session_jitter-0.055*(difficulty-3),0.15,0.90)','skill_offsets':skill_offsets,'session_jitter':'uniform(-0.07,0.07)','confidence_weights_given_correct':[.38,.32,.20,.10],'confidence_weights_given_wrong':[.12,.20,.33,.35],'understanding_weights_given_correct':[.06,.14,.34,.46],'understanding_weights_given_wrong':[.14,.24,.36,.26],'no_bkt_model_used':True},'summary':{'correct_count':sum(r['IsCorrect'] for r in results),'high_confidence_wrong':sum(not r['IsCorrect'] and r['ConfidenceLevel']<=2 for r in results),'low_confidence_correct':sum(r['IsCorrect'] and r['ConfidenceLevel']>=3 for r in results),'confidence_counts':dict(sorted(Counter(r['ConfidenceLevel'] for r in results).items())),'understanding_counts':dict(sorted(Counter(r['UnderstandingLevel'] for r in results).items()))},'limitations':['synthetic observations, not evidence of model accuracy','development quota, not official complete JLPT','all explanations and understanding checks occur after exam end','v1 has no missing or unanswered observations','no persistent SQLite database is created']}
    return tables,manifest


def write_dataset(output=DEFAULT_OUTPUT, overwrite=False, **settings):
    tables,manifest=generate(**settings)
    files={f'{name}.csv':csv_bytes(name,rows) for name,rows in tables.items()}
    dictionary=StringIO(newline='');writer=csv.writer(dictionary,lineterminator='\r\n');writer.writerow(['Table','Column','Type','Key','NullableInV1','Description'])
    for table,columns in COLUMNS.items():
        for name,kind,key,description in columns:
            writer.writerow([table,name,kind,key,'FALSE',description])
    files['DataDictionary.csv']=('\ufeff'+dictionary.getvalue()).encode('utf-8')
    files['schema.sql']=schema_sql().encode('utf-8')
    manifest['files_sha256']={name:hashlib.sha256(content).hexdigest() for name,content in files.items()}
    files['DatasetManifest.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    output=Path(output)
    for name,content in files.items():
        if (output/name).exists() and (output/name).read_bytes()!=content and not overwrite:
            raise FileExistsError(f'{output/name}は内容が異なります。別の出力先か--overwriteを指定してください。')
    output.mkdir(parents=True,exist_ok=True)
    for name,content in files.items():
        if not (output/name).exists() or (output/name).read_bytes()!=content:
            (output/name).write_bytes(content)
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed',type=int,default=DEFAULT_SEED)
    parser.add_argument('--sessions',type=int,default=20)
    parser.add_argument('--start-date',default='2026-09-01')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--overwrite',action='store_true')
    args=parser.parse_args()
    output=args.output or ROOT/f'data/mock_jlpt_n2_{args.sessions}_sessions'
    manifest=write_dataset(output,overwrite=args.overwrite,seed=args.seed,sessions=args.sessions,start_date=args.start_date)
    print(json.dumps({'output':str(output),'dataset_id':manifest['dataset_id'],'rows':manifest['rows'],'summary':manifest['summary']},ensure_ascii=False,indent=2))
