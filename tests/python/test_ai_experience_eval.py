from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_DIR / "tests" / "python"))

import ai_experience_eval as experience  # noqa: E402


class AiExperienceEvalTests(unittest.TestCase):
    def test_dataset_covers_requested_quality_dimensions(self) -> None:
        cases = json.loads(experience.DEFAULT_CASES.read_text(encoding="utf-8"))
        categories = {case["category"] for case in cases}
        self.assertTrue({"persona", "relationship", "memory", "fact_reference", "puzzle_leak", "action", "terminology", "repetition"} <= categories)
        self.assertGreaterEqual(len(cases), 10)

    def test_case_score_checks_action_reference_and_terms(self) -> None:
        case = {
            "expected_action": "none",
            "required_all": ["41", "kPa"],
            "required_references": ["local:pressure"],
        }
        result = {
            "decision": {
                "reply": "表上是 41 kPa，我没有动阀。",
                "action": "none",
                "target": "",
                "referenced_ids": ["local:pressure"],
            }
        }
        scored = experience._score_case(case, result)
        self.assertTrue(scored["passed"])
        self.assertTrue(scored["checks"]["references"])

    def test_repetition_similarity_separates_copy_from_new_wording(self) -> None:
        copied = experience._similarity("两盏联锁灯都是红色。", "两盏联锁灯都是红色。")
        varied = experience._similarity("两盏联锁灯都是红色。", "四条走廊在我脚边汇合，舱门还锁着。")
        self.assertEqual(copied, 1.0)
        self.assertLess(varied, 0.5)

    def test_percentile_interpolates_small_samples(self) -> None:
        self.assertEqual(experience._percentile([100.0, 200.0, 300.0], 0.5), 200.0)
        self.assertEqual(experience._percentile([], 0.95), 0.0)


if __name__ == "__main__":
    unittest.main()
