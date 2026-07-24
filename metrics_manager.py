import time
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SessionMetrics:
    session_name: str
    start_time: float
    end_time: Optional[float] = None
    duration_seconds: float = 0.0
    total_files: int = 0
    total_bytes: int = 0
    throughput_mbps: float = 0.0
    is_successful: bool = False
    validation_status: str = "PENDING"
    error_message: Optional[str] = None


class MetricsManager:
    """
    Manages and calculates performance metrics for test sessions.
    """

    def __init__(self, test_name: str) -> None:
        self.test_name = test_name
        self.session_metrics: list[SessionMetrics] = []

    def start_session(self, session_name: str) -> SessionMetrics:
        """Starts timing and metric tracking for a session."""
        metrics = SessionMetrics(
            session_name=session_name,
            start_time=time.perf_counter(),
        )
        self.session_metrics.append(metrics)
        logger.info(f"Started metrics collection for session '{session_name}' in test '{self.test_name}'")
        return metrics

    def finish_session(
        self,
        metrics: SessionMetrics,
        total_files: int,
        total_bytes: int,
        is_successful: bool,
        validation_status: str,
        error_message: Optional[str] = None,
    ) -> None:
        """Finalizes timing and records throughput for a completed session."""
        metrics.end_time = time.perf_counter()
        metrics.duration_seconds = max(0.001, metrics.end_time - metrics.start_time)
        metrics.total_files = total_files
        metrics.total_bytes = total_bytes
        metrics.is_successful = is_successful
        metrics.validation_status = validation_status
        metrics.error_message = error_message

        # Calculate throughput in Megabits per second (Mbps) and MB/s
        mb = total_bytes / (1024 * 1024)
        metrics.throughput_mbps = (mb * 8) / metrics.duration_seconds

        logger.info(
            f"Completed session '{metrics.session_name}': "
            f"Duration={metrics.duration_seconds:.2f}s, "
            f"Throughput={metrics.throughput_mbps:.2f} Mbps, "
            f"Success={is_successful}"
        )

    def get_all_metrics(self) -> list[SessionMetrics]:
        return self.session_metrics
