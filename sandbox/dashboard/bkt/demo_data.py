"""Synthetic observations for checking the dashboard; never real learner data."""
from datetime import datetime, timedelta, timezone


def sample_records():
    records = []
    start = datetime(2026, 10, 1, 9, tzinfo=timezone.utc)
    for student, outcomes in [("DEMO-A", [False, True, False, True, True, True]), ("DEMO-B", [True, False, False, True, False, True])]:
        for skill, label in [("SK_DEMO_READING", "サンプル・漢字読み"), ("SK_DEMO_GRAMMAR", "サンプル・文法")]:
            for index, correct in enumerate(outcomes):
                records.append({
                    "ResultID": f"{student}-{skill}-{index}", "SessionID": f"DEMO_SESSION_{index // 3}",
                    "StudentID": student, "SkillID": skill, "SkillName": label,
                    "QuestionID": f"DEMO_Q{index}", "QuestionSequence": index + 1,
                    "IsAnswered": True, "IsCorrect": correct,
                    "AnsweredAt": (start + timedelta(days=index, minutes=1 if 'GRAMMAR' in skill else 0)).isoformat(),
                    "Mode": "Drill", "ConfidenceLevel": str(1 + index % 4),
                    "UnderstandingLevel": str(index % 4), "ResponseTimeMs": str(15000 + index * 1000),
                })
    return records
