import tempfile
import unittest
from pathlib import Path

from config import Settings
from evaluation.run_eval import (
    generate_synthetic_dataset,
    run_accuracy_evaluation,
    run_agent_trace_evaluation,
    run_card_evaluation,
    run_event_evaluation,
    run_full_evaluation,
    run_graphrag_evaluation,
    run_robustness_evaluation,
    run_safety_evaluation,
    run_scale_benchmark,
)


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

    def test_robustness_evaluation_writes_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            summary = run_robustness_evaluation(self.settings, output_dir)

            self.assertIn("Robustness Summary", summary)
            self.assertTrue((output_dir / "robustness_results.csv").exists())

    def test_graphrag_evaluation_writes_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            summary = run_graphrag_evaluation(self.settings, output_dir, scale=2)

            self.assertIn("GraphRAG Harness Summary", summary)
            self.assertTrue((output_dir / "graphrag_results.csv").exists())

    def test_agent_trace_evaluation_writes_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            summary = run_agent_trace_evaluation(self.settings, output_dir)

            self.assertIn("Agent Trace Harness Summary", summary)
            self.assertTrue((output_dir / "agent_trace_results.csv").exists())

    def test_card_event_and_safety_evaluations_write_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            card_summary = run_card_evaluation(self.settings, output_dir / "cards")
            event_summary = run_event_evaluation(self.settings, output_dir / "events")
            safety_summary = run_safety_evaluation(self.settings, output_dir / "safety")

            self.assertIn("Card Harness Summary", card_summary)
            self.assertIn("Event Harness Summary", event_summary)
            self.assertIn("Safety Harness Summary", safety_summary)

    def test_full_evaluation_writes_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            summary = run_full_evaluation(self.settings, output_dir, scale=2)

            self.assertIn("Full Harness Summary", summary)
            self.assertTrue((output_dir / "full_harness_summary.md").exists())

    def test_generate_synthetic_dataset_creates_scaled_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "generated"
            generate_synthetic_dataset(self.settings.data_dir, output_dir, scale=2)

            self.assertTrue((output_dir / "docs").exists())
            self.assertTrue((output_dir / "tasks" / "tasks.json").exists())


if __name__ == "__main__":
    unittest.main()
