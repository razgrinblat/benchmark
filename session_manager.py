import time
import queue
import logging
import threading
from typing import List, Dict, Optional, Any
from queue import Queue

from metrics_manager import MetricsManager, SessionMetrics
from events import (
    TransferSuccessEvent,
    TransferFailedEvent,
    LogMonitorErrorEvent,
    FileGenerationFailedEvent,
)

logger = logging.getLogger(__name__)

class SessionManager:
    """
    Manages the lifecycle of a benchmark session.
    Consumes events from an event queue, tracks expected file statuses,
    handles dynamic timeouts, and updates metrics.
    """

    def __init__(
        self,
        session_name: str,
        expected_files: List[str],
        total_bytes: int,
        events_queue: Queue,
        metrics_manager: MetricsManager,
        metrics: SessionMetrics,
        timeout: float,
    ):
        self.session_name = session_name
        self.expected_files = expected_files
        self.total_bytes = total_bytes
        self.events_queue = events_queue
        self.metrics_manager = metrics_manager
        self.metrics = metrics
        self.timeout = timeout

        self.file_status: Dict[str, str] = {f: "Pending" for f in expected_files}
        self.start_time = None
        self.is_successful = False
        self.validation_status = "PENDING"
        self.error_message: Optional[str] = None

        self.finished_event = threading.Event()
        self.thread = None

    def start(self) -> None:
        """Starts the SessionManager consumer thread."""
        logger.info(f"Starting SessionManager for session '{self.session_name}' (Timeout: {self.timeout}s)")
        self.start_time = time.perf_counter()
        self.thread = threading.Thread(target=self._consume_loop, daemon=True)
        self.thread.start()

    def _consume_loop(self) -> None:
        try:
            while not self.finished_event.is_set():
                elapsed = time.perf_counter() - self.start_time
                remaining = self.timeout - elapsed
                if remaining <= 0:
                    logger.warning(f"SessionManager dynamic timeout of {self.timeout}s reached.")
                    self._finalize(
                        is_successful=False,
                        validation_status="TIMEOUT",
                        error_message=f"Session timed out after {self.timeout} seconds."
                    )
                    break
                try:
                    event = self.events_queue.get(timeout=min(1.0, max(0.01, remaining)))
                except queue.Empty:
                    continue

                self._handle_event(event)

                if self.finished_event.is_set():
                    break

                if self._check_all_completed():
                    passed = all(status == "Passed" for status in self.file_status.values())
                    status = "PASSED" if passed else "FAILED"
                    err_msg = None if passed else f"Some files failed transfer: {self._get_failed_files_summary()}"
                    self._finalize(is_successful=passed, validation_status=status, error_message=err_msg)
                    break
        except Exception as exc:
            logger.exception("Exception in SessionManager consume loop")
            self._finalize(
                is_successful=False,
                validation_status="ERROR",
                error_message=f"Internal SessionManager error: {exc}"
            )

    def _handle_event(self, event: Any) -> None:
        logger.debug(f"SessionManager handling event: {event}")
        if isinstance(event, TransferSuccessEvent):
            if event.filename in self.file_status:
                self.file_status[event.filename] = "Passed"
                logger.info(f"File '{event.filename}' transfer passed.")
            else:
                logger.warning(f"Received TransferSuccessEvent for unexpected file: '{event.filename}'")

        elif isinstance(event, TransferFailedEvent):
            if event.filename in self.file_status:
                self.file_status[event.filename] = "Failed"
                logger.error(f"File '{event.filename}' transfer failed: {event.reason}")
            else:
                logger.warning(f"Received TransferFailedEvent for unexpected file: '{event.filename}'")

        elif isinstance(event, LogMonitorErrorEvent):
            logger.error(f"LogMonitor error event: {event.reason}")
            self._finalize(
                is_successful=False,
                validation_status="ERROR",
                error_message=f"LogMonitor error: {event.reason}"
            )

        elif isinstance(event, FileGenerationFailedEvent):
            logger.error(f"File generation failure event: {event.reason}")
            self._finalize(
                is_successful=False,
                validation_status="ERROR",
                error_message=f"File generation failed: {event.reason}"
            )

    def _check_all_completed(self) -> bool:
        return all(status in ("Passed", "Failed") for status in self.file_status.values())

    def _get_failed_files_summary(self) -> str:
        failed_files = [f for f, status in self.file_status.items() if status == "Failed"]
        return ", ".join(failed_files)

    def _finalize(self, is_successful: bool, validation_status: str, error_message: Optional[str]) -> None:
        self.is_successful = is_successful
        self.validation_status = validation_status
        self.error_message = error_message
        self.finished_event.set()

    def wait_until_finished(self) -> dict:
        """
        Blocks the calling thread until the session completes or times out.
        Finalizes metrics tracking upon completion.
        """
        self.finished_event.wait()
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None

        # Record completion metrics
        self.metrics_manager.finish_session(
            metrics=self.metrics,
            total_files=len(self.expected_files),
            total_bytes=self.total_bytes,
            is_successful=self.is_successful,
            validation_status=self.validation_status,
            error_message=self.error_message
        )

        return {
            "is_successful": self.is_successful,
            "validation_status": self.validation_status,
            "error_message": self.error_message,
        }
