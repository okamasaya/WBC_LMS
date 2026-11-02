"""添付ガイド冊子21ページのN2配分による15回の合成回答ログ。

python -m sandbox.dashboard.bkt.full_mock_dataset
問題文・音声・公式尺度得点は生成しない。既存の5表形式を再利用する。
"""
import argparse
from collections import Counter
from contextlib import closing
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import random
import sqlite3
import tempfile

from .assisted_model import CONFIDENCE_LABELS, UNDERSTANDING_LABELS
from .mock_dataset import COLUMNS, ROOT, JST, csv_bytes, iso, schema_sql

OUTPUT = ROOT / 'data/mock_jlpt_n2_full_15_sessions'
DATABASE = OUTPUT / 'learning_logs.sqlite3'
SEED = 20261103
VERSION = 'n2-full-guide-v1'
# domain, group, detail, booklet question number, approximate item count.
# No invented linguistic subskills: the intermediate groups organize the guide's labels.
BLUEPRINT = [
    ('言語知識','文字・語彙','漢字読み',1,5),
    ('言語知識','文字・語彙','表記',2,5),
    ('言語知識','文字・語彙','語形成',3,5),
    ('言語知識','文字・語彙','文脈規定',4,7),
    ('言語知識','文字・語彙','言い換え類義',5,5),
    ('言語知識','文字・語彙','用法',6,5),
    ('言語知識','文法','文の文法1（文法形式の判断）',7,12),
    ('言語知識','文法','文の文法2（文の組み立て）',8,5),
    ('言語知識','文法','文章の文法',9,5),
    ('読解','内容理解','短文',10,5),
    ('読解','内容理解','中文',11,9),
    ('読解','統合理解','統合理解',12,2),
    ('読解','主張理解','長文',13,3),
    ('読解','情報検索','情報検索',14,2),
    ('聴解','課題理解','課題理解',1,5),
    ('聴解','ポイント理解','ポイント理解',2,6),
    ('聴解','概要理解','概要理解',3,5),
    ('聴解','即時応答','即時応答',4,12),
    ('聴解','統合理解','統合理解',5,4),
]


def skill_id(domain, number):
    return f"N2_{dict(言語知識='LK',読解='RD',聴解='LS')[domain]}_{number:02d}"


def skill_name(group, detail):
    return f'{group}（{detail}）' if group in ('内容理解','主張理解') else detail


def generate(seed=SEED):
    rng = random.Random(seed)
    dataset = f'SYNTH_N2_FULL_{seed}_V1'
    student = dataset + '_L001'
    tables = {name: [] for name in COLUMNS}
    tables['Student'] = [dict(StudentID=student, DisplayName='架空学習者001（全領域）',
                             IsSynthetic=True, DatasetID=dataset)]
    for domain, group, detail, number, count in BLUEPRINT:
        tables['Skill'].append(dict(SkillID=skill_id(domain,number), SkillName=skill_name(group,detail),
            CategoryLevel1=domain, CategoryLevel2=group, CategoryLevel3=detail, QuestionsPerSession=count))
    # Every session has a different synthetic item ID; no real item text/audio is claimed.
    for session_number in range(1,16):
        sid = f'{dataset}_S{session_number:02d}'
        start = datetime(2026,9,1,19,tzinfo=JST) + timedelta(days=3*(session_number-1))
        cursor = start
        jitter = rng.uniform(-.09,.09)
        rows = []
        for index,(domain, group, detail, number, count) in enumerate(BLUEPRINT):
            skill = skill_id(domain,number)
            for item in range(1,count+1):
                sequence = len(rows)+1
                qid = f'{sid}_{skill}_{item:02d}'
                difficulty = rng.randint(1,5)
                correct_position = rng.randint(1,4)
                probability = max(.15,min(.9,.43+.23*(session_number-1)/14
                    + {'言語知識':.05,'読解':-.07,'聴解':-.02}[domain]
                    + ((index%5)-2)*.025+jitter-.035*(difficulty-3)))
                correct = rng.random() < probability
                confidence = rng.choices([1,2,3,4], weights=[38,32,20,10] if correct else [12,20,33,35])[0]
                understanding = rng.choices([0,1,2,3], weights=[6,14,34,46] if correct else [14,24,36,26])[0]
                seconds = rng.randint(*{'言語知識':(18,40),'読解':(55,115),'聴解':(35,65)}[domain])
                recorded = cursor+timedelta(seconds=seconds)
                position = correct_position if correct else rng.choice([p for p in range(1,5) if p != correct_position])
                tables['Question'].append(dict(QuestionID=qid,SkillID=skill,Difficulty=difficulty,
                    QuestionText='合成回答ログ用の設問ID（問題文・音声なし）',
                    **{f'Option{p}':f'ダミー選択位置{p}' for p in range(1,5)},
                    CorrectOptionPosition=correct_position,SourceQuestionFile='synthetic:no-content'))
                rows.append(dict(ResultID=f'{sid}_Q{sequence:03d}',SessionID=sid,StudentID=student,
                    SessionNumber=session_number,ExamID='JLPT_N2_FULL_GUIDE_MOCK',ExamType='JLPT',ExamLevel='N2',
                    Mode='Actual',QuestionSequence=sequence,QuestionID=qid,SkillID=skill,
                    SkillName=skill_name(group,detail),CategoryLevel1=domain,CategoryLevel2=group,CategoryLevel3=detail,
                    Difficulty=difficulty,UserAnswerDisplayedPosition=position,CorrectAnswerDisplayedPosition=correct_position,
                    IsAnswered=True,IsCorrect=correct,ConfidenceLevel=confidence,ConfidenceLabel=CONFIDENCE_LABELS[confidence],
                    UnderstandingLevel=understanding,UnderstandingLabel=UNDERSTANDING_LABELS[understanding],
                    ResponseTimeMs=seconds*1000,QuestionPresentedAt=iso(cursor),AnsweredAt=iso(recorded-timedelta(seconds=3)),
                    ConfidenceRecordedAt=iso(recorded),IsSynthetic=True,DatasetID=dataset,MockSchemaVersion='1.0'))
                cursor = recorded+timedelta(seconds=2)
        end = cursor
        for row in rows:
            viewed = cursor+timedelta(seconds=5)
            cursor = viewed+timedelta(seconds=rng.randint(15,50))
            row.update(ExplanationViewedAt=iso(viewed),UnderstandingRecordedAt=iso(cursor))
        correct_count = sum(r['IsCorrect'] for r in rows)
        tables['Session'].append(dict(SessionID=sid,StudentID=student,SessionNumber=session_number,
            ExamID='JLPT_N2_FULL_GUIDE_MOCK',ExamType='JLPT',ExamLevel='N2',ExamTitle='JLPT N2 全領域・ガイド準拠モック',
            Mode='Actual',StartAt=iso(start),EndAt=iso(end),ReviewEndAt=iso(cursor),TotalTimeSec=int((end-start).total_seconds()),
            TotalQuestions=107,AnsweredQuestions=107,UnansweredQuestions=0,CorrectCount=correct_count,
            IncorrectCount=107-correct_count,ScoreRate=int(correct_count/107*100+.5),
            IsSynthetic=True,DatasetID=dataset,MockSchemaVersion='1.0'))
        tables['QuestionResult'].extend(rows)
    return tables


def write_dataset(output=OUTPUT, overwrite=False, seed=SEED):
    output = Path(output)
    tables = generate(seed)
    # Finish all outputs before replacing any existing file.
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        database = Path(temporary)/'learning_logs.sqlite3'
        with closing(sqlite3.connect(database)) as conn:
            conn.executescript(schema_sql())
            conn.execute('PRAGMA user_version=1')
            for table, columns in COLUMNS.items():
                names = ','.join(f'"{c[0]}"' for c in columns)
                placeholders = ','.join('?' for _ in columns)
                conn.executemany(f'INSERT INTO "{table}" ({names}) VALUES ({placeholders})',
                    [tuple(row[c[0]] for c in columns) for row in tables[table]])
            conn.commit()
            if conn.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
                raise ValueError('生成DBの整合性検査に失敗しました。')
            if conn.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('生成DBの外部キーが一致しません。')
        files = {'learning_logs.sqlite3':database.read_bytes(),'schema.sql':schema_sql().encode()}
    for table,rows in tables.items():
        files[f'csv/{table}.csv'] = csv_bytes(table,rows)
    manifest = dict(is_synthetic=True,generator_version=VERSION,seed=seed,dataset_id=tables['Student'][0]['DatasetID'],
        sessions=15,items_per_session=107,counts={t:len(rows) for t,rows in tables.items()},
        source=dict(document='JLPT_試験ガイドブック.pdf',booklet_page=21,created_year=2009,
                    sha256='e0cac8f3f693865f2de8932eadf7f7eb9acafd21fb268e1b5e659793ecd578b7',
                    note='小問数は目安。現行試験の固定配分とは扱わない。'),
        blueprint=[dict(domain=d,group=g,detail=t,guide_number=n,count=c,skill_id=skill_id(d,n)) for d,g,t,n,c in BLUEPRINT],
        domain_answers=dict(Counter(r['CategoryLevel1'] for r in tables['QuestionResult'])),
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        files_sha256={name:hashlib.sha256(content).hexdigest() for name,content in files.items()},
        limitations=['架空学習者1人。全回答済み。問題文・本文・音声や素材共有関係は未生成。',
                    'ScoreRateは正答率を整数に丸めた値。公式尺度得点・合否判定なし。',
                    '自信度は1が高く4が低い。解説後理解度は自己申告0〜3。',
                    '時刻は合成操作ログ。聴解音源や本試験の進行を再現しない。',
                    '改善・変動は生成規則による。モデルの精度や学習効果の証拠ではない。'])
    files['manifest.json'] = (json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode()
    for name,content in files.items():
        path = output/name
        if path.exists() and path.read_bytes()!=content and not overwrite:
            raise FileExistsError(f'{path}は内容が異なります。別の出力先か--overwriteを指定してください。')
    for name,content in files.items():
        path = output/name
        path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists() or path.read_bytes()!=content:
            path.write_bytes(content)
    return manifest


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    parser.add_argument('--seed',type=int,default=SEED)
    parser.add_argument('--overwrite',action='store_true')
    args = parser.parse_args()
    print(json.dumps(write_dataset(args.output,args.overwrite,args.seed)['counts'],ensure_ascii=False))
