import tempfile
import unittest
from pathlib import Path

from config import Settings
from evaluation.run_eval import run_accuracy_evaluation, run_scale_benchmark


class EvaluationTest(unittest.TestCase):
    def setUp(self):
        self.settings = Settings.default()

    def test_accuracy_evaluation_writes_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            summary = run_accuracy_evaluation(self.settings, output_dir)

            self.assertIn("Evaluation Summary", summary)
            self.assertTrue((output_dir / "evaluation_results.csv").exists())
            self.assertTrue((output_dir / "evaluation_summary.md").exists())

    def test_scale_benchmark_writes_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            summary = run_scale_benchmark(self.settings, output_dir, scale=2)

            self.assertIn("Scale Test Summary", summary)
            self.assertTrue((output_dir / "scale_test_results.csv").exists())
            self.assertTrue((output_dir / "scale_test_summary.md").exists())


if __name__ == "__main__":
    unittest.main()
