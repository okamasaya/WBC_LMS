"""Validate the authoring contract independently of the v0.1 runtime engine."""
import copy
import importlib.util
import itertools
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'prototype/it/GenAI_Passport'
SCRIPT = ROOT / 'scripts/validate-it-bank.py'
spec = importlib.util.spec_from_file_location('authoring_validator', SCRIPT)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class AuthoringTests(unittest.TestCase):
    def setUp(self):
        self.example = validator.load_json(BASE / 'examples/question-bank.v0.2.0.json')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def write(self, value, name='bank.json'):
        path = Path(self.temp.name) / name
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
        return path

    def reject(self, mutate, pattern=None):
        value = copy.deepcopy(self.example)
        mutate(value)
        with self.assertRaisesRegex(ValueError, pattern or '.'):
            validator.validate_files([self.write(value)])

    def test_schemas_and_completed_examples(self):
        for path in validator.SCHEMAS.values():
            Draft202012Validator.check_schema(validator.load_json(path))
        counts = validator.validate_files([BASE / 'examples/question-bank.v0.2.0.json'])
        self.assertEqual(counts['questions'], 2)
        self.assertEqual(counts['options'], 11)
        self.assertEqual(counts['versions'], ['0.2.0'])

    def test_legacy_sample_is_preserved_and_valid(self):
        result = validator.validate_files([BASE / 'data/sample_questions.json'])
        self.assertEqual((result['questions'], result['options']), (6, 36))
        self.assertEqual(result['versions'], ['0.1.0'])

    def test_templates_are_incomplete_and_become_valid_after_filling(self):
        for kind in ['polarity', 'standard']:
            template = validator.load_json(BASE / f'templates/{kind}.template.json')
            with self.assertRaisesRegex(ValueError, '未置換'):
                validator.validate_files([self.write(template)])

            def fill(value):
                if isinstance(value, dict):
                    return {k: fill(v) for k, v in value.items()}
                if isinstance(value, list):
                    return [fill(v) for v in value]
                if isinstance(value, str) and value.startswith('{{'):
                    token = value[2:-2]
                    if token == 'QUESTION_ID':
                        return f'TEST_{kind}_Q1'
                    if '_OPTION_ID_' in token:
                        return f'TEST_{kind}_{token}'
                    if token == 'QUESTION_PREFIX_ENDING_WITH_COMMA':
                        return '形式検証について、'
                    if token == 'COMPLETE_QUESTION':
                        return '形式検証の選択肢を一つ選んでください。'
                    return f'形式検証用 {token}'
                return value

            result = validator.validate_files([self.write(fill(template))])
            self.assertEqual(result['questions'], 1)

    def test_polarity_requires_both_instruction_groups_and_three_each(self):
        mutations = [
            lambda b: b['questions'][0].pop('instructions'),
            lambda b: b['questions'][0]['instructions'].pop('inappropriate'),
            lambda b: b['questions'][0]['instructions'].update(appropriate=[]),
            lambda b: b['questions'][0]['instructions'].update(appropriate=['　\n']),
            lambda b: b['questions'][0]['pools']['appropriate'].pop(),
            lambda b: b['questions'][0]['pools']['inappropriate'].pop(),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                self.reject(mutate)

    def test_standard_requires_one_correct_three_incorrect_and_no_instructions(self):
        mutations = [
            lambda b: b['questions'][1]['pools'].update(correct=[]),
            lambda b: b['questions'][1]['pools']['incorrect'].pop(),
            lambda b: b['questions'][1].update(instructions={}),
            lambda b: b['questions'][1].update(instructions=None),
            lambda b: b['questions'][1].update(instructions=copy.deepcopy(b['questions'][0]['instructions'])),
            lambda b: b['questions'][1].update(pools=copy.deepcopy(b['questions'][0]['pools'])),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                self.reject(mutate)

    def test_extra_candidates_and_one_instruction_are_valid(self):
        q = self.example['questions'][0]
        q['instructions'] = {key: value[:1] for key, value in q['instructions'].items()}
        q['pools']['appropriate'].append({'option_id': 'TEST_EXTRA_A', 'text': '構造検証専用追加候補', 'explanation': '構造検証用'})
        standard = self.example['questions'][1]
        standard['pools']['correct'].append({'option_id': 'TEST_EXTRA_C', 'text': '構造検証専用追加正解', 'explanation': '構造検証用'})
        result = validator.validate_files([self.write(self.example)])
        self.assertEqual(result['options'], 13)

    def test_unknown_and_legacy_fields_wrong_types_and_blank_text_fail(self):
        mutations = [
            lambda b: b['questions'][0].update(stems={}),
            lambda b: b['questions'][0].update(appropriate_flag=True),
            lambda b: b['questions'][0].update(correct_answer=1),
            lambda b: b['questions'][0]['pools']['appropriate'][0].update(isCorrect=True),
            lambda b: b['questions'][0].update(question_type='other'),
            lambda b: b['questions'][0].update(chapter=True),
            lambda b: b['questions'][0].update(chapter=0),
            lambda b: b['questions'][0].update(question='　'),
            lambda b: b['questions'][0]['pools']['appropriate'][0].update(explanation='\t'),
            lambda b: b.update(schema_version=0.2),
            lambda b: b.update(questions=[]),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                self.reject(mutate)

    def test_duplicate_ids_and_normalized_texts_are_rejected(self):
        self.reject(lambda b: b['questions'][1].update(question_id=b['questions'][0]['question_id']), 'IDが重複')
        self.reject(lambda b: b['questions'][1]['pools']['incorrect'][0].update(option_id=b['questions'][0]['pools']['appropriate'][0]['option_id']), 'IDが重複')
        self.reject(lambda b: b['questions'][0]['pools']['inappropriate'][0].update(text='　'+b['questions'][0]['pools']['appropriate'][0]['text']+' '), '候補本文が重複')
        self.example['questions'][0]['pools']['appropriate'][0]['text'] = 'ＡＢＣ'
        self.reject(lambda b: b['questions'][0]['pools']['inappropriate'][0].update(text='ABC'), '候補本文が重複')

    def test_duplicate_instructions_and_remaining_placeholders_are_rejected(self):
        self.reject(lambda b: b['questions'][0]['instructions']['appropriate'].append(b['questions'][0]['instructions']['appropriate'][0]))
        self.reject(lambda b: b['questions'][0]['instructions']['appropriate'].append('　'+b['questions'][0]['instructions']['appropriate'][0]+' '), '末尾表現が重複')
        self.reject(lambda b: b['questions'][0].update(explanation='{{COMMON_EXPLANATION}}'), '未置換')

    def test_multiple_files_must_have_unique_ids_and_matching_exam(self):
        first = self.write({**self.example, 'questions': self.example['questions'][:1]}, 'a.json')
        second = self.write({**self.example, 'questions': self.example['questions'][1:]}, 'b.json')
        self.assertEqual(validator.validate_files([first, second])['questions'], 2)
        with self.assertRaisesRegex(ValueError, '同じファイル'):
            validator.validate_files([first, first])
        with self.assertRaisesRegex(ValueError, 'IDが重複'):
            validator.validate_files([first, self.write(self.example, 'duplicate.json')])
        other = {**self.example, 'exam_id': 'OTHER', 'questions': self.example['questions'][1:]}
        with self.assertRaisesRegex(ValueError, 'exam_id'):
            validator.validate_files([first, self.write(other, 'other.json')])

    def test_duplicate_json_keys_and_non_json_numbers_are_rejected(self):
        path = Path(self.temp.name) / 'invalid.json'
        for content in ['{"format":"a","format":"b"}', '{"value":NaN}']:
            path.write_text(content, encoding='utf-8')
            with self.assertRaises(ValueError):
                validator.validate_files([path])

    def test_all_example_instructions_and_candidate_arrangements_have_one_target(self):
        patterns = 0
        for q in self.example['questions']:
            modes = ['appropriate', 'inappropriate'] if q['question_type'] == 'polarity' else ['correct']
            for mode in modes:
                other = {'appropriate': 'inappropriate', 'inappropriate': 'appropriate', 'correct': 'incorrect'}[mode]
                instructions = q['instructions'][mode] if q['question_type'] == 'polarity' else ['']
                target_ids = {o['option_id'] for o in q['pools'][mode]}
                for suffix in instructions:
                    self.assertTrue((q['question'] + suffix).endswith('ください。'))
                    for target in q['pools'][mode]:
                        for distractors in itertools.combinations(q['pools'][other], 3):
                            for order in itertools.permutations([target, *distractors]):
                                ids = [o['option_id'] for o in order]
                                self.assertEqual(len(set(ids)), 4)
                                self.assertEqual(sum(oid in target_ids for oid in ids), 1)
                                patterns += 1
        self.assertEqual(patterns, 336)

    def test_cli_exit_status_and_document_links(self):
        valid = subprocess.run([sys.executable, str(SCRIPT), str(BASE/'examples/question-bank.v0.2.0.json')], capture_output=True, text=True)
        self.assertEqual(valid.returncode, 0, valid.stderr)
        invalid = subprocess.run([sys.executable, str(SCRIPT), str(BASE/'templates/standard.template.json')], capture_output=True, text=True)
        self.assertNotEqual(invalid.returncode, 0)
        self.assertIn('未置換', invalid.stderr)
        for readme in [BASE/'README.md', ROOT/'prototype/assets/js/drill_IT/README.md']:
            for link in re.findall(r'\]\(([^)]+)\)', readme.read_text()):
                if not link.startswith(('http:', 'https:')):
                    self.assertTrue((readme.parent/link.split('#')[0]).exists(), (readme, link))


if __name__ == '__main__':
    unittest.main()
