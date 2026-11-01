"""CSV ingestion for the existing Session/QuestionResult export, without persistence."""
import csv
from datetime import datetime, timezone
from io import StringIO

REQUIRED = {"ResultID", "SessionID", "SkillID", "IsAnswered", "IsCorrect", "AnsweredAt"}
OBSERVATION_KEYS = ("StudentID", "SkillID", "ResultID", "SessionID", "QuestionID", "IsAnswered", "IsCorrect", "AnsweredAt", "QuestionSequence", "Mode")
MAX_ROWS = 50000


def parse_question_csv(text):
    try:
        rows = list(csv.reader(StringIO(text.lstrip("\ufeff")), strict=True))
    except csv.Error as error:
        raise ValueError(f"CSVの引用符・改行を確認してください: {error}") from error
    section, headers, records = None, None, []
    for line_number, row in enumerate(rows, 1):
        if not row or not any(cell.strip() for cell in row):
            continue
        if len(row) == 1 and row[0].strip() in ("=== Session ===", "=== QuestionResult ==="):
            section = "questions" if "QuestionResult" in row[0] else "session"
            headers = None
            continue
        if section == "session":
            continue
        if headers is None:
            headers = [cell.strip() for cell in row]
            if len(headers) != len(set(headers)):
                raise ValueError("CSVの列名が重複しています。")
            if not REQUIRED.issubset(headers):
                missing = ", ".join(sorted(REQUIRED - set(headers)))
                raise ValueError(f"QuestionResult.csv または統合Raw CSVを指定してください。必要な列: {missing}")
            continue
        if len(row) != len(headers):
            raise ValueError(f"CSV {line_number}行目の列数が見出しと一致しません。")
        records.append(dict(zip(headers, row)))
        if len(records) > MAX_ROWS:
            raise ValueError(f"1ファイルの取込上限は{MAX_ROWS:,}行です。")
    if not records:
        raise ValueError("QuestionResultのデータ行がありません。")
    return records


def boolean(value):
    if isinstance(value, bool):
        return value
    token = str(value).strip().lower()
    if token in ("true", "1"):
        return True
    if token in ("false", "0"):
        return False
    raise ValueError("TRUE / FALSE を指定してください。")


def normalize_records(raw_records, fallback_student="", confirm_single_student=False):
    if len(raw_records) > MAX_ROWS:
        raise ValueError(f"まとめて取り込める上限は{MAX_ROWS:,}行です。")
    fallback_student = fallback_student.strip()
    if fallback_student and not confirm_single_student:
        raise ValueError("学習者IDを補う場合は、空欄の行が同じ1人のログであることを確認してください。")
    records, excluded, seen = [], [], {}
    for index, raw in enumerate(raw_records, 1):
        def exclude(reason):
            excluded.append({"Row": index, "ResultID": raw.get("ResultID", ""), "Reason": reason})
        try:
            answered = boolean(raw.get("IsAnswered"))
            correct_value = raw.get("IsCorrect", "")
            correct = boolean(correct_value) if answered or str(correct_value).strip() else False
            if not answered and correct:
                raise ValueError("未回答なのにIsCorrectがTRUEです。")
            student = str(raw.get("StudentID") or "").strip() or fallback_student
            identifiers = {name: str(raw.get(name) or "").strip() for name in ("ResultID", "SessionID", "SkillID")}
            if not all(identifiers.values()):
                exclude("ResultID / SessionID / SkillIDが空欄" if answered else "未回答（BKT更新なし）")
                continue
            timestamp_text = str(raw.get("AnsweredAt") or "").strip()
            timestamp = None
            if answered or timestamp_text:
                timestamp = datetime.fromisoformat(timestamp_text.replace("Z", "+00:00"))
                if timestamp.utcoffset() is None:
                    raise ValueError("AnsweredAtにはタイムゾーンが必要です。")
            sequence = str(raw.get("QuestionSequence") or "").strip()
            if sequence and (not sequence.isdigit() or int(sequence) < 1):
                raise ValueError("QuestionSequenceは正の整数にしてください。")
            record = {
                **raw, **identifiers, "StudentID": student,
                "IsAnswered": answered, "IsCorrect": correct,
                "AnsweredAt": timestamp.astimezone(timezone.utc).isoformat() if timestamp else None,
                "QuestionSequence": int(sequence) if sequence else None,
                "Mode": str(raw.get("Mode") or "Unknown").strip(),
                "QuestionID": str(raw.get("QuestionID") or "").strip(),
            }
        except (ValueError, TypeError) as error:
            exclude(f"不正な観測: {error}")
            continue
        result_id = record["ResultID"]
        if result_id in seen:
            previous = seen[result_id]
            if any(previous.get(key) != record.get(key) for key in OBSERVATION_KEYS):
                raise ValueError(f"ResultID {result_id} の回答情報が競合しています。異なる版のログを確認してください。")
            exclude("回答情報が一致する重複（付随情報は最初の値を使用）")
            continue
        seen[result_id] = record
        if not answered:
            exclude("未回答（BKT更新なし）")
        elif not student:
            exclude("StudentIDが空欄")
        else:
            records.append(record)
    return {"records": records, "excluded": excluded, "input_count": len(raw_records)}
