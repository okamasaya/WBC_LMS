from pathlib import Path
import sys
import unittest
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bike_timeseries import FRAMES, filter_rows, aggregate, previous_year, quality, drill_period
from sample_dsbd_bike import render, export

ALL = [1, 2, 3, 4]


class BikeTimeSeriesTests(unittest.TestCase):
    def test_source_totals_and_component_counts(self):
        for frame in FRAMES.values():
            self.assertTrue((frame.casual + frame.registered == frame.cnt).all())
        hourly = FRAMES['hour'].groupby('dteday').cnt.sum()
        daily = FRAMES['day'].set_index('dteday').cnt
        self.assertEqual(hourly.to_dict(), daily.to_dict())
        self.assertEqual(int(daily.sum()), 3292679)

    def test_month_week_and_day_totals_preserved(self):
        frame = filter_rows('day', '2012-01-01', '2012-12-31', ALL, 'all')
        for level, count in [('M', 12), ('D', 366), ('W', 54)]:
            result = aggregate(frame, '2012-01-01', '2012-12-31', level, 'cnt', 'sum')
            self.assertEqual(len(result), count)
            self.assertEqual(result.value.sum(), 2049576)
        weekly = aggregate(frame, '2012-01-01', '2012-12-31', 'W', 'cnt', 'sum')
        self.assertTrue(all(date.weekday() == 0 for date in weekly.index))

    def test_mean_uses_observed_rows(self):
        frame = filter_rows('hour', '2012-01-01', '2012-01-31', ALL, '1')
        result = aggregate(frame, '2012-01-01', '2012-01-31', 'M', 'registered', 'mean')
        self.assertAlmostEqual(result.value.iloc[0], frame.registered.sum() / len(frame))
        self.assertEqual(result.observations.iloc[0], len(frame))

    def test_missing_is_not_zero(self):
        frame = pd.DataFrame({'timestamp': pd.to_datetime(['2012-01-01', '2012-01-03']), 'cnt': [0, 10]})
        result = aggregate(frame, '2012-01-01', '2012-01-03', 'D', 'cnt', 'sum')
        self.assertEqual(result.value.iloc[0], 0)
        self.assertEqual(result.observations.iloc[0], 1)
        self.assertTrue(pd.isna(result.value.iloc[1]))
        self.assertTrue(pd.isna(result.observations.iloc[1]))
        self.assertEqual(result.value.iloc[2], 10)

    def test_previous_same_day_and_leap_gap(self):
        frame = filter_rows('day', '2012-02-28', '2012-03-01', ALL, 'all')
        result = previous_year(frame, 'day', '2012-02-28', '2012-03-01', ALL, 'all', 'cnt', 'sum')
        expected = FRAMES['day'].set_index('dteday').cnt
        self.assertEqual(result['前年の同月日'].iloc[0], expected['2011-02-28'])
        self.assertTrue(pd.isna(result['前年の同月日'].iloc[1]))
        self.assertEqual(result['前年の同月日'].iloc[2], expected['2011-03-01'])

    def test_unavailable_previous_year_and_filtered_comparison(self):
        frame = filter_rows('day', '2011-01-01', '2011-01-31', ALL, 'all')
        result = previous_year(frame, 'day', '2011-01-01', '2011-01-31', ALL, 'all', 'cnt', 'sum')
        self.assertTrue(result['前年の同月日'].isna().all())
        frame = filter_rows('day', '2012-01-01', '2012-01-31', [1], '1')
        result = previous_year(frame, 'day', '2012-01-01', '2012-01-31', [1], '1', 'cnt', 'sum')
        reference = filter_rows('day', '2011-01-01', '2011-01-31', [1], '1').set_index('dteday').cnt
        for date, value in result['前年の同月日'].items():
            key = date.replace(year=2011).strftime('%Y-%m-%d')
            if key in reference:
                self.assertEqual(value, reference[key])
            else:
                self.assertTrue(pd.isna(value))

    def test_missing_slots_and_empty_filters(self):
        self.assertEqual(quality('2011-01-01', '2012-12-31'), 165)
        self.assertEqual(quality('2012-01-01', '2012-12-31'), 50)
        empty = filter_rows('day', '2012-01-01', '2012-12-31', [], 'all')
        self.assertTrue(aggregate(empty, '2012-01-01', '2012-12-31', 'M', 'cnt', 'sum').value.isna().all())

    def test_drill_limits_and_leap_month(self):
        self.assertEqual(drill_period('2012-02-01', 'M', '2012-02-10', '2012-03-01'), ('2012-02-10', '2012-02-29', 'D'))
        self.assertEqual(drill_period('2012-02-29', 'D', '2012-02-10', '2012-03-01'), ('2012-02-29', '2012-02-29', 'H'))
        self.assertIsNone(drill_period('2012-02-29', 'H', '2012-02-29', '2012-02-29'))

    def test_rolling_mean_and_reference_line(self):
        result = render('day', '2012-01-01', '2012-01-31', ALL, 'all', 'D', 'cnt', 'sum')
        rolling = result[4].data[1].y
        self.assertTrue(all(pd.isna(value) for value in rolling[:6]))
        expected = FRAMES['day'].set_index('dteday').loc['2012-01-01':'2012-01-07'].cnt.sum() / 7
        self.assertAlmostEqual(rolling[6], expected)
        self.assertEqual(len(result[4].layout.shapes), 1)

    def test_invalid_period_empty_render_and_hour_export(self):
        self.assertEqual(render('day','2012-02-01','2012-01-01',ALL,'all','M','cnt','sum')[-2:], ([], []))
        self.assertIn('抽出 0行', render('day','2012-01-01','2012-01-31',[],'all','M','cnt','sum')[0])
        data = export(1,'day','2012-01-01','2012-01-01',ALL,'all','H')['content']
        expected = len(filter_rows('hour','2012-01-01','2012-01-01',ALL,'all'))
        self.assertEqual(len(data.strip().splitlines()), expected + 1)
        self.assertIn(',hr,', data.splitlines()[0])


if __name__ == '__main__':
    unittest.main()
