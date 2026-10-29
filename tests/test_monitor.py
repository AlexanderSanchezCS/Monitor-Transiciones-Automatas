import json
import unittest
from pathlib import Path

from monitor.automata import ALPHABET, TRANSITIONS, accepts, minimize_dfa
from monitor.monitor import calculate_metrics, load_dataset_sessions


ROOT = Path(__file__).resolve().parents[1]


class MonitorTests(unittest.TestCase):
    def test_formal_json_matches_python_afd(self):
        formal = json.loads((ROOT / "automatas" / "afd_minimo.json").read_text(encoding="utf-8"))
        self.assertEqual(formal["alphabet"], list(ALPHABET))
        self.assertEqual(formal["transitions"], TRANSITIONS)
        self.assertEqual(sum(len(row) for row in formal["transitions"].values()), 32)

    def test_afd_examples(self):
        self.assertTrue(accepts("BPBC"))
        self.assertTrue(accepts("RBPC"))
        self.assertFalse(accepts("BPC"))
        self.assertFalse(accepts(""))
        self.assertEqual(load_dataset_sessions(ROOT, "validation")[0]["status"], "Normal")

    def test_dataset_metrics_match_key(self):
        validation = load_dataset_sessions(ROOT, "validation")
        test = load_dataset_sessions(ROOT, "test")
        self.assertEqual(len(validation), 300)
        self.assertEqual(len(test), 60)
        self.assertEqual(calculate_metrics(validation)["vp"], 54)
        self.assertEqual(calculate_metrics(test)["vp"], 11)
        self.assertTrue(all(session["match"] for session in test))

    def test_minimizer_returns_unique_states(self):
        minimized = minimize_dfa(
            ["A", "B"],
            ["x"],
            {"A": {"x": "B"}, "B": {"x": "B"}},
            "A",
            ["B"],
        )
        self.assertEqual(len(minimized["states"]), len(set(minimized["states"])))


if __name__ == "__main__":
    unittest.main()
