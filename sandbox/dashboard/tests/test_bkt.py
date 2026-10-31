import copy
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bkt import BKTParameters, estimate, update
from learning_data import normalize_records, parse_question_csv
from demo_data import sample_records


class BKTTests(unittest.TestCase):
    def test_known_correct_and_incorrect_updates(self):
        parameters = BKTParameters()
        predicted, posterior, learned = update(0.2, True, parameters)
        self.assertAlmostEqual(predicted, 0.38)
        self.assertAlmostEqual(posterior, 0.18 / 0.38)
        self.assertAlmostEqual(learned, posterior + (1 - posterior) * 0.1)
        _, posterior, learned = update(0.2, False, parameters)
        self.assertAlmostEqual(posterior, 0.02 / 0.62)
        self.assertAlmostEqual(learned, 0.12903225806451613)

    def test_parameter_validation_and_impossible_observations(self):
        for kwargs in [{"p_l0": math.nan}, {"p_t": -0.1}, {"p_g": True}, {"p_s": 2}, {"p_g": 0.8, "p_s": 0.2}]:
            with self.assertRaises(ValueError):
                BKTParameters(**kwargs)
        with self.assertRaises(ValueError):
            update(0, True, BKTParameters(p_g=0))
        with self.assertRaises(ValueError):
            update(0.2, "FALSE", BKTParameters())
        self.assertEqual(BKTParameters(p_t=0).parameter_id("S"), BKTParameters(p_t=0.0).parameter_id("S"))

    def test_chronology_independence_no_mutation_and_traceable_parameters(self):
        records = normalize_records(sample_records())["records"]
        original = copy.deepcopy(records)
        result = estimate(list(reversed(records)))
        self.assertEqual(records, original)
        self.assertEqual(len(result["states"]), 4)
        self.assertEqual(len(result["history"]), 24)
        for state in result["states"]:
            self.assertEqual(state["Attempts"], 6)
            self.assertGreaterEqual(state["PMastery"], 0)
            self.assertLessEqual(state["PMastery"], 1)
        for student in ["DEMO-A", "DEMO-B"]:
            for skill in ["SK_DEMO_READING", "SK_DEMO_GRAMMAR"]:
                chain = [r for r in result["history"] if r["StudentID"] == student and r["SkillID"] == skill]
                self.assertEqual([r["AttemptIndex"] for r in chain], list(range(1, 7)))
                self.assertEqual(chain[0]["PBefore"], 0.2)
                self.assertEqual(chain[1]["PBefore"], chain[0]["PAfterLearning"])
        ids = {r["BKTParamID"] for r in result["parameters"]}
        self.assertTrue(all(r["BKTParamID"] in ids for r in result["history"]))

    def test_skill_parameters_no_learning_and_unanswered(self):
        records = normalize_records(sample_records())["records"][:2]
        result = estimate(records, by_skill={records[0]["SkillID"]: BKTParameters(p_t=0)})
        self.assertTrue(all(r["PAfterLearning"] == r["PAfterObservation"] for r in result["history"]))
        unanswered = {"IsAnswered": False}
        self.assertEqual(estimate([unanswered])["history"], [])


class IngestionTests(unittest.TestCase):
    def row(self, **updates):
        return {**sample_records()[0], **updates}

    def test_booleans_skips_and_identity_confirmation(self):
        records = [self.row(IsCorrect="FALSE"), self.row(ResultID="skip", IsAnswered="FALSE", IsCorrect="FALSE", AnsweredAt=""), self.row(ResultID="missing", StudentID=""), self.row(ResultID="bad", IsCorrect="maybe")]
        result = normalize_records(records)
        self.assertEqual(len(result["records"]), 1)
        self.assertIs(result["records"][0]["IsCorrect"], False)
        self.assertEqual(len(result["excluded"]), 3)
        with self.assertRaises(ValueError):
            normalize_records([self.row(StudentID="")], "student-a")
        result = normalize_records([self.row(StudentID="")], "student-a", True)
        self.assertEqual(result["records"][0]["StudentID"], "student-a")

    def test_duplicates_post_review_changes_and_conflicts(self):
        row = self.row()
        result = normalize_records([row, {**row, "UnderstandingLevel": "3", "ReviewFlag": "TRUE"}])
        self.assertEqual(len(result["records"]), 1)
        self.assertEqual(len(result["excluded"]), 1)
        with self.assertRaises(ValueError):
            normalize_records([row, {**row, "IsCorrect": not row["IsCorrect"]}])
        with self.assertRaises(ValueError):
            normalize_records([row, {**row, "IsAnswered": False, "IsCorrect": False, "AnsweredAt": ""}])

    def test_timestamps_are_required_and_utc_normalized(self):
        result = normalize_records([self.row(AnsweredAt="2026-10-01T18:00:00+09:00"), self.row(ResultID="naive", AnsweredAt="2026-10-01T18:00:00"), self.row(ResultID="blank", AnsweredAt="")])
        self.assertEqual(result["records"][0]["AnsweredAt"], "2026-10-01T09:00:00+00:00")
        self.assertEqual(len(result["excluded"]), 2)

    def test_standalone_unified_bom_quotes_and_invalid_csv(self):
        header = "ResultID,SessionID,SkillID,IsAnswered,IsCorrect,AnsweredAt,QuestionText\r\n"
        body = 'R1,S1,K1,TRUE,FALSE,2026-10-01T09:00:00Z,"a,b\n""quoted"""\r\n'
        standalone = parse_question_csv("\ufeff" + header + body)
        unified = parse_question_csv("\ufeff=== Session ===\r\nSessionID,StudentID\r\nS1,A\r\n=== QuestionResult ===\r\n" + header + body)
        self.assertEqual(standalone, unified)
        self.assertEqual(standalone[0]["QuestionText"], 'a,b\n"quoted"')
        for text in ["a,b\n1,2\n", header + '"unclosed', header + "1,2,3\n"]:
            with self.assertRaises(ValueError):
                parse_question_csv(text)


if __name__ == "__main__":
    unittest.main()
