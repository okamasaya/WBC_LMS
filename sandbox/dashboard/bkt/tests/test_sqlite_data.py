from contextlib import closing
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
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from sandbox.dashboard.bkt import sqlite_data as database
from sandbox.dashboard.bkt.csv_inference import INPUT_FIELDS, estimate_import, import_csv_texts
from sandbox.dashboard.bkt.learning_data import normalize_records, parse_question_csv
from sandbox.dashboard.bkt.model import estimate
from sandbox.dashboard.bkt.mock_dataset import generate
from sandbox.dashboard.bkt.tests import test_assisted_model as http_base

ROOT = Path(__file__).resolve().parents[4]
ARCHIVE = database.ROOT / 'data/prototype_exports/SESS_1793573633671'


def minimal_database(path, rows=None):
    with closing(sqlite3.connect(path)) as connection:
        connection.execute('CREATE TABLE QuestionResult (ResultID TEXT, SessionID TEXT, SkillID TEXT, IsAnswered INTEGER, IsCorrect INTEGER, AnsweredAt TEXT, UnderstandingLevel INTEGER)')
        for index, value in enumerate(rows or []):
            connection.execute('INSERT INTO QuestionResult VALUES (?, ?, ?, ?, ?, ?, ?)', (str(index), 'session', 'skill', 1, 1, '2026-11-02T00:00:00Z', value))
        connection.commit()


class SQLiteDataTests(unittest.TestCase):
    def test_counts_relations_and_observation_ranges(self):
        manifest = json.loads((database.DEFAULT_DB.parent / 'manifest.json').read_text())
        with closing(sqlite3.connect(database.DEFAULT_DB)) as connection:
            self.assertEqual(connection.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(connection.execute('PRAGMA foreign_key_check').fetchall(), [])
            for table, count in manifest['counts'].items():
                self.assertEqual(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0], count)
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM Student').fetchone()[0], 1)
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM Session').fetchone()[0], 5)
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM QuestionResult').fetchone()[0], 150)
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM QuestionResult WHERE IsAnswered=1').fetchone()[0], 150)
            self.assertEqual({r[0] for r in connection.execute('SELECT DISTINCT ConfidenceLevel FROM QuestionResult')}, {1, 2, 3, 4})
            self.assertEqual({r[0] for r in connection.execute('SELECT DISTINCT UnderstandingLevel FROM QuestionResult')}, {0, 1, 2, 3})
        self.assertEqual(hashlib.sha256(database.DEFAULT_DB.read_bytes()).hexdigest(), manifest['database_sha256'])

    def test_both_models_and_generated_values(self):
        data = database.load_database()
        result = estimate_import(data)
        self.assertEqual(result['source'], 'sqlite')
        self.assertEqual(len(result['records']), 150)
        self.assertEqual(result['excluded'], [])
        self.assertEqual(set(data['records'][0]), set(INPUT_FIELDS))
        self.assertIsNone(data['records'][0]['DataSchemaVersion'])
        classic = estimate(normalize_records(data['records'])['records'])
        self.assertEqual(len(classic['history']), 150)
        self.assertEqual(len(classic['states']), 9)
        original, _ = generate(sessions=5)
        for source, row in zip(original['QuestionResult'], data['records']):
            self.assertEqual(source['ResultID'], row['ResultID'])
            for key in ('IsCorrect', 'ConfidenceLevel', 'UnderstandingLevel'):
                self.assertEqual(source[key], row[key])

    def test_reads_and_inference_do_not_modify_database(self):
        before = database.DEFAULT_DB.read_bytes()
        for _ in range(2):
            estimate_import(database.load_database())
        self.assertEqual(before, database.DEFAULT_DB.read_bytes())
        with closing(sqlite3.connect(database.DEFAULT_DB.resolve().as_uri() + '?mode=ro', uri=True)) as connection:
            with self.assertRaises(sqlite3.OperationalError):
                connection.execute('DELETE FROM QuestionResult')
        self.assertFalse(Path(str(database.DEFAULT_DB) + '-wal').exists())

    def test_regeneration_and_existing_file_protection(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'learning_logs.sqlite3'
            manifest = database.write_demo_database(path)
            first = path.read_bytes()
            database.write_demo_database(path)
            self.assertEqual(first, path.read_bytes())
            # 同じSQLiteライブラリではバイト一致も確認。別版では論理内容の一致が基準。
            if manifest['sqlite_version'] == json.loads((database.DEFAULT_DB.parent / 'manifest.json').read_text())['sqlite_version']:
                self.assertEqual(first, database.DEFAULT_DB.read_bytes())
            path.write_bytes(b'user database')
            with self.assertRaises(FileExistsError):
                database.write_demo_database(path)
            self.assertEqual(path.read_bytes(), b'user database')

    def test_missing_bad_or_incompatible_databases_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'test.sqlite3'
            with self.assertRaises(ValueError): database.load_database(path)
            self.assertFalse(path.exists())
            path.write_text('not a database')
            with self.assertRaises(ValueError): database.load_database(path)
            path.unlink()
            with closing(sqlite3.connect(path)) as connection:
                connection.execute('CREATE TABLE Other (id TEXT)')
            with self.assertRaisesRegex(ValueError, 'QuestionResult'): database.load_database(path)
            path.unlink()
            with closing(sqlite3.connect(path)) as connection:
                connection.execute('CREATE TABLE QuestionResult (ResultID TEXT)')
            with self.assertRaisesRegex(ValueError, '必要な列'): database.load_database(path)

    def test_optional_levels_empty_table_and_row_limit(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'test.sqlite3'
            minimal_database(path)
            with self.assertRaisesRegex(ValueError, '回答データ'): database.load_database(path)
            path.unlink(); minimal_database(path, [0, None])
            result = estimate_import(database.load_database(path))
            self.assertEqual(len(result['records']), 2)
            self.assertFalse(result['records'][0]['UnderstandingMissing'])
            self.assertTrue(result['records'][1]['UnderstandingMissing'])
            self.assertTrue(result['records'][0]['ConfidenceMissing'])
            with patch.object(database, 'MAX_ROWS', 1), self.assertRaises(ValueError): database.load_database(path)

    def test_cli_requires_no_dash_or_third_party_packages(self):
        process = subprocess.run([sys.executable, '-S', '-m', 'sandbox.dashboard.bkt.sqlite_data'], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        summary = json.loads(process.stdout)
        self.assertEqual((summary['sessions'], summary['estimated'], summary['excluded']), (5, 150, 0))

    def test_dashboard_selects_sqlite_and_filters_results(self):
        helper = http_base.FlatHTTPTests()
        rendered = helper.callback('flat-analysis.data', 'flat-dataset.value', helper.inputs(**{'flat-dataset':'n2-sqlite'}))
        self.assertEqual(len(rendered['flat-table']['data']), 150)
        self.assertIn('SQLite', rendered['flat-summary']['children'])
        wrong = helper.callback('flat-analysis.data', 'flat-filter.value', helper.inputs(**{'flat-dataset':'n2-sqlite', 'flat-filter':'wrong'}))
        self.assertTrue(all(not row['IsCorrect'] for row in wrong['flat-table']['data']))
        self.assertGreater(len(wrong['flat-table']['data']), 0)
        exported = helper.callback('flat-download.data', 'flat-export.n_clicks', {'flat-export':1, 'flat-analysis':rendered['flat-analysis']['data']})
        rows = list(csv.DictReader(StringIO(exported['flat-download']['data']['content'].lstrip('\ufeff'))))
        self.assertEqual(len(rows), 150)
        self.assertNotIn('ScoreRate', rows[0])

    def test_original_export_archive_matches_manifest(self):
        manifest = json.loads((ARCHIVE / 'manifest.json').read_text())
        self.assertEqual(len(manifest['files']), 3)
        for entry in manifest['files']:
            content = (ARCHIVE / entry['name']).read_bytes()
            self.assertEqual(len(content), entry['bytes'])
            self.assertEqual(hashlib.sha256(content).hexdigest(), entry['sha256'])
        questions = parse_question_csv(next(ARCHIVE.glob('QuestionResult_*.csv')).read_text(encoding='utf-8-sig'))
        raw = parse_question_csv(next(ARCHIVE.glob('CBT_RAW_*.csv')).read_text(encoding='utf-8-sig'))
        self.assertEqual(questions, raw)
        self.assertEqual(len(questions), 10)
        self.assertTrue(all(row['IsAnswered'] == 'FALSE' for row in questions))

    def test_current_csv_table_schema_is_also_readable(self):
        fixture = Path(__file__).parent / 'fixtures/csv_import/QuestionResult.csv'
        data = import_csv_texts([(fixture.name, fixture.read_text(encoding='utf-8-sig'))])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'csv.sqlite3'
            with closing(sqlite3.connect(path)) as connection:
                columns = ', '.join(f'"{key}" TEXT' for key in INPUT_FIELDS)
                connection.execute(f'CREATE TABLE QuestionResult ({columns})')
                connection.executemany('INSERT INTO QuestionResult VALUES (' + ','.join('?' for _ in INPUT_FIELDS) + ')', [tuple(row[key] for key in INPUT_FIELDS) for row in data['records']])
                connection.commit()
            self.assertEqual(estimate_import(data)['records'], estimate_import(database.load_database(path))['records'])


if __name__ == '__main__':
    unittest.main()
