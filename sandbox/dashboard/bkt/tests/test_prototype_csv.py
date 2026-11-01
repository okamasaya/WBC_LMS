import copy
import csv
from datetime import datetime
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from sandbox.dashboard.bkt.prototype_csv import OUTPUT, prototype_payload, write_exports
from sandbox.dashboard.bkt.mock_dataset import generate
from sandbox.dashboard.bkt.learning_data import normalize_records, parse_question_csv
from sandbox.dashboard.bkt.model import estimate
from sandbox.dashboard.bkt.assisted_model import estimate_flat


def rows(content):
    return list(csv.DictReader(StringIO(content.lstrip('\ufeff'))))


class PrototypeCSVTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload=prototype_payload()
        cls.original,_=generate()
        cls.canonical=parse_question_csv((OUTPUT/'QuestionResult.csv').read_text(encoding='utf-8-sig'))

    def test_headers_order_and_original_differences(self):
        for name in ['Session','QuestionResult']:
            expected=[c['header'] for c in self.payload['schema'][name]]
            with (OUTPUT/f'{name}.csv').open(encoding='utf-8-sig',newline='') as f:
                self.assertEqual(csv.DictReader(f).fieldnames,expected)
            with (OUTPUT.parent/f'{name}.csv').open(encoding='utf-8-sig',newline='') as f:
                original=csv.DictReader(f).fieldnames
            self.assertNotEqual(original,expected)
        self.assertEqual(len(self.payload['schema']['Session']),26)
        self.assertEqual(len(self.payload['schema']['QuestionResult']),41)

    def test_600_observations_preserved_via_mapping(self):
        original={r['ResultID']:r for r in self.original['QuestionResult']}
        mapping={r['PrototypeResultID']:r['MockResultID'] for r in rows((OUTPUT/'ResultMapping.csv').read_text(encoding='utf-8-sig'))}
        self.assertEqual(len(self.canonical),600)
        for row in self.canonical:
            source=original[mapping[row['ResultID']]]
            self.assertEqual(row['IsCorrect']=='TRUE',source['IsCorrect'])
            for key in ['ConfidenceLevel','UnderstandingLevel','QuestionID','SkillID','ResponseTimeMs']:
                self.assertEqual(row[key],str(source[key]))
            self.assertEqual(datetime.fromisoformat(row['AnsweredAt'].replace('Z','+00:00')),datetime.fromisoformat(source['AnsweredAt']))
            self.assertEqual(row['DataSchemaVersion'],'2.0.0')
            self.assertNotIn('UnderstandingRecordedAt',row)

    def test_both_models_accept_real_export_schema(self):
        normalized=normalize_records(self.canonical)
        self.assertEqual(len(normalized['records']),600)
        self.assertEqual(normalized['excluded'],[])
        result=estimate(normalized['records'])
        self.assertEqual(len(result['history']),600)
        self.assertEqual(len(result['states']),9)
        assisted=estimate_flat(self.canonical)
        self.assertEqual(len(assisted['records']),600)
        self.assertEqual(assisted['excluded'],[])

    def test_three_files_and_ai_report_use_one_snapshot(self):
        sample=self.payload['sessions'][0]
        question_rows=rows(sample['exports']['questions']['content'])
        raw_rows=parse_question_csv(sample['exports']['raw']['content'])
        self.assertEqual(question_rows,raw_rows)
        session=rows(sample['exports']['session']['content'])[0]
        self.assertEqual(session['SessionID'],question_rows[0]['SessionID'])
        self.assertEqual(int(session['CorrectCount']),sum(row['IsCorrect']=='TRUE' for row in question_rows))
        analysis=json.loads(sample['report'].split('=== AI_ANALYSIS_DATA_JSON ===\n')[1])
        self.assertEqual(analysis['session']['sessionId'],session['SessionID'])
        for report,row in zip(analysis['questions'],question_rows):
            self.assertEqual(report['correct'],row['IsCorrect']=='TRUE')
            self.assertEqual(report['confidence'],f"{row['ConfidenceLevel']} ({row['ConfidenceLabel']})")
            self.assertEqual(report['explanationUnderstanding'],f"{row['UnderstandingLevel']} ({row['UnderstandingLabel']})")

    def test_default_anonymous_exports_require_explicit_identity(self):
        payload=prototype_payload('anonymous')
        raw=parse_question_csv(payload['sessions'][0]['exports']['questions']['content'])
        self.assertTrue(all(row['StudentID']=='' for row in raw))
        self.assertEqual(normalize_records(raw)['records'],[])
        with self.assertRaises(ValueError):normalize_records(raw,'fixture-learner')
        confirmed=normalize_records(raw,'fixture-learner',True)
        self.assertEqual(len(confirmed['records']),30)
        self.assertEqual(len(estimate_flat(raw)['records']),30)

    def test_missing_unanswered_and_refinalization(self):
        tables=copy.deepcopy(self.original)
        tables['Session']=tables['Session'][:1];tables['QuestionResult']=tables['QuestionResult'][:3]
        tables['QuestionResult'][0]['ConfidenceLevel']=None
        tables['QuestionResult'][0]['UnderstandingLevel']=None
        tables['QuestionResult'][1]['UnderstandingLevel']=0
        tables['QuestionResult'][1]['UnderstandingLabel']='全然分からない'
        tables['QuestionResult'][2]['IsAnswered']=False
        payload=prototype_payload(tables=tables)
        raw=parse_question_csv(payload['sessions'][0]['exports']['questions']['content'])
        self.assertEqual(raw[0]['ConfidenceLevel'],'')
        self.assertEqual(raw[0]['UnderstandingLevel'],'')
        self.assertEqual(raw[0]['UnderstandingLabel'],'未入力')
        self.assertEqual(raw[1]['UnderstandingLevel'],'0')
        self.assertEqual(raw[2]['AnsweredAt'],'')
        flat=estimate_flat(raw)
        self.assertEqual(len(flat['records']),2)
        self.assertTrue(flat['records'][0]['UnderstandingMissing'])
        self.assertFalse(flat['records'][1]['UnderstandingMissing'])
        updated={**raw[1],'UnderstandingLevel':'3'}
        with self.assertRaises(ValueError):estimate_flat([raw[1],updated])

    def test_deterministic_generation_and_committed_files(self):
        with tempfile.TemporaryDirectory() as temp:
            write_exports(temp)
            snapshots={str(p.relative_to(temp)):p.read_bytes() for p in Path(temp).rglob('*') if p.is_file()}
            write_exports(temp)
            for name,content in snapshots.items():
                self.assertEqual(content,(Path(temp)/name).read_bytes())
                self.assertEqual(content,(OUTPUT/name).read_bytes())

    def test_summary_csv_is_not_a_question_input(self):
        with self.assertRaises(ValueError):
            parse_question_csv(self.payload['sessions'][0]['exports']['session']['content'])


if __name__=='__main__':unittest.main()
