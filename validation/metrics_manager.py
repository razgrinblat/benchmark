import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from core.events import TransferSuccessEvent, TransferFailedEvent

logger = logging.getLogger(__name__)


@dataclass
class SessionMetrics:
    session_name: str
    total_files: int = 0
    failed_files: int = 0
    total_bytes: int = 0
    session_duration_seconds: float = 0.0
    session_throughput_mbps: float = 0.0
    avg_file_throughput_mbps: float = 0.0
    max_file_transfer_time_ms: int = 0
    min_file_transfer_time_ms: int = 0
    is_successful: bool = False
    validation_status: str = "PENDING"
    error_message: Optional[str] = None


class MetricsManager:
    """
    Incrementally accumulates performance metrics for a single test session
    as transfer events arrive, one at a time — no event list is retained.
    """

    def __init__(self, session_name: str, file_size_bytes: int) -> None:
        self.session_name = session_name
        self.file_size_bytes = file_size_bytes

        self._success_count = 0
        self._failure_reasons: list[str] = []

        self._first_event_timestamp: Optional[datetime] = None
        self._first_event_transfer_time_ms: int = 0
        self._last_event_timestamp: Optional[datetime] = None

        self._max_transfer_time_ms: int = 0
        self._min_transfer_time_ms: Optional[int] = None
        self._sum_per_file_throughput_mbps: float = 0.0

    def record_event(self, event) -> None:
        """Feeds a single transfer event into the running aggregates. O(1), no storage."""
        if isinstance(event, TransferSuccessEvent):
            self._record_success(event)
        elif isinstance(event, TransferFailedEvent):
            self._failure_reasons.append(f"{event.filename}: {event.reason}")

    def _record_success(self, event: TransferSuccessEvent) -> None:
        self._success_count += 1

        if self._first_event_timestamp is None:
            self._first_event_timestamp = event.timestamp
            self._first_event_transfer_time_ms = event.transfer_time_ms
        self._last_event_timestamp = event.timestamp

        self._max_transfer_time_ms = max(self._max_transfer_time_ms, event.transfer_time_ms)
        self._min_transfer_time_ms = (
            event.transfer_time_ms
            if self._min_transfer_time_ms is None
            else min(self._min_transfer_time_ms, event.transfer_time_ms)
        )

        mbits_per_file = (self.file_size_bytes * 8) / (1024 * 1024)
        transfer_time_s = max(event.transfer_time_ms / 1000, 0.001)
        self._sum_per_file_throughput_mbps += mbits_per_file / transfer_time_s

    def finalize(self) -> SessionMetrics:
        """Builds the final SessionMetrics from everything accumulated so far."""
        total_bytes = self._success_count * self.file_size_bytes
        is_successful = self._success_count > 0 and not self._failure_reasons
        validation_status = "PASSED" if is_successful else "FAILED"

        session_duration_seconds, session_throughput_mbps = self._calculate_session_throughput(total_bytes)
        avg_file_throughput_mbps = (
            self._sum_per_file_throughput_mbps / self._success_count if self._success_count else 0.0
        )

        metrics = SessionMetrics(
            session_name=self.session_name,
            total_files=self._success_count,
            failed_files=len(self._failure_reasons),
            total_bytes=total_bytes,
            session_duration_seconds=session_duration_seconds,
            session_throughput_mbps=session_throughput_mbps,
            avg_file_throughput_mbps=avg_file_throughput_mbps,
            max_file_transfer_time_ms=self._max_transfer_time_ms,
            min_file_transfer_time_ms=self._min_transfer_time_ms or 0,
            is_successful=is_successful,
            validation_status=validation_status,
            error_message="; ".join(self._failure_reasons) or None,
        )

        logger.info(
            f"Session '{self.session_name}': {validation_status}, "
            f"{metrics.total_files} files, {session_throughput_mbps:.2f} Mbps session, "
            f"{avg_file_throughput_mbps:.2f} Mbps avg/file"
        )
        return metrics

    def _calculate_session_throughput(self, total_bytes: int) -> tuple[float, float]:
        if self._first_event_timestamp is None or self._last_event_timestamp is None:
            return 0.0, 0.0

        session_start = self._first_event_timestamp - timedelta(milliseconds=self._first_event_transfer_time_ms)
        duration_seconds = max((self._last_event_timestamp - session_start).total_seconds(), 0.001)

        mbits = (total_bytes * 8) / (1024 * 1024)
        throughput_mbps = mbits / duration_seconds
        return duration_seconds, throughput_mbps
