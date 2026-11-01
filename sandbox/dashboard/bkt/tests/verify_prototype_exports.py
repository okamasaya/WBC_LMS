"""Playwrightで保存した現行画面のCSV・レポートと推定接続を検証する。"""
import csv
from io import StringIO
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from sandbox.dashboard.bkt.learning_data import normalize_records, parse_question_csv
from sandbox.dashboard.bkt.model import estimate
from sandbox.dashboard.bkt.assisted_model import estimate_flat


def verify(root):
    summaries = []
    for mode, count in [('Actual', 30), ('Drill', 10)]:
        folder = Path(root) / mode
        manifest = json.loads((folder / 'manifest.json').read_text())
        read = lambda kind: (folder / manifest['files'][kind]).read_text(encoding='utf-8-sig')
        rows = parse_question_csv(read('questions'))
        assert len(rows) == count
        assert rows == parse_question_csv(read('raw'))
        assert all(row['StudentID'] == '' for row in rows)
        assert [row['ConfidenceLevel'] for row in rows[:2]] == ['2', '4']
        assert [row['UnderstandingLevel'] for row in rows[:2]] == ['0', '3']
        assert [row['IsAnswered'] for row in rows].count('TRUE') == 2
        assert not normalize_records(rows)['records']
        normalized = normalize_records(rows, 'synthetic-browser-learner', True)
        assert len(normalized['records']) == 2
        assert len(estimate(normalized['records'])['history']) == 2
        flat = estimate_flat(rows)
        assert len(flat['records']) == 2
        assert len(flat['excluded']) == count - 2
        assert not flat['records'][0]['UnderstandingMissing']
        session = list(csv.DictReader(StringIO(read('session'))))[0]
        assert len(session) == 26 and len(rows[0]) == 41
        assert session['SessionID'] == rows[0]['SessionID']
        assert int(session['AnsweredQuestions']) == 2
        assert int(session['CorrectCount']) == sum(r['IsCorrect'] == 'TRUE' for r in rows)
        report = (folder / manifest['report']).read_text()
        analysis = json.loads(report.split('=== AI_ANALYSIS_DATA_JSON ===\n')[1])
        assert analysis['session']['sessionId'] == session['SessionID']
        for item, row in zip(analysis['questions'], rows):
            assert item['correct'] == (row['IsCorrect'] == 'TRUE')
            if row['IsAnswered'] == 'TRUE':
                assert item['confidence'] == f"{row['ConfidenceLevel']} ({row['ConfidenceLabel']})"
                assert item['explanationUnderstanding'] == f"{row['UnderstandingLevel']} ({row['UnderstandingLabel']})"
        if mode == 'Actual':
            assert rows[0]['ReviewFlag'] == 'TRUE'
        summaries.append({'mode': mode, 'csv_rows': count, 'answered': 2,
                          'unanswered_excluded': count - 2, 'session_columns': 26,
                          'question_columns': 41, 'flat_records': 2,
                          'standard_bkt_history_with_explicit_identity': 2,
                          'raw_and_question_csv_equal': True,
                          'report_and_csv_values_equal': True})
    return summaries


if __name__ == '__main__':
    print(json.dumps(verify(sys.argv[1]), ensure_ascii=False, indent=2))
