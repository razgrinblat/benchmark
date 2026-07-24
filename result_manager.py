import json
import logging
from pathlib import Path
from dataclasses import asdict
from metrics_manager import SessionMetrics

logger = logging.getLogger(__name__)


class ResultManager:
    """
    Handles aggregation, formatting, and persistence of benchmark test results.
    """

    def __init__(self, test_name: str, results_dir: Path) -> None:
        self.test_name = test_name
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def save_test_results(self, session_metrics: list[SessionMetrics]) -> Path:
        """
        Saves compiled test session results to a JSON summary file.
        """
        output_file = self.results_dir / f"{self.test_name}_results.json"
        
        report_data = {
            "test_name": self.test_name,
            "session_count": len(session_metrics),
            "sessions": [asdict(m) for m in session_metrics],
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=4)

        # Also write human readable summary TXT file
        summary_txt_file = self.results_dir / f"{self.test_name}_summary.txt"
        with open(summary_txt_file, "w", encoding="utf-8") as f:
            f.write(f"=== BENCHMARK TEST SUMMARY: {self.test_name} ===\n\n")
            for m in session_metrics:
                f.write(f"Session: {m.session_name}\n")
                f.write(f"  Status       : {m.validation_status}\n")
                f.write(f"  Duration     : {m.duration_seconds:.2f} s\n")
                f.write(f"  Files        : {m.total_files}\n")
                f.write(f"  Bytes        : {m.total_bytes:,} bytes\n")
                f.write(f"  Throughput   : {m.throughput_mbps:.2f} Mbps\n")
                if m.error_message:
                    f.write(f"  Error        : {m.error_message}\n")
                f.write("-" * 50 + "\n")

        logger.info(f"Saved test results for '{self.test_name}' to {output_file}")
        return output_file
