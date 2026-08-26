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
        Saves human readable summary TXT file.
        """
        # Write human readable summary TXT file
        summary_txt_file = self.results_dir / f"{self.test_name}_summary.txt"
        with open(summary_txt_file, "w", encoding="utf-8") as f:
            f.write(f"=== BENCHMARK TEST SUMMARY: {self.test_name} ===\n\n")
            for m in session_metrics:
                f.write(f"Session: {m.session_name}\n")
                f.write(f"  Status              : {m.validation_status}\n")
                f.write(f"  Session Duration    : {m.session_duration_seconds:.2f} s\n")
                f.write(f"  Total Files         : {m.total_files}\n")
                f.write(f"  Failed Files        : {m.failed_files}\n")
                f.write(f"  Total Bytes         : {m.total_bytes:,} bytes\n")
                f.write(f"  Session Throughput  : {m.session_throughput_mbps:.2f} Mbps\n")
                f.write(f"  Avg File Throughput : {m.avg_file_throughput_mbps:.2f} Mbps\n")
                f.write(f"  Min Transfer Time   : {m.min_file_transfer_time_ms} ms\n")
                f.write(f"  Max Transfer Time   : {m.max_file_transfer_time_ms} ms\n")
                if m.error_message:
                    f.write(f"  Error               : {m.error_message}\n")
                f.write("-" * 50 + "\n")

        logger.info(f"Saved test results summary for '{self.test_name}' to {summary_txt_file}")
        return summary_txt_file
