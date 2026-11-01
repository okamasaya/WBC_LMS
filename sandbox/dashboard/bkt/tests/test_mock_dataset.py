import csv
from collections import Counter,defaultdict
from datetime import datetime
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from sandbox.dashboard.bkt.mock_dataset import COLUMNS, DEFAULT_OUTPUT, generate, schema_sql, write_dataset
from sandbox.dashboard.bkt.learning_data import normalize_records, parse_question_csv
from sandbox.dashboard.bkt.model import estimate
from sandbox.dashboard.bkt.assisted_model import estimate_flat
from sandbox.dashboard.bkt.flat_app import render


class MockDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables,cls.manifest=generate()

    def test_counts_and_session_quotas(self):
        self.assertEqual(len(self.tables['Student']),1)
        self.assertEqual(len(self.tables['Session']),20)
        self.assertEqual(len(self.tables['QuestionResult']),600)
        by_session=defaultdict(list)
        for row in self.tables['QuestionResult']:by_session[row['SessionID']].append(row)
        quotas={r['SkillID']:r['QuestionsPerSession'] for r in self.tables['Skill']}
        for rows in by_session.values():
            self.assertEqual(Counter(r['SkillID'] for r in rows),quotas)
            self.assertEqual([r['QuestionSequence'] for r in rows],list(range(1,31)))
            self.assertEqual(len({r['QuestionID'] for r in rows}),30)

    def test_keys_relations_and_answers(self):
        sessions={r['SessionID']:r for r in self.tables['Session']}
        questions={r['QuestionID']:r for r in self.tables['Question']}
        results=self.tables['QuestionResult']
        self.assertEqual(len({r['ResultID'] for r in results}),600)
        self.assertLess(len(questions),600)  # 回をまたぐ反復は許容する。
        for row in results:
            session=sessions[row['SessionID']];question=questions[row['QuestionID']]
            self.assertEqual(row['StudentID'],session['StudentID'])
            self.assertEqual(row['SessionNumber'],session['SessionNumber'])
            self.assertEqual(row['SkillID'],question['SkillID'])
            self.assertEqual(row['IsCorrect'],row['UserAnswerDisplayedPosition']==question['CorrectOptionPosition'])
            self.assertTrue(row['IsSynthetic'] and row['IsAnswered'])

    def test_real_question_definitions_and_answer_positions(self):
        repo=Path(__file__).resolve().parents[4]
        source={}
        for path in (repo/'prototype/language/JLPT_N2/data').glob('JLPT_N2_LK_*.json'):
            for row in json.loads(path.read_text()):
                source[row['question_id']]=row
        for question in self.tables['Question']:
            raw=source[question['QuestionID']]
            self.assertEqual(question['QuestionText'],raw['question_text'])
            self.assertEqual(question['Difficulty'],raw['difficulty'])
            self.assertEqual(raw[f"option_{question['CorrectOptionPosition']}"],raw['correct_answer'])

    def test_timestamp_order_and_explanation_after_exam(self):
        sessions={r['SessionID']:r for r in self.tables['Session']}
        previous_answer=None
        for row in self.tables['QuestionResult']:
            session=sessions[row['SessionID']]
            names=['QuestionPresentedAt','AnsweredAt','ConfidenceRecordedAt','ExplanationViewedAt','UnderstandingRecordedAt']
            values=[datetime.fromisoformat(row[key]) for key in names]
            self.assertEqual(values,sorted(values))
            self.assertTrue(all(value.utcoffset().total_seconds()==32400 for value in values))
            self.assertGreaterEqual(values[3],datetime.fromisoformat(session['EndAt']))
            self.assertLessEqual(values[4],datetime.fromisoformat(session['ReviewEndAt']))
            self.assertEqual(int((values[2]-values[0]).total_seconds()*1000),row['ResponseTimeMs'])
            if previous_answer:self.assertGreater(values[1],previous_answer)
            previous_answer=values[1]
        for session in sessions.values():self.assertLessEqual(session['TotalTimeSec'],2400)

    def test_summary_and_self_report_variation(self):
        by_session=defaultdict(list)
        for row in self.tables['QuestionResult']:by_session[row['SessionID']].append(row)
        for session in self.tables['Session']:
            correct=sum(row['IsCorrect'] for row in by_session[session['SessionID']])
            self.assertEqual(session['CorrectCount'],correct)
            self.assertEqual(session['IncorrectCount'],30-correct)
            self.assertEqual(session['ScoreRate'],int(correct/30*100+.5))
        self.assertEqual({r['ConfidenceLevel'] for r in self.tables['QuestionResult']},{1,2,3,4})
        self.assertEqual({r['UnderstandingLevel'] for r in self.tables['QuestionResult']},{0,1,2,3})
        self.assertGreater(self.manifest['summary']['high_confidence_wrong'],0)
        self.assertGreater(self.manifest['summary']['low_confidence_correct'],0)

    def test_seed_reproducibility_and_safe_rewrite(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)
            (out/'notes.md').write_text('user notes preserved')
            write_dataset(out)
            first={p.name:p.read_bytes() for p in out.iterdir()}
            write_dataset(out)
            self.assertEqual(first,{p.name:p.read_bytes() for p in out.iterdir()})
            with self.assertRaises(FileExistsError):write_dataset(out,seed=7)
            self.assertEqual(first,{p.name:p.read_bytes() for p in out.iterdir()})
        changed,_=generate(seed=7)
        fields=['QuestionID','IsCorrect','ConfidenceLevel','UnderstandingLevel']
        self.assertNotEqual([[r[key] for key in fields] for r in changed['QuestionResult']],[[r[key] for key in fields] for r in self.tables['QuestionResult']])
        short,_=generate(sessions=2)
        self.assertEqual(len(short['QuestionResult']),60)
        for count in [0,101]:
            with self.assertRaises(ValueError):generate(sessions=count)

    def test_committed_files_and_hashes_match_generator(self):
        with tempfile.TemporaryDirectory() as temp:
            write_dataset(temp)
            for path in Path(temp).iterdir():
                self.assertEqual(path.read_bytes(),(DEFAULT_OUTPUT/path.name).read_bytes(),path.name)
        manifest=json.loads((DEFAULT_OUTPUT/'DatasetManifest.json').read_text())
        import hashlib
        for name,sha in manifest['files_sha256'].items():
            self.assertEqual(hashlib.sha256((DEFAULT_OUTPUT/name).read_bytes()).hexdigest(),sha)

    def test_existing_ingestion_and_both_models(self):
        text=(DEFAULT_OUTPUT/'QuestionResult.csv').read_text(encoding='utf-8-sig')
        records=normalize_records(parse_question_csv(text))
        self.assertEqual(len(records['records']),600)
        self.assertEqual(records['excluded'],[])
        classic=estimate(records['records'])
        self.assertEqual(len(classic['states']),9)
        self.assertEqual(len(classic['history']),600)
        assisted=estimate_flat(records['records'])
        self.assertEqual(len(assisted['records']),600)
        self.assertEqual(assisted['excluded'],[])

    def test_sqlite_schema_foreign_keys_and_row_counts(self):
        with sqlite3.connect(':memory:') as connection:
            connection.executescript(schema_sql())
            for table,columns in COLUMNS.items():
                with (DEFAULT_OUTPUT/f'{table}.csv').open(encoding='utf-8-sig',newline='') as stream:
                    reader=csv.DictReader(stream)
                    self.assertEqual(reader.fieldnames,[c[0] for c in columns])
                    rows=[]
                    for record in reader:
                        row=[]
                        for name,kind,_,_ in columns:
                            value=record[name]
                            row.append(int(value=='TRUE') if kind=='BOOLEAN' else int(value) if kind=='INTEGER' else value)
                        rows.append(row)
                placeholders=','.join('?' for _ in columns)
                connection.executemany(f'INSERT INTO "{table}" VALUES ({placeholders})',rows)
                self.assertEqual(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0],len(self.tables[table]))
            self.assertEqual(connection.execute('PRAGMA foreign_key_check').fetchall(),[])
            self.assertEqual(connection.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("UPDATE QuestionResult SET StudentID='unknown' WHERE rowid=1")

    def test_dashboard_loads_600_without_history(self):
        result=render(1,2,3,.2,.1,.25,.1,'n2-mock','all')
        self.assertEqual(len(result[6]),600)
        self.assertEqual(result[8]['scope'],'independent_answers_same_prior')
        self.assertEqual(result[8]['excluded'],[])
        wrong=render(1,2,3,.2,.1,.25,.1,'n2-mock','wrong')
        self.assertEqual(len(wrong[6]),600-self.manifest['summary']['correct_count'])


if __name__=='__main__':unittest.main()
