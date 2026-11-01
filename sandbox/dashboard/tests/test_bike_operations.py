from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bike_data_service import BikeDataService, DATA
import sample_dsbd_bike as app_module


class BikeOperationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        for name in ('day', 'hour'):
            shutil.copy2(DATA / f'{name}.csv', self.folder / f'{name}.csv')
        self.service = BikeDataService(self.folder, self.folder / 'bike.sqlite3', cache_size=2, snapshot_size=2)

    def tearDown(self):
        self.temp.cleanup()

    def test_reload_same_content_keeps_version(self):
        first, second = self.service.reload(), self.service.reload()
        self.assertEqual(first['version'], second['version'])
        self.assertEqual(len(self.service.frames(first)['hour']), 17379)

    def test_sqlite_real_read_and_update(self):
        token = self.service.reload('sqlite')
        self.assertEqual(self.service.frames(token)['day'].cnt.sum(), 3292679)
        with sqlite3.connect(self.service.database) as conn:
            for name in ('day', 'hour'):
                conn.execute(f'UPDATE "{name}" SET cnt=cnt+1, casual=casual+1 WHERE instant=1')
        updated = self.service.reload('sqlite')
        self.assertNotEqual(token['version'], updated['version'])
        self.assertEqual(self.service.frames(updated)['day'].cnt.sum(), 3292680)
        self.assertEqual(self.service.frames(token)['day'].cnt.sum(), 3292679)

    def test_invalid_reload_retains_prior_snapshot(self):
        token = self.service.reload()
        (self.folder / 'day.csv').write_text('broken\n1\n')
        with self.assertRaises(ValueError):
            self.service.reload()
        self.assertEqual(len(self.service.frames(token)['day']), 731)

    def test_inconsistent_db_counts_rejected(self):
        token = self.service.reload('sqlite')
        with sqlite3.connect(self.service.database) as conn:
            conn.execute('UPDATE day SET cnt=cnt+1 WHERE instant=1')
        with self.assertRaises(ValueError):
            self.service.reload('sqlite')
        self.assertEqual(self.service.frames(token)['day'].cnt.sum(), 3292679)

    def test_cache_hit_copy_and_lru_limit(self):
        original = self.service.cached('a', lambda: {'rows': [1]})
        original['rows'].append(2)
        repeated = self.service.cached('a', lambda: self.fail('cache was not used'))
        self.assertEqual(repeated, {'rows': [1]})
        self.assertEqual(self.service.hits, 1)
        self.service.cached('b', lambda: 2)
        self.service.cached('c', lambda: 3)
        self.assertNotIn('a', self.service.cache)
        self.assertEqual(len(self.service.cache), 2)

    def test_version_changes_invalidate_aggregate_cache(self):
        with patch.object(app_module, 'SERVICE', self.service):
            token = self.service.reload('sqlite')
            args = ('day','2011-01-01','2011-01-01',[1,2,3,4],'all','D','cnt','sum')
            first = app_module.render(*args, data_token=token)
            again = app_module.render(*args, data_token=token)
            self.assertEqual(first[0], again[0])
            self.assertEqual(self.service.hits, 1)
            with sqlite3.connect(self.service.database) as conn:
                for name in ('day','hour'):
                    conn.execute(f'UPDATE "{name}" SET cnt=cnt+1, casual=casual+1 WHERE instant=1')
            updated = self.service.reload('sqlite')
            self.assertNotEqual(first[0], app_module.render(*args, data_token=updated)[0])
            # CSV uses the displayed version, even after a newer refresh.
            self.assertIn(',985\n', app_module.export(1,*args[:5],args[5],data_token=token)['content'])

    def test_server_sort_page_and_out_of_range_page(self):
        rows = [{'instant': index, 'cnt': index * 2} for index in range(1, 32)]
        page, count, index = app_module.page_rows(rows, 1, 15, [{'column_id':'cnt','direction':'desc'}])
        self.assertEqual(count, 3)
        self.assertEqual(index, 1)
        self.assertEqual(page[0]['instant'], 16)
        self.assertEqual(len(page), 15)
        page, count, index = app_module.page_rows(rows, 99, 15, [])
        self.assertEqual(index, 2)
        self.assertEqual(len(page), 1)

    def test_refresh_http_failure_retains_browser_token(self):
        with patch.object(app_module, 'SERVICE', self.service):
            key = next(key for key in app_module.app.callback_map if 'bike-refresh-status.children' in key)
            definition = app_module.app.callback_map[key]
            def request():
                payload = {'output': key,
                    'outputs': [{'id': item.component_id, 'property': item.component_property} for item in definition['output']],
                    'inputs': [{**item, 'value': 'sqlite' if item['id'] == 'bike-backend' else 1} for item in definition['inputs']],
                    'state': [], 'changedPropIds': ['bike-refresh.n_clicks']}
                with app_module.app.server.test_client() as client:
                    response = client.post('/_dash-update-component', json=payload)
                self.assertEqual(response.status_code, 200)
                return response.get_json()['response']
            good = request()
            self.assertEqual(good['bike-data']['data']['backend'], 'sqlite')
            with sqlite3.connect(self.service.database) as conn:
                conn.execute('UPDATE day SET cnt=-1 WHERE instant=1')
            failed = request()
            self.assertNotIn('bike-data', failed)
            self.assertIn('前回のデータを保持', failed['bike-refresh-status']['children'])

    def test_snapshot_expiry_is_explicit(self):
        first = self.service.reload('sqlite')
        for _ in range(2):
            with sqlite3.connect(self.service.database) as conn:
                for name in ('day','hour'):
                    conn.execute(f'UPDATE "{name}" SET cnt=cnt+1, casual=casual+1 WHERE instant=1')
            self.service.reload('sqlite')
        with self.assertRaisesRegex(ValueError, '保存期限'):
            self.service.frames(first)
        with patch.object(app_module, 'SERVICE', self.service):
            _, message = app_module.download_data(1, 'day', '2012-01-01', '2012-12-31', [1,2,3,4], 'all', 'M', first)
            self.assertIn('再読込', message)

    def test_automatic_refresh_toggle_and_expired_token(self):
        self.assertTrue(app_module.toggle_refresh([]))
        self.assertFalse(app_module.toggle_refresh(['auto']))
        with self.assertRaises(ValueError):
            self.service.frames({'version':'expired'})


if __name__ == '__main__':
    unittest.main()
