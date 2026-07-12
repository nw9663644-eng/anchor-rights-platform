import tempfile
import unittest
from pathlib import Path

from app import auth, storage
from app.data.content import QUESTIONS
from app.evaluator import evaluate_answers


class PlatformCoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        storage.DB_PATH = Path(self.temp.name) / "test.db"
        storage.DATABASE_URL = ""
        storage.USE_POSTGRES = False
        storage.init_db([], [])
        auth.init_auth()

    def tearDown(self):
        self.temp.cleanup()

    def test_scoring_model_has_expected_shape_and_maximum(self):
        self.assertEqual(len(QUESTIONS), 36)
        counts = {dimension: len([q for q in QUESTIONS if q["dimension"] == dimension]) for dimension in ("personal", "economic", "organizational", "risk")}
        self.assertEqual(counts, {"personal": 10, "economic": 9, "organizational": 7, "risk": 10})
        answers = {question["id"]: question["options"][0]["id"] for question in QUESTIONS}
        result = evaluate_answers(answers)
        self.assertEqual(result["totalScore"], 100)
        self.assertEqual(result["relationType"], "labor")

    def test_user_matters_are_isolated_and_evaluation_is_linked(self):
        first = auth.register_user("first@example.com", "第一用户", "Password123!")["user"]
        second = auth.register_user("second@example.com", "第二用户", "Password123!")["user"]
        matter = storage.save_matter({"title": "测试事项", "evaluation_id": "evaluation-1"}, first["id"])
        self.assertEqual(matter["evaluationId"], "evaluation-1")
        self.assertEqual(len(storage.list_matters(first["id"])), 1)
        self.assertEqual(len(storage.list_matters(second["id"])), 0)
        self.assertFalse(storage.matter_owned(matter["id"], second["id"]))
        storage.save_evaluation({}, {"totalScore": 0, "relationType": "business", "relationLabel": "纯平等民事商务合作关系", "gaps": []}, first["id"])
        evaluation_id = storage.list_evaluations(first["id"])[0]["id"]
        self.assertTrue(storage.evaluation_owned(evaluation_id, first["id"]))
        self.assertFalse(storage.evaluation_owned(evaluation_id, second["id"]))

    def test_high_risk_statistics_only_use_gap_count(self):
        user = auth.register_user("stats@example.com", "统计用户", "Password123!")["user"]
        storage.save_evaluation({}, {"totalScore": 90, "relationType": "labor", "relationLabel": "标准劳动关系", "gaps": []}, user["id"])
        self.assertEqual(storage.platform_stats(user["id"])["highRiskReports"], 0)

    def test_audit_log_records_actor_and_action(self):
        user = auth.register_user("audit@example.com", "审计用户", "Password123!")["user"]
        storage.log_action(user["id"], "新建事项", "matter", "matter-1", "测试事项")
        logs = storage.list_audit_logs()
        self.assertEqual(logs[0]["action"], "新建事项")
        self.assertEqual(logs[0]["userName"], "审计用户")


if __name__ == "__main__":
    unittest.main()
