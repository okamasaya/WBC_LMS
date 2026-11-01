"""時系列集計のルール。表示処理から独立させ、欠損と0を区別する。"""
from pathlib import Path
import pandas as pd

DATA = Path(__file__).resolve().parent / 'data' / 'bike'
FRAMES = {name: pd.read_csv(DATA / f'{name}.csv') for name in ('day', 'hour')}
for frame in FRAMES.values():
    frame['timestamp'] = pd.to_datetime(frame['dteday'])
    if 'hr' in frame:
        frame['timestamp'] += pd.to_timedelta(frame['hr'], unit='h')
MIN_DATE, MAX_DATE = '2011-01-01', '2012-12-31'
WEATHER = {1: '晴れ・薄曇り', 2: '霧・曇り', 3: '小雨・小雪', 4: '強い雨・雪'}
METRICS = {'cnt': '貸出合計', 'casual': '一般利用', 'registered': '登録利用'}
LEVELS = {'M': '月別', 'W': '週別（月曜始まり）', 'D': '日別', 'H': '時間別'}


def bounds(start, end):
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if pd.isna(start) or pd.isna(end) or end < start:
        raise ValueError('開始日と終了日を確認してください。')
    return start.normalize(), end.normalize()


def filter_rows(source, start, end, weather, working):
    start, end = bounds(start, end)
    frame = FRAMES[source]
    mask = frame.timestamp.between(start, end + pd.Timedelta(days=1), inclusive='left')
    mask &= frame.weathersit.isin(weather or [])
    if working != 'all':
        mask &= frame.workingday.eq(int(working))
    return frame.loc[mask].copy()


def bucket(index, level):
    index = pd.DatetimeIndex(index)
    if level == 'H':
        return index.floor('h')
    return index.to_period({'M': 'M', 'W': 'W-SUN', 'D': 'D'}[level]).start_time


def aggregate(frame, start, end, level, metric, statistic):
    """平均の分母は観測行数。欠損・条件で除外した期間を0へ変換しない。"""
    start, end = bounds(start, end)
    index = pd.date_range(start, end + pd.Timedelta(days=1), freq='h' if level == 'H' else 'D', inclusive='left')
    keys = bucket(index, level).unique()
    grouped = frame.groupby(bucket(frame.timestamp, level))[metric]
    values = grouped.sum(min_count=1) if statistic == 'sum' else grouped.mean()
    result = pd.DataFrame({'value': values, 'observations': grouped.size()}).reindex(keys)
    result.index.name = 'period'
    return result


def previous_year(frame, source, start, end, weather, working, metric, statistic):
    """同じ月日で前年を比較。前年にない2/29や未収録の2010年はNaN。"""
    start, end = bounds(start, end)
    current = aggregate(frame, start, end, 'D', metric, statistic)['value']
    prior = filter_rows(source, start - pd.DateOffset(years=1), end - pd.DateOffset(years=1), weather, working)
    prior_daily = aggregate(prior, start - pd.DateOffset(years=1), end - pd.DateOffset(years=1), 'D', metric, statistic)['value']
    aligned = []
    for date in current.index:
        try:
            previous_date = date.replace(year=date.year - 1)
        except ValueError:
            aligned.append(float('nan'))
        else:
            aligned.append(prior_daily.get(previous_date, float('nan')))
    return pd.DataFrame({'今回': current, '前年の同月日': aligned}, index=current.index)


def quality(start, end):
    start, end = bounds(start, end)
    expected = pd.date_range(start, end + pd.Timedelta(days=1), freq='h', inclusive='left')
    present = pd.DatetimeIndex(FRAMES['hour'].timestamp)
    return len(expected.difference(present))


def drill_period(date, level, start, end):
    date = pd.Timestamp(date)
    start, end = bounds(start, end)
    if level == 'M':
        left, right, next_level = date.to_period('M').start_time, date.to_period('M').end_time.normalize(), 'D'
    elif level == 'W':
        left, right, next_level = date, date + pd.Timedelta(days=6), 'D'
    elif level == 'D':
        left = right = date.normalize()
        next_level = 'H'
    else:
        return None
    left, right = max(start, left), min(end, right)
    if right < left:
        return None
    return left.strftime('%Y-%m-%d'), right.strftime('%Y-%m-%d'), next_level
