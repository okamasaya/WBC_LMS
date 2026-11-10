#!/usr/bin/env python3
"""Authoring validation for IT banks; does not execute questions or review their meaning."""
import argparse
import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'prototype/it/GenAI_Passport'
SCHEMAS = {
    '0.1.0': BASE / 'schemas/question-bank.v0.1.0.schema.json',
    '0.2.0': BASE / 'question-bank.schema.json',
}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'JSONキーが重複しています: {key}')
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f'JSONでは使えない数値です: {value}')


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'),
                      object_pairs_hook=unique_object, parse_constant=reject_constant)


def check_placeholders(value, path='$'):
    if isinstance(value, str) and ('{{' in value or '}}' in value):
        raise ValueError(f'{path}: 未置換のテンプレート項目があります')
    if isinstance(value, dict):
        for key, item in value.items():
            check_placeholders(item, f'{path}.{key}')
    elif isinstance(value, list):
        for index, item in enumerate(value):
            check_placeholders(item, f'{path}[{index}]')


def validate_files(paths):
    from jsonschema import Draft202012Validator
    ids, exam_id, versions, counts = set(), None, set(), {'questions': 0, 'options': 0}
    resolved = set()
    for path in map(Path, paths):
        if path.resolve() in resolved:
            raise ValueError(f'{path}: 同じファイルが重複しています')
        resolved.add(path.resolve())
        try:
            bank = load_json(path)
            check_placeholders(bank)
            version = bank.get('schema_version') if isinstance(bank, dict) else None
            if not isinstance(version, str) or version not in SCHEMAS:
                raise ValueError('schema_version は0.1.0または0.2.0が必要です')
            schema = load_json(SCHEMAS[version])
            Draft202012Validator.check_schema(schema)
            errors = list(Draft202012Validator(schema).iter_errors(bank))
            if errors:
                error = errors[0]
                raise ValueError(f'{error.json_path}: {error.message}')
            if exam_id is not None and exam_id != bank['exam_id']:
                raise ValueError('exam_id が他のバンクと一致しません')
            exam_id = bank['exam_id']
            versions.add(version)
            for q in bank['questions']:
                def add_id(identifier):
                    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', identifier):
                        raise ValueError(f'IDの形式が不正です: {identifier!r}')
                    if identifier in ids:
                        raise ValueError(f'IDが重複しています: {identifier}')
                    ids.add(identifier)
                add_id(q['question_id'])
                texts = set()
                for pool in q['pools'].values():
                    for option in pool:
                        add_id(option['option_id'])
                        normalized = unicodedata.normalize('NFKC', option['text']).strip()
                        if normalized in texts:
                            raise ValueError(f"{q['question_id']}: 候補本文が重複しています")
                        texts.add(normalized)
                        counts['options'] += 1
                for group in q.get('instructions', {}).values():
                    normalized = [unicodedata.normalize('NFKC', text).strip() for text in group]
                    if len(normalized) != len(set(normalized)):
                        raise ValueError(f"{q['question_id']}: 末尾表現が重複しています")
                counts['questions'] += 1
        except (ValueError, OSError) as error:
            raise ValueError(f'{path}: {error}') from error
    return {**counts, 'versions': sorted(versions), 'exam_id': exam_id}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('banks', nargs='+', type=Path, help='教材JSON。複数指定時は全体でID重複を検査')
    args = parser.parse_args()
    try:
        result = validate_files(args.banks)
    except ImportError:
        print('ERROR: jsonschemaが必要です。使用するPython環境へ導入してください。', file=sys.stderr)
        return 2
    except ValueError as error:
        print(f'ERROR: {error}', file=sys.stderr)
        return 1
    print(f"PASS: {result['questions']}問 / {result['options']}候補 / schema {', '.join(result['versions'])}")
    print('確認範囲: 構造・ID・本文重複・未置換項目。教材の意味とエンジン対応状況は別途確認が必要です。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
