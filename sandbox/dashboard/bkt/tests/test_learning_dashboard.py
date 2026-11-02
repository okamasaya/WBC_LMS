import copy
import csv
import hashlib
from io import StringIO
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from sandbox.dashboard.bkt.dashboard_data import (CSV_BACKUP, build_report, export_csv_backup,
    filter_records, load_learning_data, summarize)
from sandbox.dashboard.bkt.learning_dashboard import app
from sandbox.dashboard.bkt.mock_dataset import COLUMNS
from sandbox.dashboard.bkt.sqlite_data import DEFAULT_DB

ROOT = Path(__file__).resolve().parents[4]


class LearningDataTests(unittest.TestCase):
    def setUp(self):
        self.records = load_learning_data()

    def test_overall_numbers_and_distinct_meanings(self):
        result = build_report(self.records)
        overall = result['overall']
        self.assertEqual((overall['Answered'], overall['Correct'], overall['Sessions']), (150, 81, 5))
        self.assertAlmostEqual(overall['Accuracy'], .54)
        self.assertAlmostEqual(overall['Understanding'], 1.94)
        self.assertAlmostEqual(overall['AverageSeconds'], 37.18)
        self.assertEqual(overall['ModelCount'], 150)
        self.assertEqual(overall['ConfidentWrong'], 21)
        self.assertNotEqual(overall['ModelMean'], overall['Accuracy'])
        self.assertEqual(result['scope'], 'independent_answers_same_prior')
        self.assertEqual(result['excluded'], [])

    def test_groups_and_weighted_accuracy(self):
        result = build_report(self.records)
        self.assertEqual((len(result['skills']), len(result['sessions'])), (9, 5))
        self.assertEqual(sum(g['Answered'] for g in result['skills']), 150)
        self.assertTrue(all(g['Answered'] == 30 for g in result['sessions']))
        rows = copy.deepcopy(self.records[:4])
        for index, row in enumerate(rows):
            row['SkillID'] = 'a' if index == 0 else 'b'
            row['IsCorrect'] = index == 0
        result = build_report(rows)
        self.assertEqual(result['overall']['Accuracy'], .25)
        self.assertEqual(sum(r['Accuracy'] for r in result['skills']) / 2, .5)

    def test_zero_missing_invalid_and_unanswered(self):
        rows = copy.deepcopy(self.records[:3])
        rows[0].update(UnderstandingLevel=0, ConfidenceLevel=9, IsAnswered=True, IsCorrect=True)
        rows[1].update(UnderstandingLevel=None, ConfidenceLevel=None, IsAnswered=True, IsCorrect=False)
        rows[2].update(IsAnswered=False)
        result = summarize(rows)
        self.assertEqual(result['Answered'], 2)
        self.assertEqual(result['Accuracy'], .5)  # 補助値が不正でも有効な正誤の分母から落とさない。
        self.assertEqual(result['Understanding'], 0)
        self.assertEqual(result['UnderstandingCount'], 1)
        self.assertEqual(result['UnderstandingUnavailable'], 1)
        self.assertEqual(result['Unanswered'], 1)
        self.assertEqual(result['ModelCount'], 1)
        self.assertEqual(result['ModelExcluded'], 2)
        for row in rows: row['IsAnswered'] = False
        empty = summarize(rows)
        self.assertIsNone(empty['Accuracy'])
        self.assertIsNone(empty['Understanding'])
        self.assertIsNone(empty['ModelMean'])

    def test_period_skill_student_filters_and_empty(self):
        selected = filter_records(self.records, start='2026-09-07', end='2026-09-13')
        self.assertEqual(len(selected), 90)
        skill = self.records[0]['SkillID']
        selected = filter_records(selected, skill=skill)
        self.assertTrue(all(r['SkillID'] == skill for r in selected))
        self.assertEqual(build_report(selected)['overall']['Sessions'], 3)
        self.assertEqual(filter_records(self.records, student='not-present'), [])
        self.assertEqual(build_report([])['sessions'], [])
        with self.assertRaises(ValueError): filter_records(self.records, start='2026-10-01', end='2026-09-01')

    def test_sqlite_csv_parity_and_read_only_database(self):
        original = DEFAULT_DB.read_bytes()
        self.assertEqual(self.records, load_learning_data('csv'))
        self.assertEqual(build_report(self.records), build_report(load_learning_data('csv')))
        self.assertEqual(original, DEFAULT_DB.read_bytes())
        manifest = json.loads((CSV_BACKUP / 'manifest.json').read_text())
        self.assertEqual(hashlib.sha256(original).hexdigest(), manifest['source_database_sha256'])
        with sqlite3.connect(DEFAULT_DB.resolve().as_uri() + '?mode=ro', uri=True) as connection:
            for table, columns in COLUMNS.items():
                with (CSV_BACKUP / f'{table}.csv').open(encoding='utf-8-sig', newline='') as stream:
                    reader = csv.DictReader(stream)
                    self.assertEqual(reader.fieldnames, [c[0] for c in columns])
                    csv_rows = [tuple(int(r[k] == 'TRUE') if t == 'BOOLEAN' else int(r[k]) if t == 'INTEGER' else r[k] for k,t,_,_ in columns) for r in reader]
                self.assertEqual(connection.execute(f'SELECT * FROM "{table}"').fetchall(), csv_rows)

    def test_backup_generation_is_reproducible_and_protects_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            export_csv_backup(output=output)
            for name in ('Student','Skill','Question','Session','QuestionResult'):
                self.assertEqual((output / f'{name}.csv').read_bytes(), (CSV_BACKUP / f'{name}.csv').read_bytes())
            export_csv_backup(output=output)
            (output / 'Student.csv').write_text('user change')
            with self.assertRaises(FileExistsError): export_csv_backup(output=output)
            self.assertEqual((output / 'Student.csv').read_text(), 'user change')

    def test_bad_sources_do_not_fall_back_silently(self):
        with self.assertRaises(ValueError): load_learning_data('unknown')
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError): load_learning_data('csv', csv_folder=temp)
            path = Path(temp) / 'missing.sqlite3'
            with self.assertRaises(ValueError): load_learning_data(database=path)
            self.assertFalse(path.exists())


class LearningHTTPTests(unittest.TestCase):
    def callback(self, contains, changed, values):
        key = next(k for k in app.callback_map if contains in k)
        definition = app.callback_map[key]
        outputs = definition['output']; multiple = isinstance(outputs, list)
        items = outputs if multiple else [outputs]
        output_json = [{'id':o.component_id,'property':o.component_property} for o in items]
        def entries(items):
            return [{**item,'value':values.get(item['id']+'.'+item['property'],values.get(item['id']))} for item in items]
        payload = {'output':key,'outputs':output_json if multiple else output_json[0],
                   'inputs':entries(definition['inputs']),'state':entries(definition['state']),'changedPropIds':[changed]}
        with app.server.test_client() as client:
            response = client.post('/_dash-update-component',json=payload)
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        return response.get_json()['response']

    def values(self, **extra):
        records = load_learning_data()
        return {'learning-data':records,'learning-student':records[0]['StudentID'],
                'learning-skill':'__all__','learning-period.start_date':'2026-09-01',
                'learning-period.end_date':'2026-09-13','learning-trend-metric':'understanding',**extra}

    def test_layout_source_and_initial_dashboard(self):
        with app.server.test_client() as client:
            for path in ('/','/_dash-layout','/_dash-dependencies','/assets/learning.css'):
                with client.get(path) as response:
                    self.assertEqual(response.status_code, 200)
        loaded = self.callback('learning-data.data', 'learning-source.value', {'learning-source':'sqlite'})
        self.assertEqual(len(loaded['learning-data']['data']), 150)
        self.assertEqual(len(loaded['learning-skill']['options']), 10)
        rendered = self.callback('learning-report.data', 'learning-data.data', self.values())
        self.assertEqual(len(rendered['learning-kpis']['children']), 5)
        self.assertEqual(len(rendered['learning-history']['data']), 5)
        self.assertEqual(len(rendered['learning-skill-table']['data']), 9)
        self.assertEqual(len(rendered['learning-category-chart']['figure']['data']), 3)
        self.assertEqual(rendered['learning-trend-chart']['figure']['layout']['yaxis']['range'], [0,3])

    def test_chart_selection_period_and_metric_link(self):
        skill = load_learning_data()[0]['SkillID']
        selected = self.callback('learning-skill.value@', 'learning-category-chart.clickData', {'learning-category-chart':{'points':[{'customdata':[skill]}]}})
        self.assertEqual(selected['learning-skill']['value'], skill)
        rendered = self.callback('learning-report.data', 'learning-skill.value', self.values(**{'learning-skill':skill,'learning-period.start_date':'2026-09-07','learning-trend-metric':'model'}))
        self.assertEqual(len(rendered['learning-skill-table']['data']), 1)
        self.assertEqual(len(rendered['learning-history']['data']), 3)
        self.assertEqual(rendered['learning-trend-chart']['figure']['layout']['yaxis']['range'], [0,1])
        reset = self.callback('learning-skill.value@', 'learning-reset.n_clicks', {'learning-reset':1})
        self.assertEqual(reset['learning-skill']['value'], '__all__')

    def test_csv_downloads_respect_filter_and_include_model_context(self):
        skill = load_learning_data()[0]['SkillID']
        rendered = self.callback('learning-report.data', 'learning-skill.value', self.values(**{'learning-skill':skill}))
        report = rendered['learning-report']['data']
        for button,key in [('learning-export-skills','skills'),('learning-export-history','sessions'),('learning-export-details','details')]:
            output = self.callback('learning-download.data',button+'.n_clicks',{button:1,'learning-report':report})
            rows = list(csv.DictReader(StringIO(output['learning-download']['data']['content'].lstrip('\ufeff'))))
            self.assertEqual(len(rows),len(report[key]))
        output = self.callback('learning-download.data','learning-export-model.n_clicks',{'learning-export-model':1,'learning-report':report})
        assumptions = json.loads(output['learning-download']['data']['content'])
        self.assertEqual(assumptions['scope'], 'independent_answers_same_prior')
        self.assertEqual(assumptions['filters']['skill'],skill)

    def test_empty_conditions_and_failed_source_clear_previous_results(self):
        empty = self.callback('learning-report.data','learning-period.start_date',self.values(**{'learning-period.start_date':'2027-01-01','learning-period.end_date':'2027-12-31'}))
        self.assertEqual(empty['learning-details']['data'],[])
        self.assertEqual(empty['learning-report']['data']['overall']['Answered'],0)
        invalid = self.callback('learning-report.data','learning-period.start_date',self.values(**{'learning-period.start_date':'2027-01-01'}))
        self.assertIsNone(invalid['learning-report']['data'])
        failed = self.callback('learning-data.data','learning-source.value',{'learning-source':'unknown'})
        self.assertEqual(failed['learning-data']['data'],[])


class LearningLaunchTests(unittest.TestCase):
    def test_module_launch_from_repository_or_dashboard_folder(self):
        for folder,module in [(ROOT,'sandbox.dashboard.bkt.learning_dashboard'),(ROOT/'sandbox/dashboard','bkt.learning_dashboard')]:
            process = subprocess.run([sys.executable,'-m',module,'--help'],cwd=folder,capture_output=True,text=True)
            self.assertEqual(process.returncode,0,process.stderr)
            self.assertIn('--port',process.stdout)


if __name__ == '__main__':
    unittest.main()
