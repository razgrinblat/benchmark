import logging
import csv
from pathlib import Path
from dataclasses import asdict
from validation.metrics_manager import SessionMetrics

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
        Saves test results as a CSV file.
        """
        csv_file = self.results_dir / f"{self.test_name}_summary.csv"
        
        if not session_metrics:
            logger.warning(f"No session metrics to save for test '{self.test_name}'")
            return csv_file

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            fieldnames = [
                "session_name", "validation_status", "session_duration_seconds", 
                "total_files", "failed_files", "total_bytes", 
                "session_throughput_mbps", "avg_file_throughput_mbps", 
                "min_file_transfer_time_ms", "max_file_transfer_time_ms", "error_message"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for m in session_metrics:
                row = asdict(m)
                # Keep only the relevant fields
                filtered_row = {k: v for k, v in row.items() if k in fieldnames}
                
                # Format float values cleanly
                filtered_row["session_duration_seconds"] = f"{m.session_duration_seconds:.2f}"
                filtered_row["session_throughput_mbps"] = f"{m.session_throughput_mbps:.2f}"
                filtered_row["avg_file_throughput_mbps"] = f"{m.avg_file_throughput_mbps:.2f}"
                
                writer.writerow(filtered_row)

        logger.info(f"Saved test results summary for '{self.test_name}' to {csv_file}")
        return csv_file
