"""共有URLの境界値と描画の一致を確認する。"""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from iris_view_state import encode_view, decode_view, validate_view
from sample_dsbd_iris import update_dashboard, export_csv


class ViewStateTests(unittest.TestCase):
    def view(self, **changes):
        return {'version': 1, 'species': 'all', 'x': 'petal_length', 'y': 'petal_width', 'filters': {}, **changes}

    def test_roundtrip_and_deduplication(self):
        query = encode_view('setosa', 'petal_length', 'petal_width', {'filters': {'scatter': [2, 1, 2], 'bar': ['setosa']}})
        self.assertEqual(decode_view(query), {key: val for key, val in self.view(species='setosa', filters={'scatter': [1, 2], 'bar': ['setosa']}).items() if key != 'version'})

    def test_empty_selection_survives_sharing(self):
        result = decode_view(encode_view('all', 'petal_length', 'petal_width', {'filters': {'scatter': []}}))
        self.assertEqual(result['filters'], {'scatter': []})
        self.assertEqual(update_dashboard('all', {'filters': result['filters']})[0], 0)

    def test_malformed_unknown_duplicate_and_oversized_queries(self):
        for query in ['', '?view=bad', '?view=%5B%5D', '?view={}&view={}', '?' + 'a' * 12000]:
            with self.subTest(query=query[:40]), self.assertRaises(ValueError):
                decode_view(query)

    def test_invalid_species_axes_version_and_source(self):
        for changes in [{'version': 2}, {'species': 'unknown'}, {'x': 'cnt'}, {'y': None}, {'filters': {'unknown': []}}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_view(self.view(**changes))

    def test_invalid_ids_and_filter_types(self):
        for filters in [[], {'scatter': [0]}, {'scatter': [151]}, {'scatter': [True]}, {'scatter': ['1']}, {'scatter': [1.5]}, {'bar': ['unknown']}, {'bar': 'setosa'}]:
            with self.subTest(filters=filters), self.assertRaises(ValueError):
                validate_view(self.view(filters=filters))

    def test_restored_rows_match_kpi_and_csv(self):
        view = decode_view(encode_view('setosa', 'petal_length', 'petal_width', {'filters': {'scatter': [1, 51]}}))
        state = {'filters': view['filters']}
        result = update_dashboard(view['species'], state, view['x'], view['y'])
        self.assertEqual(result[:3], (1, '1.40', '—'))
        self.assertEqual(result[-1][0]['sample_no'], 1)
        self.assertEqual(len(export_csv(1, view['species'], state)['content'].strip().splitlines()), 2)


if __name__ == '__main__':
    unittest.main()
