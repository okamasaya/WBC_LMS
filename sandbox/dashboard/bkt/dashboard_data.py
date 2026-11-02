"""SQLiteを主入力、同内容CSVを控えとする学習画面の集計。標準ライブラリのみ。"""
import argparse
from contextlib import closing
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import sqlite3
from statistics import mean

from .assisted_model import estimate_flat, level
from .learning_data import boolean, MAX_ROWS
from .mock_dataset import COLUMNS, csv_bytes
from .sqlite_data import DEFAULT_DB

CSV_BACKUP = DEFAULT_DB.parent / 'csv'
JST = timezone(timedelta(hours=9))
# 点数・問題本文・解説は集計・モデルへ持ち込まない。
RESULT_FIELDS = ('ResultID', 'SessionID', 'StudentID', 'SkillID', 'SkillName',
                 'QuestionID', 'QuestionSequence', 'SessionNumber', 'Mode',
                 'CategoryLevel2', 'CategoryLevel3', 'AnsweredAt', 'IsAnswered',
                 'IsCorrect', 'ConfidenceLevel', 'UnderstandingLevel', 'ResponseTimeMs')


def _read_tables(database):
    database = Path(database).resolve()
    if not database.is_file():
        raise ValueError('SQLiteファイルが見つかりません。')
    try:
        with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute('PRAGMA query_only=ON')
            result = {}
            for table, fields in [('QuestionResult', RESULT_FIELDS),
                                  ('Session', ('SessionID', 'SessionNumber', 'StartAt', 'StudentID')),
                                  ('Student', ('StudentID', 'DisplayName'))]:
                names = ', '.join(f'"{key}"' for key in fields)
                # SQLiteの二重引用符による文字列フォールバックを避け、必須列を検査。
                available = {r['name'] for r in connection.execute(f'PRAGMA table_info("{table}")')}
                if not set(fields).issubset(available):
                    raise ValueError(f'{table}表の表示用項目が不足しています。')
                result[table] = [dict(r) for r in connection.execute(f'SELECT {names} FROM "{table}" LIMIT ?', (MAX_ROWS + 1,))]
                if len(result[table]) > MAX_ROWS:
                    raise ValueError(f'表示用入力は各表{MAX_ROWS:,}行以下にしてください。')
            return result
    except sqlite3.Error as error:
        raise ValueError(f'SQLiteを読み込めません: {error}') from error


def export_csv_backup(database=DEFAULT_DB, output=CSV_BACKUP, overwrite=False):
    """保存用5表をCSVへ複製する。DBの値・型と対応する控えで、現行41列の再出力ではない。"""
    database, output = Path(database).resolve(), Path(output)
    if not database.is_file():
        raise ValueError('SQLiteファイルが見つかりません。')
    files, counts = {}, {}
    with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        for table, columns in COLUMNS.items():
            names = ', '.join(f'"{col[0]}"' for col in columns)
            rows = [dict(row) for row in connection.execute(f'SELECT {names} FROM "{table}"')]
            for row in rows:
                for key, kind, _, _ in columns:
                    if kind == 'BOOLEAN' and row[key] is not None:
                        row[key] = bool(row[key])
            files[f'{table}.csv'] = csv_bytes(table, rows)
            counts[table] = len(rows)
    manifest = {'is_synthetic': True, 'purpose': 'CSV backup of the five-session SQLite fixture',
                'source_database': database.name, 'source_database_sha256': hashlib.sha256(database.read_bytes()).hexdigest(),
                'counts': counts, 'files_sha256': {name: hashlib.sha256(value).hexdigest() for name, value in files.items()}}
    files['manifest.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    for name, value in files.items():
        path = output / name
        if path.exists() and path.read_bytes() != value and not overwrite:
            raise FileExistsError(f'{name}は既存内容と異なります。更新時のみ--overwriteを指定してください。')
    output.mkdir(parents=True, exist_ok=True)
    for name, value in files.items():
        path = output / name
        if not path.exists() or path.read_bytes() != value:
            path.write_bytes(value)
    return manifest


def load_learning_data(source='sqlite', database=DEFAULT_DB, csv_folder=CSV_BACKUP):
    if source == 'sqlite':
        tables = _read_tables(database)
    elif source == 'csv':
        tables = {}
        try:
            for table in ('QuestionResult', 'Session', 'Student'):
                with (Path(csv_folder) / f'{table}.csv').open(encoding='utf-8-sig', newline='') as stream:
                    reader = csv.DictReader(stream)
                    if reader.fieldnames != [column[0] for column in COLUMNS[table]]:
                        raise ValueError(f'{table}.csvの列定義を確認してください。')
                    tables[table] = []
                    for row in reader:
                        if None in row or None in row.values():
                            raise ValueError(f'{table}.csvの列数を確認してください。')
                        for key, kind, _, _ in COLUMNS[table]:
                            if kind in ('BOOLEAN', 'INTEGER'):
                                row[key] = None if row[key] == '' else int(boolean(row[key])) if kind == 'BOOLEAN' else int(row[key])
                        tables[table].append(row)
                        if len(tables[table]) > MAX_ROWS:
                            raise ValueError(f'表示用入力は各表{MAX_ROWS:,}行以下にしてください。')
        except (OSError, csv.Error, UnicodeError) as error:
            raise ValueError(f'控えCSVを読み込めません: {error}') from error
    else:
        raise ValueError('入力元はsqliteまたはcsvです。')
    try:
        sessions = {row['SessionID']: row for row in tables['Session']}
        students = {row['StudentID']: row['DisplayName'] for row in tables['Student']}
        records, seen = [], set()
        for raw in tables['QuestionResult']:
            row = {key: raw[key] for key in RESULT_FIELDS}
            if row['ResultID'] in seen:
                raise ValueError('回答IDが重複しています。')
            seen.add(row['ResultID'])
            session = sessions[row['SessionID']]
            if row['StudentID'] != session['StudentID'] or row['StudentID'] not in students:
                raise ValueError('回答と実施回・学習者の対応を確認してください。')
            started = datetime.fromisoformat(session['StartAt'].replace('Z', '+00:00'))
            if started.utcoffset() is None:
                raise ValueError('実施時刻にタイムゾーンが必要です。')
            row['SessionDate'] = started.astimezone(JST).date().isoformat()
            row['SessionNumber'] = int(session['SessionNumber'])
            row['QuestionSequence'] = int(row['QuestionSequence'])
            row['StudentName'] = students[row['StudentID']]
            records.append(row)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f'学習ログの構成を確認してください: {error}') from error
    if not records:
        raise ValueError('表示する回答データがありません。')
    return sorted(records, key=lambda r: (r['SessionDate'], r['SessionID'], r['QuestionSequence']))


def filter_records(records, student='__all__', skill='__all__', start=None, end=None):
    if start and end and start[:10] > end[:10]:
        raise ValueError('開始日は終了日以前にしてください。')
    return [r for r in records if (student == '__all__' or r['StudentID'] == student)
            and (skill == '__all__' or r['SkillID'] == skill)
            and (not start or r['SessionDate'] >= start[:10])
            and (not end or r['SessionDate'] <= end[:10])]


def _average(values):
    return mean(values) if values else None


def summarize(records):
    """実測正誤・自己申告・独立モデルを別集計。各平均は有効値だけを分母にする。"""
    observations, unanswered, invalid = [], 0, 0
    for raw in records:
        try:
            if not boolean(raw['IsAnswered']):
                unanswered += 1
                continue
            correct = boolean(raw['IsCorrect'])
        except (ValueError, TypeError):
            invalid += 1
            continue
        values = {}
        for key, allowed in [('ConfidenceLevel', range(1, 5)), ('UnderstandingLevel', range(4))]:
            try:
                values[key] = level(raw.get(key), allowed, key)
            except (ValueError, TypeError):
                values[key] = None
        try:
            duration = float(raw.get('ResponseTimeMs')) / 1000
            if not math.isfinite(duration) or duration <= 0:
                duration = None
        except (TypeError, ValueError):
            duration = None
        observations.append({**values, 'correct': correct, 'seconds': duration})
    model = estimate_flat(records)
    understanding = [r['UnderstandingLevel'] for r in observations if r['UnderstandingLevel'] is not None]
    return {'InputCount': len(records), 'Answered': len(observations), 'Correct': sum(r['correct'] for r in observations),
            'Accuracy': _average([int(r['correct']) for r in observations]),
            'Understanding': _average(understanding), 'UnderstandingCount': len(understanding),
            'ModelMean': _average([r['AssistedAfterLearning'] for r in model['records']]),
            'ModelCount': len(model['records']), 'AverageSeconds': _average([r['seconds'] for r in observations if r['seconds'] is not None]),
            'Sessions': len({r['SessionID'] for r in records}), 'Unanswered': unanswered,
            'InvalidObservation': invalid, 'UnderstandingUnavailable': len(observations) - len(understanding),
            'ConfidenceUnavailable': sum(r['ConfidenceLevel'] is None for r in observations),
            'ConfidentWrong': sum(not r['correct'] and r['ConfidenceLevel'] in (1, 2) for r in observations),
            'ModelExcluded': len(model['excluded'])}


def build_report(records):
    overall = summarize(records)
    skills, sessions = [], []
    for skill in sorted({r['SkillID'] for r in records}):
        group = [r for r in records if r['SkillID'] == skill]
        skills.append({'SkillID': skill, 'SkillName': group[0]['SkillName'], 'Category': group[0]['CategoryLevel2'], **summarize(group)})
    for session in sorted({r['SessionID'] for r in records}, key=lambda sid: next((r['SessionDate'], r['SessionNumber'], sid) for r in records if r['SessionID'] == sid)):
        group = [r for r in records if r['SessionID'] == session]
        sessions.append({'SessionID': session, 'SessionNumber': group[0]['SessionNumber'], 'Date': group[0]['SessionDate'], **summarize(group)})
    model = estimate_flat(records)
    return {'overall': overall, 'skills': skills, 'sessions': sessions, 'details': model['records'],
            'excluded': model['excluded'], 'parameters': model['parameters'], 'assumptions': model['assumptions'],
            'model_version': model['model_version'], 'scope': 'independent_answers_same_prior'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export-csv', action='store_true')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    if args.export_csv:
        export_csv_backup(overwrite=args.overwrite)
    report = build_report(load_learning_data())
    print(json.dumps(report['overall'], ensure_ascii=False))


if __name__ == '__main__':
    main()
