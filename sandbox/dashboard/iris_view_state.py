"""URLから渡された値を検証する。URLには行IDと表示条件だけを保存する。"""
import json
from urllib.parse import parse_qs, urlencode
from iris_crossfilter import MEASUREMENTS, SOURCES, load_iris

_FRAME = load_iris()
SPECIES = set(_FRAME['species'])
ROW_IDS = set(_FRAME['sample_no'])
DEFAULT = {'species': 'all', 'x': 'sepal_length', 'y': 'sepal_width', 'filters': {}}


def validate_view(value):
    if not isinstance(value, dict) or value.get('version') != 1:
        raise ValueError('対応していない形式です。')
    species, x, y = (value.get(key) for key in ('species', 'x', 'y'))
    if species not in ['all', *SPECIES] or x not in MEASUREMENTS or y not in MEASUREMENTS:
        raise ValueError('品種または測定項目が不正です。')
    filters = value.get('filters', {})
    if not isinstance(filters, dict) or any(key not in SOURCES for key in filters):
        raise ValueError('選択条件が不正です。')
    normalized = {}
    for source, items in filters.items():
        if not isinstance(items, list) or len(items) > len(ROW_IDS):
            raise ValueError('選択した行が不正です。')
        valid = (lambda item: isinstance(item, str) and item in SPECIES) if source == 'bar' else (lambda item: type(item) is int and item in ROW_IDS)
        if not all(valid(item) for item in items):
            raise ValueError('存在しない品種または行が指定されています。')
        normalized[source] = sorted(set(items))
    return {'species': species, 'x': x, 'y': y, 'filters': normalized}


def encode_view(species, x, y, state):
    view = validate_view({'version': 1, 'species': species, 'x': x, 'y': y, 'filters': (state or {}).get('filters', {})})
    return '?' + urlencode({'view': json.dumps({'version': 1, **view}, separators=(',', ':'))})


def decode_view(search):
    if len(search) > 12000:
        raise ValueError('URLが長すぎます。')
    try:
        values = parse_qs(search.lstrip('?')).get('view')
        if not values or len(values) != 1:
            raise ValueError('共有条件がありません。')
        return validate_view(json.loads(values[0]))
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError('共有条件を読み込めません。') from exc
