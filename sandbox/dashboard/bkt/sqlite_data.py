"""Gitで配布する5回分の合成SQLiteと、読み取り専用のBKT入力アダプター。

python -m sandbox.dashboard.bkt.sqlite_data --create-demo
python -m sandbox.dashboard.bkt.sqlite_data
"""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile

from .csv_inference import INPUT_FIELDS, estimate_import
from .learning_data import MAX_ROWS, REQUIRED
from .mock_dataset import COLUMNS, DEFAULT_SEED, ROOT, generate, schema_sql

DEFAULT_DB = ROOT / 'data/mock_jlpt_n2_5_sessions/learning_logs.sqlite3'


def load_database(path=DEFAULT_DB):
    """QuestionResult表から必要列だけを読み、既存の補助モデル入力へ変換する。

    DBへは書き込まず、存在しないパスに空DBを作らない。任意の外部DBには
    現行CSVと同じ最低限の列名が必要。保存形式とCSV全列の一致は要求しない。
    """
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError(f'SQLiteファイルが見つかりません: {path.name}')
    try:
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as connection:
            connection.execute('PRAGMA query_only=ON')
            connection.row_factory = sqlite3.Row
            table = connection.execute("SELECT type FROM sqlite_master WHERE name='QuestionResult'").fetchone()
            if table is None or table['type'] != 'table':
                raise ValueError('SQLiteにQuestionResult表が必要です。')
            columns = {row['name'] for row in connection.execute('PRAGMA table_info("QuestionResult")')}
            missing = REQUIRED - columns
            if missing:
                raise ValueError('QuestionResult表に必要な列がありません: ' + ', '.join(sorted(missing)))
            # 列名は固定ホワイトリスト。本文・解説・点数はSELECTしない。
            selected = ', '.join(f'"{key}"' if key in columns else f'NULL AS "{key}"' for key in INPUT_FIELDS)
            order = '"SessionID", "QuestionSequence", "ResultID"' if 'QuestionSequence' in columns else '"SessionID", "ResultID"'
            rows = [dict(row) for row in connection.execute(f'SELECT {selected} FROM "QuestionResult" ORDER BY {order} LIMIT ?', (MAX_ROWS + 1,))]
    except sqlite3.Error as error:
        raise ValueError(f'SQLiteを読み込めません: {error}') from error
    if len(rows) > MAX_ROWS:
        raise ValueError(f'SQLiteの回答は{MAX_ROWS:,}行以下にしてください。')
    if not rows:
        raise ValueError('QuestionResult表に回答データがありません。')
    return {'records': rows, 'duplicates': [], 'files': [{'name': path.name, 'kind': 'SQLite', 'rows': len(rows)}],
            'input_count': len(rows), 'unique_input_count': len(rows), 'source': 'sqlite'}


def write_demo_database(path=DEFAULT_DB, overwrite=False):
    """既存の合成生成器と保存用5表スキーマで、1人×5回×30問を作る。"""
    path = Path(path)
    tables, source_manifest = generate(seed=DEFAULT_SEED, sessions=5)
    path.parent.mkdir(parents=True, exist_ok=True)
    # 一時DBを完成・検査してから配置する。既存の異なるファイルは既定で保護。
    with tempfile.TemporaryDirectory(dir=path.parent) as temp:
        temporary = Path(temp) / 'learning_logs.sqlite3'
        with closing(sqlite3.connect(temporary)) as connection:
            connection.executescript(schema_sql())
            connection.execute('PRAGMA user_version=1')
            for table, columns in COLUMNS.items():
                names = ', '.join(f'"{col[0]}"' for col in columns)
                placeholders = ', '.join('?' for _ in columns)
                connection.executemany(f'INSERT INTO "{table}" ({names}) VALUES ({placeholders})',
                                       [tuple(row[col[0]] for col in columns) for row in tables[table]])
            connection.commit()
            if connection.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('生成DBの外部キーが一致しません。')
            if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('生成DBの整合性を確認してください。')
        content = temporary.read_bytes()
        if path.exists() and path.read_bytes() != content and not overwrite:
            raise FileExistsError(f'{path}は内容が異なります。別の出力先か--overwriteを指定してください。')
        if not path.exists() or path.read_bytes() != content:
            temporary.replace(path)
    counts = {name: len(rows) for name, rows in tables.items()}
    sources = [Path(__file__), ROOT / 'mock_dataset.py']
    manifest = {'is_synthetic': True, 'purpose': 'read-only SQLite -> assisted BKT -> Dash smoke test',
                'database': path.name, 'schema': 'mock-storage-v1', 'sqlite_version': sqlite3.sqlite_version,
                'seed': DEFAULT_SEED, 'sessions': 5, 'counts': counts, 'dataset_id': source_manifest['dataset_id'],
                'summary': source_manifest['summary'],
                'generator_settings': {key: source_manifest[key] for key in ('generator_version', 'seed', 'sessions', 'start_date', 'spacing_days', 'source_sha256')},
                'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                'database_sha256': hashlib.sha256(content).hexdigest(),
                'notes': ['one synthetic learner, five sessions, thirty answered questions per session',
                          'all confidence and understanding levels are simulated, not measurements',
                          'storage tables reuse mock_dataset schema, not the 41-column export schema',
                          'DataSchemaVersion is absent in storage; the adapter leaves it null',
                          'the Dash reader never writes to the versioned database']}
    sidecars = {'manifest.json': json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', 'schema.sql': schema_sql()}
    for name, text in sidecars.items():
        target = path.parent / name
        if not target.exists() or target.read_text() != text:
            target.write_text(text)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=DEFAULT_DB)
    parser.add_argument('--create-demo', action='store_true')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    try:
        if args.create_demo:
            write_demo_database(args.database, args.overwrite)
        data = load_database(args.database)
        result = estimate_import(data)
    except (OSError, ValueError) as error:
        parser.exit(2, f'読み込めません: {error}\n')
    print(json.dumps({'database': str(args.database), 'sessions': len({r['SessionID'] for r in data['records']}),
                      'input': data['input_count'], 'estimated': len(result['records']),
                      'excluded': len(result['excluded']), 'source': result['source']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
