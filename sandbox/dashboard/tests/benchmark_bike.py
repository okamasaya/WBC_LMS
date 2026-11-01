"""合成100万行で集計関数を測定。CSV読込やブラウザの負荷試験ではない。

python sandbox/dashboard/tests/benchmark_bike.py --rows 1000000
"""
from pathlib import Path
import argparse
import json
import platform
import sys
from time import perf_counter
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bike_timeseries import FRAMES, aggregate
from bike_data_service import BikeDataService


def benchmark(rows):
    base = FRAMES['hour'][['timestamp', 'cnt']]
    frame = pd.concat([base] * ((rows + len(base) - 1) // len(base)), ignore_index=True).iloc[:rows]
    total = int(frame.cnt.sum())
    measured = {}
    for level in ['M','W','D','H']:
        before = perf_counter()
        result = aggregate(frame, '2011-01-01', '2012-12-31', level, 'cnt', 'sum')
        measured[level] = {'milliseconds': round((perf_counter() - before) * 1000, 3), 'buckets': len(result)}
        assert int(result.value.sum()) == total
    service = BikeDataService()
    before = perf_counter()
    first = service.cached('million-months', lambda: aggregate(frame,'2011-01-01','2012-12-31','M','cnt','sum'))
    cold_ms = (perf_counter() - before) * 1000
    before = perf_counter()
    second = service.cached('million-months', lambda: (_ for _ in ()).throw(AssertionError('cache miss')))
    hit_ms = (perf_counter() - before) * 1000
    pd.testing.assert_frame_equal(first, second)
    assert service.hits == 1 and service.misses == 1
    return {'rows': rows, 'synthetic': True, 'scope': 'aggregation functions only; repeated hourly observations, not a validated production dataset', 'python': platform.python_version(), 'pandas': pd.__version__, 'total': total, 'measurements': measured, 'cache': {'cold_ms':round(cold_ms,3), 'hit_ms':round(hit_ms,3), 'hits':service.hits, 'misses':service.misses}, 'threshold': None}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--rows',type=int,default=1000000)
    args = parser.parse_args()
    if not 1 <= args.rows <= 2000000:
        parser.error('--rows must be 1..2000000')
    print(json.dumps(benchmark(args.rows),ensure_ascii=False,indent=2))
