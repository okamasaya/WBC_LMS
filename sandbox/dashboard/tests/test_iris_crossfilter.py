import base64
import numpy as np
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app_1 import app, update_dashboard
from iris_crossfilter import load_iris, selection_from_event, update_selection, filtered_rows, figures


class IrisCrossfilterTests(unittest.TestCase):
    def setUp(self):
        self.frame = load_iris()

    def test_stable_ids_after_filtering_not_curve_or_point_positions(self):
        event = {"points": [{"curveNumber": 0, "pointIndex": 0, "customdata": [51]}]}
        state = update_selection(self.frame, None, "scatter", event, clicked=True)
        rows = filtered_rows(self.frame, "versicolor", state)
        self.assertEqual(rows["sample_no"].tolist(), [51])
        self.assertEqual(rows["species"].tolist(), ["versicolor"])

    def test_multiple_traces_deduplicate_and_filters_intersect(self):
        event = {"points": [{"customdata": [1]}, {"customdata": [2]}, {"customdata": [1]}]}
        state = update_selection(self.frame, None, "line", event)
        self.assertEqual(state["filters"]["line"], [1, 2])
        state = update_selection(self.frame, state, "scatter", {"points": [{"customdata": [2]}, {"customdata": [51]}]})
        self.assertEqual(filtered_rows(self.frame, state=state)["sample_no"].tolist(), [2])
        state = update_selection(self.frame, state, "bar", {"points": [{"customdata": ["versicolor"]}]}, clicked=True)
        self.assertEqual(len(filtered_rows(self.frame, state=state)), 0)

    def test_source_context_remains_available_and_clear_restores(self):
        state = update_selection(self.frame, None, "scatter", {"points": [{"customdata": [1]}]})
        self.assertEqual(len(filtered_rows(self.frame, state=state)), 1)
        self.assertEqual(len(filtered_rows(self.frame, state=state, exclude_source="scatter")), 150)
        plotted = figures(self.frame, "all", state)
        self.assertEqual(sum(len(trace.x) for trace in plotted[0].data), 150)
        self.assertEqual(sum(len(trace.x) for trace in plotted[1].data), 2)
        state = update_selection(self.frame, state, "scatter", clear=True)
        self.assertEqual(len(filtered_rows(self.frame, state=state)), 150)

    def test_species_selection_applies_to_all_four_bar_measurements(self):
        state = update_selection(self.frame, None, "bar", {"points": [{"customdata": ["setosa"]}, {"customdata": ["setosa"]}]})
        self.assertEqual(len(filtered_rows(self.frame, state=state)), 50)
        chart = figures(self.frame, "all", state)[2]
        self.assertEqual(len(chart.data), 4)
        self.assertTrue(all(list(trace.selectedpoints) == [0] for trace in chart.data))
        self.assertEqual(len(chart.data[0].x), 3)

    def test_empty_singleton_and_base_filter_kpis_and_rows(self):
        values = update_dashboard("all", {"filters": {"scatter": []}, "revision": 1})
        self.assertEqual(values[:3], (0, "—", "—"))
        self.assertEqual(values[-1], [])
        values = update_dashboard("all", {"filters": {"scatter": [1]}, "revision": 1})
        self.assertEqual(values[:3], (1, "5.10", "—"))
        self.assertEqual(values[-1][0]["sample_no"], 1)
        self.assertEqual(update_dashboard("setosa")[:3], (50, "5.01", "0.35"))

    def test_repeat_click_reset_and_malformed_events(self):
        event = {"points": [{"customdata": [1]}]}
        state = update_selection(self.frame, None, "scatter", event, clicked=True)
        again = update_selection(self.frame, state, "scatter", event, clicked=True)
        self.assertEqual(again["filters"], {})
        self.assertEqual(update_selection(self.frame, state, reset=True)["filters"], {})
        for event in [None, {}, {"points": [{"customdata": [9999]}]}, {"points": [{"customdata": [1.2]}]}]:
            self.assertIsNone(selection_from_event(self.frame, "scatter", event))
        self.assertEqual(selection_from_event(self.frame, "scatter", {"points": []}), [])


class IrisHTTPTests(unittest.TestCase):
    def callback(self, output_id, changed, values, state=None):
        key = next(key for key in app.callback_map if output_id in key)
        definition = app.callback_map[key]
        outputs = definition["output"]
        payload = {
            "output": key,
            "outputs": [{"id": item.component_id, "property": item.component_property} for item in outputs],
            "inputs": [{**item, "value": values.get(item['id'] + '.' + item['property'])} for item in definition["inputs"]],
            "state": [{**item, "value": state} for item in definition["state"]],
            "changedPropIds": [changed],
        }
        with app.server.test_client() as client:
            response = client.post('/_dash-update-component', json=payload)
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        return response.get_json()["response"]

    def test_http_selection_to_linked_output_and_repeat_reset(self):
        selected = self.callback('iris-selection.data', 'iris-scatter.clickData', {
            'iris-scatter.clickData': {"points": [{"customdata": [51]}]}, 'species-dropdown.value': 'versicolor',
        }, {"filters": {}, "revision": 0})
        state = selected['iris-selection']['data']
        self.assertEqual(state['filters'], {'scatter': [51]})
        self.assertIsNone(selected['iris-scatter']['clickData'])
        rendered = self.callback('kpi-count.children', 'iris-selection.data', {'species-dropdown.value': 'versicolor', 'iris-selection.data': state})
        self.assertEqual(rendered['kpi-count']['children'], 1)
        self.assertEqual(rendered['iris-table']['data'][0]['sample_no'], 51)
        self.assertIsInstance(rendered['iris-scatter']['figure']['data'][0]['customdata'], list)
        self.assertEqual(rendered['iris-scatter']['figure']['data'][0]['customdata'][0], ['51'])
        self.assertEqual(sum(len(trace['x']) if isinstance(trace['x'], list) else len(np.frombuffer(base64.b64decode(trace['x']['bdata']), dtype=trace['x']['dtype'])) for trace in rendered['iris-scatter']['figure']['data']), 50)
        reset = self.callback('iris-selection.data', 'reset-iris.n_clicks', {'reset-iris.n_clicks': 1}, state)
        self.assertEqual(reset['iris-selection']['data']['filters'], {})
        self.assertEqual(reset['species-dropdown']['value'], 'all')

    def test_dropdown_clears_old_selection_and_native_none_does_not_loop(self):
        state = {"filters": {"scatter": [1]}, "revision": 1}
        changed = self.callback('iris-selection.data', 'species-dropdown.value', {'species-dropdown.value': 'virginica'}, state)
        self.assertEqual(changed['iris-selection']['data']['filters'], {})
        ignored = self.callback('iris-selection.data', 'iris-scatter.selectedData', {'iris-scatter.selectedData': None}, state)
        self.assertEqual(ignored, {})


if __name__ == '__main__':
    unittest.main()
