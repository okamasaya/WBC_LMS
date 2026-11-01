"""CSV/SQLiteの検証済みスナップショットと、サイズ制限付き集計キャッシュ。

共有するのは公開サンプルデータと計算結果だけ。画面の選択状態は保持しない。
再読込に失敗した場合は既存のスナップショットを変更しない。
"""
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import sqlite3
import threading
import pandas as pd

DATA = Path(__file__).resolve().parent / 'data' / 'bike'
DATABASE = Path(__file__).resolve().parent / '.local' / 'bike.sqlite3'


def validate_frames(raw):
    frames = {}
    for source in ('day', 'hour'):
        frame = raw[source].copy()
        required = ['instant', 'dteday', 'weathersit', 'workingday', 'cnt', 'casual', 'registered']
        if source == 'hour':
            required.append('hr')
        if not set(required).issubset(frame.columns) or frame.empty:
            raise ValueError(f'{source}: 必須列またはデータがありません。')
        frame['timestamp'] = pd.to_datetime(frame['dteday'], format='%Y-%m-%d', errors='raise')
        for name in [key for key in required if key != 'dteday']:
            values = pd.to_numeric(frame[name], errors='raise')
            if values.isna().any() or not values.mod(1).eq(0).all():
                raise ValueError(f'{source}: {name}は欠損のない整数にしてください。')
            frame[name] = values.astype('int64')
        if source == 'hour':
            if not frame.hr.between(0, 23).all():
                raise ValueError('hour: 時刻は0〜23です。')
            frame['timestamp'] += pd.to_timedelta(frame.hr, unit='h')
        if frame.timestamp.duplicated().any() or frame.instant.duplicated().any():
            raise ValueError(f'{source}: 日時またはIDが重複しています。')
        if not frame.weathersit.isin([1, 2, 3, 4]).all() or not frame.workingday.isin([0, 1]).all():
            raise ValueError(f'{source}: 天候・勤務日の値が不正です。')
        if (frame[['cnt', 'casual', 'registered']] < 0).any().any() or not (frame.casual + frame.registered == frame.cnt).all():
            raise ValueError(f'{source}: 貸出回数の整合性がありません。')
        if not frame.timestamp.between('2011-01-01', '2013-01-01', inclusive='left').all():
            raise ValueError('このサンプルの対応期間は2011〜2012年です。')
        frames[source] = frame.sort_values('timestamp').reset_index(drop=True)
    daily = frames['day'].set_index('dteday')['cnt'].sort_index()
    hourly = frames['hour'].groupby('dteday')['cnt'].sum().sort_index()
    if not daily.equals(hourly):
        raise ValueError('日別と時間別の日ごとの貸出総数が一致しません。')
    return frames


class BikeDataService:
    def __init__(self, data_dir=DATA, database=DATABASE, cache_size=16, snapshot_size=8):
        self.data_dir, self.database = Path(data_dir), Path(database)
        self.cache_size, self.snapshot_size = cache_size, snapshot_size
        self.lock = threading.RLock()
        self.snapshots, self.cache = OrderedDict(), OrderedDict()
        self.hits = self.misses = 0

    def initialize_database(self):
        """初回だけCSVをSQLiteへ取り込む。既存DBや元CSVは上書きしない。"""
        with self.lock:
            if self.database.exists():
                return
            raw = {name: pd.read_csv(self.data_dir / f'{name}.csv') for name in ('day', 'hour')}
            validate_frames(raw)
            self.database.parent.mkdir(parents=True, exist_ok=True)
            # 両テーブルを1つのトランザクションで作成する。
            connection = sqlite3.connect(self.database)
            try:
                connection.execute('BEGIN IMMEDIATE')
                for name, frame in raw.items():
                    columns = ', '.join('"' + column.replace('"', '""') + '" ' + ('TEXT' if column == 'dteday' else 'REAL') for column in frame.columns)
                    connection.execute(f'CREATE TABLE "{name}" ({columns})')
                    placeholders = ','.join('?' for _ in frame.columns)
                    connection.executemany(f'INSERT INTO "{name}" VALUES ({placeholders})', frame.itertuples(index=False, name=None))
                connection.commit()
            except Exception:
                connection.rollback()
                connection.close()
                self.database.unlink(missing_ok=True)
                raise
            finally:
                connection.close()

    def reload(self, backend='csv'):
        with self.lock:
            if backend == 'csv':
                raw = {name: pd.read_csv(self.data_dir / f'{name}.csv') for name in ('day', 'hour')}
            elif backend == 'sqlite':
                self.initialize_database()
                # read-only connection + a read transaction: both tables use one DB snapshot.
                with sqlite3.connect(self.database.resolve().as_uri() + '?mode=ro', uri=True) as connection:
                    connection.execute('BEGIN')
                    raw = {name: pd.read_sql_query(f'SELECT * FROM "{name}"', connection) for name in ('day', 'hour')}
            else:
                raise ValueError('未対応の接続先です。')
            frames = validate_frames(raw)
            digest = sha256()
            for name, frame in frames.items():
                digest.update(frame.to_csv(index=False).encode())
            version = backend + ':' + digest.hexdigest()
            self.snapshots[version] = frames
            self.snapshots.move_to_end(version)
            while len(self.snapshots) > self.snapshot_size:
                self.snapshots.popitem(last=False)
            return {'version': version, 'backend': backend, 'checked_at': datetime.now(timezone.utc).isoformat()}

    def frames(self, token):
        with self.lock:
            version = (token or {}).get('version')
            if version not in self.snapshots:
                raise ValueError('表示データの保存期限が切れました。「データを再読込」を押してください。')
            # Internal read-only convention; consumers never mutate these frames.
            return self.snapshots[version]

    def cached(self, key, factory):
        with self.lock:
            if key in self.cache:
                self.hits += 1
                self.cache.move_to_end(key)
                return deepcopy(self.cache[key])
        value = factory()
        with self.lock:
            self.misses += 1
            self.cache[key] = deepcopy(value)
            while len(self.cache) > self.cache_size:
                self.cache.popitem(last=False)
        return value
