import base64
import csv
from io import StringIO
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from alp_app import app, import_uploads, csv_text
from demo_data import sample_records
from dashboard_views import self_report_figure


def encoded_csv(rows):
    return "data:text/csv;base64," + base64.b64encode(csv_text(rows).encode("utf-8")).decode("ascii")


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.client = app.server.test_client()

    def callback(self, output_id, changed, inputs, states=None):
        key = next(key for key in app.callback_map if output_id in key)
        definition = app.callback_map[key]
        outputs = definition["output"]
        multiple = isinstance(outputs, list)
        if not multiple:
            outputs = [outputs]
        output_json = [{"id": item.component_id, "property": item.component_property} for item in outputs]
        payload = {
            "output": key, "outputs": output_json if multiple else output_json[0],
            "inputs": [{**item, "value": inputs.get(item["id"])} for item in definition["inputs"]],
            "state": [{**item, "value": (states or {}).get(item["id"])} for item in definition["state"]],
            "changedPropIds": [changed],
        }
        response = self.client.post('/_dash-update-component', json=payload)
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        return response.get_json()["response"]

    def test_http_layout_and_sample_inference_exports(self):
        for route in ['/', '/_dash-layout', '/_dash-dependencies']:
            self.assertEqual(self.client.get(route).status_code, 200)
        loaded = self.callback('raw-data.data', 'sample-data.n_clicks', {'sample-data': 1})
        raw = loaded['raw-data']['data']
        self.assertEqual(len(raw['records']), 24)
        self.assertEqual(raw['source'], 'demo')
        self.assertIsNone(loaded['csv-upload']['contents'])
        calculated = self.callback('bkt-estimates.data', 'raw-data.data', {
            'raw-data': raw, 'student-filter': '__all__', 'skill-filter': '__all__', 'mode-filter': '__all__',
            'p-l0': 0.2, 'p-t': 0.1, 'p-g': 0.25, 'p-s': 0.1,
        })
        result = calculated['bkt-estimates']['data']
        self.assertEqual(len(result['history']), 24)
        self.assertEqual(len(result['states']), 4)
        self.assertFalse(calculated['export-state']['disabled'])
        self.assertEqual(len(calculated['history-chart']['figure']['data']), 8)
        for trigger, filename, expected in [('export-state', 'KnowledgeState.csv', 4), ('export-history', 'KnowledgeStateHistory.csv', 24), ('export-parameters', 'BKTParameter.csv', 2)]:
            exported = self.callback('bkt-download.data', trigger + '.n_clicks', {trigger: 1}, {'bkt-estimates': result})['bkt-download']['data']
            self.assertEqual(exported['filename'], filename)
            rows = list(csv.DictReader(StringIO(exported['content'].lstrip('\ufeff'))))
            self.assertEqual(len(rows), expected)
            self.assertTrue(all(row['ModelVersion'] == 'bkt-classic-v1' for row in rows))

    def test_invalid_parameters_clear_estimations_and_disable_downloads(self):
        raw = {'records': sample_records()}
        result = self.callback('bkt-estimates.data', 'p-g.value', {
            'raw-data': raw, 'student-filter': '__all__', 'skill-filter': '__all__', 'mode-filter': '__all__',
            'p-l0': 0.2, 'p-t': 0.1, 'p-g': 0.9, 'p-s': 0.9,
        })
        self.assertIsNone(result['bkt-estimates']['data'])
        self.assertEqual(result['state-table']['data'], [])
        self.assertTrue(result['export-history']['disabled'])
        self.assertIn('Guess + Slip', result['model-status']['children'])

    def test_import_errors_clear_previous_data_and_clear_erases_upload(self):
        result = self.callback('raw-data.data', 'import-data.n_clicks', {'import-data': 1}, {
            'csv-upload': None, 'fallback-student': '', 'confirm-single': [],
        })
        self.assertEqual(result['raw-data']['data']['records'], [])
        self.assertIn('取り込めません', result['import-status']['children'])
        result = self.callback('raw-data.data', 'clear-data.n_clicks', {'clear-data': 1})
        self.assertIsNone(result['csv-upload']['contents'])
        self.assertIsNone(result['csv-upload']['filename'])
        self.assertEqual(result['raw-data']['data']['records'], [])

    def test_self_report_zero_is_recorded_and_missing_values_are_not(self):
        figure = self_report_figure([
            {"ConfidenceLevel": "4", "UnderstandingLevel": "0"},
            {"ConfidenceLevel": "", "UnderstandingLevel": None},
        ])
        self.assertEqual(sum(figure.data[0].x), 1)
        self.assertEqual(sum(figure.data[1].x), 1)
        self.assertEqual(figure.data[1].x[0], 1)
        empty = self_report_figure([{"UnderstandingLevel": None}])
        self.assertEqual(len(empty.data), 0)

    def test_upload_identity_deduplication_and_encoding(self):
        row = {**sample_records()[0], 'StudentID': ''}
        content = encoded_csv([row])
        empty = import_uploads([content], ['QuestionResult.csv'])
        self.assertEqual(len(empty['records']), 0)
        self.assertIn('StudentID', empty['excluded'][0]['Reason'])
        result = import_uploads([content, content], ['a.csv', 'b.csv'], 'learner', True)
        self.assertEqual(len(result['records']), 1)
        self.assertEqual(result['records'][0]['StudentID'], 'learner')
        self.assertEqual(len(result['excluded']), 1)
        with self.assertRaises(ValueError):
            import_uploads([content], ['data.csv'], 'learner', False)
        with self.assertRaises(ValueError):
            import_uploads(['data:text/csv;base64,!!!!'], ['data.csv'])


if __name__ == '__main__':
    unittest.main()
