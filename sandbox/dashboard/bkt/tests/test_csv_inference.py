import base64
import copy
import csv
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from sandbox.dashboard.bkt import csv_inference as ingestion
from sandbox.dashboard.bkt.assisted_model import estimate_flat, update_flat
from sandbox.dashboard.bkt.flat_app import app
from sandbox.dashboard.bkt.model import BKTParameters
from sandbox.dashboard.bkt.tests import test_assisted_model as base_http

FIXTURE = Path(__file__).parent / 'fixtures/csv_import'


def files():
    return [(p.name, p.read_text(encoding='utf-8-sig')) for p in sorted(FIXTURE.glob('*.csv'))]


def upload(text):
    return 'data:text/csv;base64,' + base64.b64encode(text.encode('utf-8')).decode()


def question_text(rows):
    stream = StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader(); writer.writerows(rows)
    return stream.getvalue()


class CSVInferenceTests(unittest.TestCase):
    def test_three_exports_deduplicate_and_ignore_summary(self):
        data = ingestion.import_csv_texts(files())
        self.assertEqual((data['input_count'], data['unique_input_count']), (6, 3))
        self.assertEqual(len(data['duplicates']), 3)
        result = ingestion.estimate_import(data)
        self.assertEqual(len(result['records']), 2)
        self.assertEqual(len(result['excluded']), 1)
        self.assertEqual(result['records'][0]['UnderstandingLevel'], 0)
        self.assertFalse(result['records'][0]['UnderstandingMissing'])
        self.assertEqual(result['records'][1]['ConfidenceLevel'], 4)
        self.assertTrue(all(row['StudentID'] == '' for row in result['records']))

    def test_question_and_raw_produce_same_values(self):
        outputs = []
        for name, text in files():
            if name == 'Session.csv':
                continue
            outputs.append(ingestion.estimate_import(ingestion.import_csv_texts([(name, text)]))['records'])
        self.assertEqual(outputs[0], outputs[1])

    def test_all_unanswered_has_no_estimates(self):
        rows = ingestion.import_csv_texts(files())['records']
        for row in rows:
            row.update(IsAnswered='FALSE', IsCorrect='FALSE', ConfidenceLevel='', UnderstandingLevel='')
        result = ingestion.estimate_import(ingestion.import_csv_texts([('test.csv', question_text(rows))]))
        self.assertEqual(result['records'], [])
        self.assertEqual(len(result['excluded']), 3)
        self.assertTrue(all('未回答' in row['Reason'] for row in result['excluded']))

    def test_only_needed_columns_and_no_score_dependency(self):
        rows = ingestion.import_csv_texts(files())['records']
        baseline = ingestion.estimate_import(ingestion.import_csv_texts([('q.csv', question_text(rows))]))
        for row in rows:
            row.update(ScoreRate='not-a-score', QuestionText='unused', Explanation='unused')
        actual = ingestion.estimate_import(ingestion.import_csv_texts([('q.csv', question_text(rows))]))
        self.assertEqual(baseline['records'], actual['records'])
        for row in actual['records']:
            self.assertNotIn('ScoreRate', row)
            self.assertNotIn('Explanation', row)
            self.assertNotIn('QuestionText', row)

    def test_same_id_different_finalized_version_is_rejected(self):
        rows = ingestion.import_csv_texts(files())['records']
        for change in [{'UnderstandingLevel': '3'}, {'ConfidenceLevel': '1'}, {'IsCorrect': 'FALSE'},
                       {'SessionID': 'other'}, {'QuestionID': 'other'}, {'IsAnswered': 'FALSE'}]:
            changed = {**rows[0], **change}
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, '競合'):
                ingestion.import_csv_texts([('q.csv', question_text(rows)), ('updated.csv', question_text([changed]))])

    def test_missing_and_invalid_auxiliary_values_are_explained(self):
        rows = ingestion.import_csv_texts(files())['records']
        rows[0]['UnderstandingLevel'] = ''
        rows[1]['ConfidenceLevel'] = '9'
        result = ingestion.estimate_import(ingestion.import_csv_texts([('q.csv', question_text(rows))]))
        self.assertEqual(len(result['records']), 1)
        self.assertTrue(result['records'][0]['UnderstandingMissing'])
        self.assertEqual(len(result['excluded']), 2)
        self.assertIn('自信度', result['excluded'][0]['Reason'])

    def test_summary_alone_and_invalid_csv_fail(self):
        summary = next(item for item in files() if item[0] == 'Session.csv')
        for items in [[], [summary], [('bad.csv', 'bad\n1')], [('bad.txt', 'text')], [('bad.csv', None)]]:
            with self.subTest(items=items), self.assertRaises(ValueError):
                ingestion.import_csv_texts(items)

    def test_upload_decoding_and_limits(self):
        source = files()
        data = ingestion.import_uploads([upload(text) for _, text in source], [name for name, _ in source])
        self.assertEqual(data['unique_input_count'], 3)
        for contents, names in [(None, None), (['invalid'], ['a.csv']), (['data:,***'], ['a.csv']),
                                (['data:;base64,/w=='], ['a.csv']), ([upload('a')], [])]:
            with self.subTest(contents=contents), self.assertRaises(ValueError):
                ingestion.import_uploads(contents, names)
        with patch.object(ingestion, 'MAX_FILE_BYTES', 8), self.assertRaises(ValueError):
            ingestion.import_uploads(upload('0123456789'), 'q.csv')
        with patch.object(ingestion, 'MAX_FILES', 1), self.assertRaises(ValueError):
            ingestion.import_csv_texts(source)
        with patch.object(ingestion, 'MAX_TOTAL_BYTES', 8), self.assertRaises(ValueError):
            ingestion.import_csv_texts(source)
        with patch.object(ingestion, 'MAX_ROWS', 2), self.assertRaises(ValueError):
            ingestion.import_csv_texts(source)

    def test_same_observation_computation_is_reused_without_state_leak(self):
        rows = [{'ResultID': str(i), 'IsCorrect': True, 'ConfidenceLevel': 2, 'UnderstandingLevel': 0} for i in range(600)]
        original = copy.deepcopy(rows)
        with patch('sandbox.dashboard.bkt.assisted_model.update_flat', wraps=update_flat) as operation:
            first = estimate_flat(rows)
            self.assertEqual(operation.call_count, 1)
            second = estimate_flat(rows, BKTParameters(p_l0=.4))
            self.assertEqual(operation.call_count, 2)
        self.assertNotEqual(first['records'][0]['AssistedAfterLearning'], second['records'][0]['AssistedAfterLearning'])
        self.assertEqual(rows, original)
        first['records'][0]['AssistedAfterLearning'] = -1
        self.assertGreater(first['records'][1]['AssistedAfterLearning'], 0)

    def test_cli_outputs_results_exclusions_and_reproducible_metadata(self):
        with tempfile.TemporaryDirectory() as output:
            result = subprocess.run([sys.executable, '-m', 'sandbox.dashboard.bkt.csv_inference',
                                     *map(str, sorted(FIXTURE.glob('*.csv'))), '--output', output],
                                    cwd=Path(__file__).resolve().parents[4], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            metadata = json.loads((Path(output) / 'inference.json').read_text())
            self.assertEqual(metadata['estimated_count'], 2)
            self.assertEqual(metadata['excluded_count'], 1)
            self.assertEqual(metadata['duplicate_count'], 3)
            self.assertFalse(metadata['score_used'])
            with (Path(output) / 'bkt_assisted_flat_results.csv').open(encoding='utf-8-sig') as f:
                self.assertEqual(len(list(csv.DictReader(f))), 2)


class CSVImportHTTPTests(unittest.TestCase):
    callback = base_http.FlatHTTPTests.callback
    inputs = base_http.FlatHTTPTests.inputs

    def test_upload_render_export_and_clear(self):
        source = files()
        imported = self.callback('flat-uploaded.data', 'flat-import.n_clicks', {
            'flat-import': 1, 'flat-upload.contents': [upload(t) for _, t in source],
            'flat-upload.filename': [n for n, _ in source],
        })
        data = imported['flat-uploaded']['data']
        self.assertEqual(data['unique_input_count'], 3)
        self.assertEqual(imported['flat-dataset']['value'], 'uploaded')
        self.assertIsNone(imported['flat-upload']['contents'])
        rendered = self.callback('flat-analysis.data', 'flat-uploaded.data', self.inputs(**{'flat-dataset':'uploaded','flat-uploaded':data}))
        self.assertEqual(len(rendered['flat-table']['data']), 2)
        self.assertEqual(len(rendered['flat-excluded-table']['data']), 4)
        result = self.callback('flat-download.data', 'flat-export.n_clicks', {'flat-export':1,'flat-analysis':rendered['flat-analysis']['data']})
        self.assertIn('AssistedAfterLearning', result['flat-download']['data']['content'])
        self.assertNotIn('Explanation', result['flat-download']['data']['content'])
        cleared = self.callback('flat-uploaded.data', 'flat-clear-upload.n_clicks', {'flat-clear-upload':1})
        self.assertIsNone(cleared['flat-uploaded']['data'])
        self.assertIsNone(cleared['flat-upload']['contents'])
        failed = self.callback('flat-uploaded.data', 'flat-import.n_clicks', {
            'flat-import': 1, 'flat-upload.contents': [upload('bad')], 'flat-upload.filename': ['bad.csv'],
        })
        self.assertIsNone(failed['flat-uploaded']['data'])
        self.assertIn('前の取込結果はクリア', failed['flat-import-status']['children'])

    def test_zero_answers_clears_estimates_but_exports_reasons(self):
        data = ingestion.import_csv_texts(files())
        for row in data['records']:
            row['IsAnswered'] = 'FALSE'
        rendered = self.callback('flat-analysis.data', 'flat-uploaded.data', self.inputs(**{'flat-dataset':'uploaded','flat-uploaded':data}))
        self.assertEqual(rendered['flat-table']['data'], [])
        self.assertTrue(rendered['flat-export']['disabled'])
        self.assertFalse(rendered['flat-export-excluded']['disabled'])
        self.assertIn('推定対象の回答がありません', rendered['flat-summary']['children'])
        result = self.callback('flat-download.data', 'flat-export-excluded.n_clicks', {'flat-export-excluded':1,'flat-analysis':rendered['flat-analysis']['data']})
        self.assertIn('未回答', result['flat-download']['data']['content'])

    def test_no_upload_does_not_fall_back_to_synthetic_estimates(self):
        rendered = self.callback('flat-analysis.data', 'flat-dataset.value', self.inputs(**{'flat-dataset':'uploaded'}))
        self.assertEqual(rendered['flat-table']['data'], [])
        self.assertTrue(rendered['flat-export']['disabled'])


if __name__ == '__main__':
    unittest.main()
