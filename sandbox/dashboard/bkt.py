"""Classic binary BKT with explicit, assumed parameters; raw records remain unchanged."""
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib
import json
import math

MODEL_VERSION = "bkt-classic-v1"


@dataclass(frozen=True)
class BKTParameters:
    p_l0: float = 0.2
    p_t: float = 0.1
    p_g: float = 0.25
    p_s: float = 0.1

    def __post_init__(self):
        for name, value in asdict(self).items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} は0〜1の有限な数値で指定してください。")
            object.__setattr__(self, name, float(value))
        if self.p_g + self.p_s >= 1:
            raise ValueError("Guess + Slip は1未満にしてください。")

    def parameter_id(self, skill_id):
        payload = json.dumps([MODEL_VERSION, skill_id, asdict(self)], sort_keys=True)
        return "BKTP_" + hashlib.sha256(payload.encode()).hexdigest()[:16]


def update(prior, correct, parameters):
    """Return observation posterior, then mastery after the learning transition."""
    if not isinstance(correct, bool):
        raise ValueError("正誤はboolで指定してください。")
    if isinstance(prior, bool) or not isinstance(prior, (int, float)) or not math.isfinite(prior) or not 0 <= prior <= 1:
        raise ValueError("事前確率は0〜1にしてください。")
    predicted_correct = prior * (1 - parameters.p_s) + (1 - prior) * parameters.p_g
    likelihood_known = 1 - parameters.p_s if correct else parameters.p_s
    likelihood_unknown = parameters.p_g if correct else 1 - parameters.p_g
    denominator = prior * likelihood_known + (1 - prior) * likelihood_unknown
    if denominator == 0:
        raise ValueError("観測の確率が0になるパラメータです。Guess / Slip / 初期値を見直してください。")
    posterior = prior * likelihood_known / denominator
    after_learning = posterior + (1 - posterior) * parameters.p_t
    return predicted_correct, posterior, after_learning


def estimate(records, defaults=None, by_skill=None):
    """One chain per StudentID/SkillID, ordered by actual answer timestamps.

    All included modes use the same configured transition rule. No forgetting,
    automatic parameter fitting, or use of self-reported confidence is applied.
    """
    defaults = defaults or BKTParameters()
    by_skill = by_skill or {}
    states, history, parameter_rows = {}, [], {}
    ordered = sorted((r for r in records if r["IsAnswered"] is True), key=lambda r: (
        r["StudentID"], r["SkillID"], datetime.fromisoformat(r["AnsweredAt"]),
        r["SessionID"], r.get("QuestionSequence") or 0, r["ResultID"],
    ))
    for record in ordered:
        if record["IsAnswered"] is not True:
            continue
        skill_id = record["SkillID"]
        parameters = by_skill.get(skill_id, defaults)
        key = (record["StudentID"], skill_id)
        previous = states.get(key)
        prior = previous["PMastery"] if previous else parameters.p_l0
        predicted, posterior, mastery = update(prior, record["IsCorrect"], parameters)
        parameter_id = parameters.parameter_id(skill_id)
        parameter_rows[skill_id] = {
            "BKTParamID": parameter_id, "SkillID": skill_id,
            "P_L0": parameters.p_l0, "P_T": parameters.p_t,
            "P_G": parameters.p_g, "P_S": parameters.p_s,
            "ModelVersion": MODEL_VERSION, "ParameterSource": "manual_assumption",
        }
        step = (previous["Attempts"] if previous else 0) + 1
        row = {
            "StudentID": key[0], "SkillID": skill_id,
            "SkillName": record.get("SkillName") or skill_id,
            "SessionID": record["SessionID"], "ResultID": record["ResultID"],
            "QuestionID": record.get("QuestionID"), "Mode": record.get("Mode"),
            "AnsweredAt": record["AnsweredAt"], "AttemptIndex": step,
            "IsCorrect": record["IsCorrect"], "PBefore": prior,
            "PredictedCorrect": predicted, "PAfterObservation": posterior,
            "PAfterLearning": mastery,
            "PNextCorrect": mastery * (1 - parameters.p_s) + (1 - mastery) * parameters.p_g,
            "BKTParamID": parameter_id, "ModelVersion": MODEL_VERSION,
        }
        history.append(row)
        states[key] = {
            "StudentID": key[0], "SkillID": skill_id, "SkillName": row["SkillName"],
            "PMastery": mastery, "PAfterObservation": posterior,
            "PNextCorrect": row["PNextCorrect"], "Attempts": step,
            "CorrectCount": (previous["CorrectCount"] if previous else 0) + int(record["IsCorrect"]),
            "LastAnsweredAt": record["AnsweredAt"], "LastResultID": record["ResultID"],
            "BKTParamID": parameter_id, "ModelVersion": MODEL_VERSION,
        }
    return {"parameters": list(parameter_rows.values()), "history": history, "states": list(states.values())}
