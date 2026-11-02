"""ガイドの配分、DB/CSV同値性、集計階層と読み取り専用性の検証。"""
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from sandbox.dashboard.bkt.dashboard_data import filter_records
from sandbox.dashboard.bkt.full_mock_dataset import BLUEPRINT, DATABASE, generate, write_dataset
from sandbox.dashboard.bkt.full_learning_dashboard import (app, full_report, groups, load_full, render, skills)
from sandbox.dashboard.bkt.mock_dataset import COLUMNS


class FullMockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = load_full()

    def test_pdf_blueprint_and_each_session_counts(self):
        # Independent transcription of booklet p.21; do not infer expected quotas from the generator.
        expected = {'言語知識':[5,5,5,7,5,5,12,5,5], '読解':[5,9,2,3,2], '聴解':[5,6,5,12,4]}
        self.assertEqual(len(self.records),1605)
        self.assertEqual(len({r['SkillID'] for r in self.records}),19)
        self.assertEqual(len({r['StudentID'] for r in self.records}),1)
        for session in range(1,16):
            rows = [r for r in self.records if r['SessionNumber']==session]
            self.assertEqual([r['QuestionSequence'] for r in rows],list(range(1,108)))
            for domain,counts in expected.items():
                selected = [r for r in rows if r['CategoryLevel1']==domain]
                self.assertEqual(list(Counter(r['SkillID'] for r in selected).values()),counts)
        self.assertEqual([sum(e[4] for e in BLUEPRINT if e[0]==d) for d in expected],[54,21,32])

    def test_database_integrity_csv_values_and_manifest(self):
        before = DATABASE.read_bytes()
        self.assertEqual(self.records,load_full('csv'))
        manifest = json.loads((DATABASE.parent/'manifest.json').read_text())
        for name,digest in manifest['files_sha256'].items():
            self.assertEqual(hashlib.sha256((DATABASE.parent/name).read_bytes()).hexdigest(),digest,name)
        import csv
        with sqlite3.connect(DATABASE.resolve().as_uri()+'?mode=ro',uri=True) as conn:
            self.assertEqual(conn.execute('PRAGMA integrity_check').fetchone(),('ok',))
            self.assertEqual(conn.execute('PRAGMA foreign_key_check').fetchall(),[])
            for table,columns in COLUMNS.items():
                with (DATABASE.parent/f'csv/{table}.csv').open(encoding='utf-8-sig',newline='') as stream:
                    reader = csv.DictReader(stream)
                    self.assertEqual(reader.fieldnames,[c[0] for c in columns])
                    rows = [tuple(int(r[k]=='TRUE') if t=='BOOLEAN' else int(r[k]) if t=='INTEGER' else r[k] for k,t,_,_ in columns) for r in reader]
                self.assertEqual(conn.execute(f'SELECT * FROM "{table}"').fetchall(),rows)
        self.assertEqual(before,DATABASE.read_bytes())

    def test_generation_matches_fixture_and_protects_existing_files(self):
        first = generate()
        self.assertEqual(first,generate())
        self.assertNotEqual(first['QuestionResult'],generate(seed=123)['QuestionResult'])
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)/'fixture'
            write_dataset(target)
            for file in target.rglob('*'):
                if file.is_file():
                    self.assertEqual(file.read_bytes(),(DATABASE.parent/file.relative_to(target)).read_bytes())
            write_dataset(target)
            marker = target/'csv/Skill.csv'
            marker.write_text('preserve local edit')
            with self.assertRaises(FileExistsError): write_dataset(target)
            self.assertEqual(marker.read_text(),'preserve local edit')

    def test_observation_ranges_and_temporal_order(self):
        tables = generate()
        sessions = {r['SessionID']:r for r in tables['Session']}
        rows = tables['QuestionResult']
        self.assertEqual({r['ConfidenceLevel'] for r in rows},{1,2,3,4})
        self.assertEqual({r['UnderstandingLevel'] for r in rows},{0,1,2,3})
        self.assertTrue(any(r['IsCorrect'] and r['ConfidenceLevel']==4 for r in rows))
        self.assertTrue(any(not r['IsCorrect'] and r['ConfidenceLevel']==1 for r in rows))
        for r in rows:
            session = sessions[r['SessionID']]
            self.assertEqual(r['IsCorrect'],r['UserAnswerDisplayedPosition']==r['CorrectAnswerDisplayedPosition'])
            fields = [r['QuestionPresentedAt'],r['AnsweredAt'],r['ConfidenceRecordedAt'],session['EndAt'],r['ExplanationViewedAt'],r['UnderstandingRecordedAt'],session['ReviewEndAt']]
            self.assertEqual(fields,sorted(fields))
            self.assertEqual(r['ResponseTimeMs'],int((datetime.fromisoformat(r['ConfidenceRecordedAt'])-datetime.fromisoformat(r['QuestionPresentedAt'])).total_seconds())*1000)
        for sid,session in sessions.items():
            self.assertEqual(session['CorrectCount'],sum(r['IsCorrect'] for r in rows if r['SessionID']==sid))

    def test_hierarchical_filters_and_weighted_summary(self):
        records = self.records
        report = full_report(records)
        self.assertEqual([d['Answered'] for d in report['domains']],[810,315,480])
        self.assertAlmostEqual(report['overall']['Accuracy'],sum(r['IsCorrect'] for r in records)/1605)
        self.assertEqual(report['overall']['ModelCount'],1605)
        selected = filter_records(records,domain='読解',group='内容理解')
        self.assertEqual(len(selected),210)
        skill = next(r['SkillID'] for r in selected if r['CategoryLevel3']=='中文')
        selected = filter_records(selected,skill=skill,session=selected[0]['SessionID'])
        self.assertEqual(len(selected),9)
        self.assertEqual({r['CategoryLevel3'] for r in selected},{'中文'})
        self.assertEqual(len(filter_records(records,start='2026-09-07',end='2026-09-13')),321)
        self.assertEqual(filter_records(records,domain='聴解',group='文字・語彙'),[])
        with self.assertRaises(ValueError): filter_records(records,start='2026-10-01',end='2026-09-01')

    def test_ui_options_exports_and_empty_state(self):
        options,_ = groups(self.records,'読解')
        self.assertEqual([r['value'] for r in options],[ '__all__','内容理解','統合理解','主張理解','情報検索'])
        options,_ = skills(self.records,'読解','内容理解')
        self.assertEqual(len(options),3)
        rendered = render(self.records,'読解','内容理解','__all__','__all__',None,None,'accuracy')
        self.assertEqual(rendered[7]['overall']['Answered'],210)
        self.assertEqual(len(rendered[6]),210)
        self.assertTrue(all(r['CategoryLevel1']=='読解' for r in rendered[6]))
        rendered = render(self.records,'聴解','文字・語彙','__all__','__all__',None,None,'understanding')
        self.assertEqual(rendered[6],[])
        self.assertIsNone(rendered[7]['overall']['Accuracy'])
        self.assertIn('条件に合う回答がありません',rendered[8])
        client = app.server.test_client()
        self.assertEqual(client.get('/_dash-layout').status_code,200)
        self.assertEqual(client.get('/_dash-dependencies').status_code,200)


if __name__=='__main__':
    unittest.main()
