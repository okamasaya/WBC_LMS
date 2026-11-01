"""実出力CSVの取込と補助BKTへの接続。Dash/Djangoに依存しない。

python -m sandbox.dashboard.bkt.csv_inference CSV... --output 出力フォルダー
"""
import argparse
import base64
import binascii
import csv
from datetime import datetime
import hashlib
from io import StringIO
import json
from pathlib import Path

from .assisted_model import estimate_flat, level
from .learning_data import MAX_ROWS, boolean, parse_question_csv
from .model import BKTParameters

MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024
MAX_FILES = 20
# 問題本文・解説・点数などは取り込まず、推定と照合に必要な列に絞る。
INPUT_FIELDS = (
    'DataSchemaVersion', 'ResultID', 'SessionID', 'StudentID', 'QuestionID',
    'SkillID', 'SkillName', 'QuestionSequence', 'AnsweredAt', 'Mode',
    'IsAnswered', 'IsCorrect', 'ConfidenceLevel', 'UnderstandingLevel',
)
SUMMARY_REQUIRED = {'SessionID', 'TotalQuestions', 'AnsweredQuestions', 'StartAt', 'EndAt'}


def _signature(row):
    """同じ回答のRaw/QuestionResult重複と、異なる確定版を区別する。"""
    result = []
    for key in INPUT_FIELDS:
        if key in ('DataSchemaVersion', 'SkillName', 'ResultID'):
            continue
        value = row.get(key)
        try:
            if key in ('IsAnswered', 'IsCorrect'):
                value = boolean(value)
            elif key in ('ConfidenceLevel', 'UnderstandingLevel'):
                value = level(value, range(1, 5) if key == 'ConfidenceLevel' else range(4), key)
            elif key == 'AnsweredAt' and value:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            else:
                value = str(value or '').strip()
        except (ValueError, TypeError):
            # 不正な観測も勝手に採用せず、推定側の除外理由へ渡す。
            value = str(value or '').strip()
        result.append(value)
    return tuple(result)


def import_csv_texts(files):
    """[(filename, UTF-8 decoded text)] -> 最小入力。原本も学習者IDも変更しない。"""
    files = list(files)
    if not files or len(files) > MAX_FILES:
        raise ValueError(f'CSVを1〜{MAX_FILES}ファイル指定してください。')
    records, duplicates, reports, seen = [], [], [], {}
    total_bytes = input_count = 0
    for name, text in files:
        if not isinstance(name, str) or not name.lower().endswith('.csv') or not isinstance(text, str):
            raise ValueError('UTF-8のCSVファイルを指定してください。')
        size = len(text.encode('utf-8'))
        total_bytes += size
        if size > MAX_FILE_BYTES or total_bytes > MAX_TOTAL_BYTES:
            raise ValueError('1ファイル8MB以下、合計32MB以下にしてください。')
        try:
            first = next((row for row in csv.reader(StringIO(text.lstrip('\ufeff')), strict=True) if row and any(row)), [])
            if SUMMARY_REQUIRED.issubset(first) and 'IsCorrect' not in first:
                summary = list(csv.DictReader(StringIO(text.lstrip('\ufeff')), strict=True))
                if any(None in row or None in row.values() for row in summary):
                    raise ValueError('Session CSVの列数を確認してください。')
                reports.append({'name': Path(name).name, 'kind': 'Session（集計のみ・推定対象外）', 'rows': len(summary)})
                continue
            raw = parse_question_csv(text)
        except (ValueError, csv.Error) as error:
            raise ValueError(f'{Path(name).name}: {error}') from error
        kind = 'Raw' if first == ['=== Session ==='] else 'QuestionResult'
        reports.append({'name': Path(name).name, 'kind': kind, 'rows': len(raw)})
        for row in raw:
            input_count += 1
            if input_count > MAX_ROWS:
                raise ValueError(f'回答の入力は重複を含め{MAX_ROWS:,}行以下にしてください。')
            selected = {key: row.get(key, '') for key in INPUT_FIELDS}
            result_id = selected['ResultID'].strip()
            if result_id and result_id in seen:
                if seen[result_id] != _signature(selected):
                    raise ValueError(f'ResultID {result_id} の回答・補助項目または識別情報が競合しています。採用する確定版だけを指定してください。')
                duplicates.append({'Row': input_count, 'ResultID': result_id, 'Reason': '同じ回答の重複（Raw/QuestionResultなど）'})
                continue
            if result_id:
                seen[result_id] = _signature(selected)
            records.append(selected)
    if not records:
        raise ValueError('Sessionは集計用です。QuestionResultまたは統合Raw CSVも指定してください。')
    return {'records': records, 'duplicates': duplicates, 'files': reports,
            'input_count': input_count, 'unique_input_count': len(records), 'source': 'uploaded'}


def import_uploads(contents, filenames):
    if isinstance(contents, str):
        contents, filenames = [contents], [filenames]
    if not isinstance(contents, list) or not contents or not isinstance(filenames, list) or len(contents) != len(filenames):
        raise ValueError('CSVファイルを選択してください。')
    if len(contents) > MAX_FILES:
        raise ValueError(f'一度に選べるのは{MAX_FILES}ファイルまでです。')
    files, total = [], 0
    for content, name in zip(contents, filenames):
        try:
            payload = content.split(',', 1)[1]
            if len(payload) > MAX_FILE_BYTES * 4 // 3 + 8:
                raise ValueError('1ファイル8MB以下にしてください。')
            decoded = base64.b64decode(payload, validate=True)
            total += len(decoded)
            if len(decoded) > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
                raise ValueError('1ファイル8MB以下、合計32MB以下にしてください。')
            files.append((name, decoded.decode('utf-8-sig')))
        except (AttributeError, IndexError, binascii.Error, UnicodeDecodeError) as error:
            raise ValueError('UTF-8のCSVファイルを指定してください。') from error
    return import_csv_texts(files)


def estimate_import(data, parameters=None):
    result = estimate_flat(data['records'], parameters)
    return {**result, 'source': 'uploaded', 'files': data['files'],
            'duplicates': data['duplicates'], 'input_count': data['input_count'],
            'unique_input_count': data['unique_input_count'], 'scope': 'independent_answers_same_prior'}


def _csv(rows, fallback_fields):
    stream = StringIO(newline='')
    fields = list(dict.fromkeys(key for row in rows for key in row)) if rows else list(fallback_fields)
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return '\ufeff' + stream.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='+', type=Path)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / '.local/bkt_results')
    args = parser.parse_args()
    try:
        if len(args.files) > MAX_FILES or any(p.stat().st_size > MAX_FILE_BYTES for p in args.files) or sum(p.stat().st_size for p in args.files) > MAX_TOTAL_BYTES:
            raise ValueError('最大20ファイル、1ファイル8MB、合計32MB以下にしてください。')
        data = import_csv_texts([(p.name, p.read_text(encoding='utf-8-sig')) for p in args.files])
        result = estimate_import(data, BKTParameters())
    except (OSError, UnicodeDecodeError, ValueError) as error:
        parser.exit(2, f'取り込めません: {error}\n')
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'bkt_assisted_flat_results.csv').write_text(_csv(result['records'], (*INPUT_FIELDS, 'AssistedAfterLearning')), encoding='utf-8', newline='')
    (args.output / 'excluded.csv').write_text(_csv(result['excluded'] + result['duplicates'], ('Row', 'ResultID', 'Reason')), encoding='utf-8', newline='')
    metadata = {key: value for key, value in result.items() if key not in ('records', 'excluded', 'duplicates')}
    metadata.update({'estimated_count': len(result['records']), 'excluded_count': len(result['excluded']),
                     'duplicate_count': len(result['duplicates']), 'score_used': False,
                     'input_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in args.files}})
    (args.output / 'inference.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'estimated': len(result['records']), 'excluded': len(result['excluded']),
                      'duplicates': len(result['duplicates']), 'output': str(args.output)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
