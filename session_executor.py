import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Any
from queue import Queue

from dut import Dut
from config_manager import ConfigurationManager
from file_generator import FileGenerator, _SCALE_TO_BYTES
from session_file_manager import SessionFileManager
from integrity_validator import IntegrityValidator
from metrics_manager import MetricsManager, SessionMetrics
from logger import setup_worker_logging
from log_monitor import LogMonitor
from session_manager import SessionManager
from events import FileGenerationFailedEvent

logger = logging.getLogger(__name__)


class SessionExecutor:
    """
    Executes a single benchmark session following an event-driven asynchronous lifecycle:
      1. Prepare session directories
      2. Start LogMonitor and SessionManager asynchronously in background threads
      3. Generate files in Tx and trigger the DUT transfer
      4. Wait for SessionManager to signal completion or dynamic timeout
      5. Stop LogMonitor and collect logs
      6. Perform final file integrity validation
    """

    def __init__(
        self,
        tx_dut: Dut,
        rx_dut: Dut,
        config_manager: ConfigurationManager,
        tx_dir: Path,
        rx_dir: Path,
        results_dir: Path,
    ) -> None:
        self.tx = tx_dut
        self.rx = rx_dut
        self.config_manager = config_manager
        self.tx_dir = tx_dir
        self.rx_dir = rx_dir
        self.results_dir = results_dir

        self.file_generator = FileGenerator()
        self.integrity_validator = IntegrityValidator()

    def execute_session(
        self,
        test_name: str,
        session_str: str,
        metrics_manager: MetricsManager,
    ) -> SessionMetrics:
        """Runs the asynchronous event-driven session lifecycle."""
        session_info = self.config_manager.parse_session_string(session_str)
        session_name = session_info["session_name"]

        metrics = metrics_manager.start_session(session_name)
        session_file_mgr = self._prepare_session_files(test_name, session_name)

        self._run_asynchronous_session(
            session_info=session_info,
            session_name=session_name,
            session_str=session_str,
            tx_dir=session_file_mgr.get_tx_dir(),
            rx_dir=session_file_mgr.get_rx_dir(),
            results_dir=session_file_mgr.get_results_dir(),
            metrics_manager=metrics_manager,
            metrics=metrics,
        )

        return metrics

    def _prepare_session_files(self, test_name: str, session_name: str) -> SessionFileManager:
        """Initializes and prepares local directory structure for the session."""
        session_file_mgr = SessionFileManager(
            tx_dir=self.tx_dir,
            rx_dir=self.rx_dir,
            results_dir=self.results_dir,
            test_name=test_name,
            session_name=session_name,
        )
        session_file_mgr.prepare_directories()
        return session_file_mgr

    def _run_asynchronous_session(
        self,
        session_info: dict,
        session_name: str,
        session_str: str,
        tx_dir: Path,
        rx_dir: Path,
        results_dir: Path,
        metrics_manager: MetricsManager,
        metrics: SessionMetrics,
    ) -> None:
        """Coordinates LogMonitor, FileGenerator, and SessionManager asynchronously."""
        file_setting = session_info.get("file_setting")
        if not file_setting:
            raise ValueError(f"No file setting found for session '{session_str}'")

        file_count = file_setting["file_count"]
        file_size = file_setting["file_size"]
        file_scale = file_setting["file_scale"].upper()

        size_in_bytes = file_size * _SCALE_TO_BYTES.get(file_scale, 1024)
        total_expected_bytes = file_count * size_in_bytes

        expected_filenames: list[str] = [f"{session_name}_{i + 1}.bin" for i in range(file_count)]

        # Dynamic timeout calculation: base of 30 seconds plus 1 second for every 2MB of payload
        dynamic_timeout = max(30.0, 10.0 + (total_expected_bytes / (1024 * 1024 * 2.0)))

        events_queue = Queue()

        # 1. Initialize and start LogMonitor and SessionManager
        log_monitor = LogMonitor(
            session_name=session_name,
            events_queue=events_queue,
            rx_dut=self.rx,
        )

        session_manager = SessionManager(
            session_name=session_name,
            expected_files=expected_filenames,
            total_bytes=total_expected_bytes,
            events_queue=events_queue,
            metrics_manager=metrics_manager,
            metrics=metrics,
            timeout=dynamic_timeout,
        )

        log_monitor.start()
        session_manager.start()

        # Ensure SSH log monitor has started before writing files
        time.sleep(1)

        # 2. Generate files (catches error and publishes FileGenerationFailedEvent on exception)
        try:
            logger.info(f"Generating files for session '{session_name}' on Tx host...")
            self.file_generator.generate_files(
                target_dir=tx_dir,
                file_setting=file_setting,
                mode=session_info.get("mode"),
            )
            logger.info("Files generated successfully.")
        except Exception as exc:
            logger.exception("File generation failed")
            events_queue.put(FileGenerationFailedEvent(reason=str(exc), timestamp=datetime.now()))

        # 3. Wait for SessionManager to complete (signals finished_event)
        logger.info(f"Main thread waiting for SessionManager to finish (Timeout: {dynamic_timeout:.1f}s)...")
        result_summary = session_manager.wait_until_finished()
        logger.info(f"SessionManager finished. Result: {result_summary}")

        # 4. Stop LogMonitor
        log_monitor.stop()

        # 5. Post-validation: Validate file integrity directly between directories
        is_success = result_summary["is_successful"]
        validation_status = result_summary["validation_status"]
        error_msg = result_summary["error_message"]

        # Only validate filesystem matches if the run didn't hit error or timeout states
        if validation_status not in ("ERROR", "TIMEOUT"):
            try:
                val_result = self.integrity_validator.validate_session_files(tx_dir, rx_dir)
                if not val_result.is_valid:
                    is_success = False
                    validation_status = "FAILED"
                    error_msg = val_result.details
                else:
                    if is_success:
                        validation_status = "PASSED"
            except Exception as exc:
                logger.exception("File integrity validation failed due to exception")
                is_success = False
                validation_status = "ERROR"
                error_msg = f"Integrity validation error: {exc}"

            # Override the session metrics with the validated filesystem results
            metrics.is_successful = is_success
            metrics.validation_status = validation_status
            metrics.error_message = error_msg


# ----------------------------------------------------------------------
# Process Worker Context & Helper Functions
# ----------------------------------------------------------------------

class WorkerSessionContext:
    """Context manager for managing DUT connections and lifecycle inside a worker process."""

    def __init__(self, endpoint_settings: dict, session_str: str) -> None:
        self.endpoint_settings = endpoint_settings
        self.session_str = session_str
        self.tx_dut: Optional[Dut] = None
        self.rx_dut: Optional[Dut] = None

    def __enter__(self) -> Tuple[Dut, Dut]:
        self.tx_dut = Dut.from_config("Tx", self.endpoint_settings["tx"])
        self.rx_dut = Dut.from_config("Rx", self.endpoint_settings["rx"])

        logger.info(f"[Process Worker] Connecting SSH to Tx & Rx for session '{self.session_str}'")
        self.tx_dut.connect()
        self.rx_dut.connect()
        return self.tx_dut, self.rx_dut

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        for dut in (self.rx_dut, self.tx_dut):
            if dut:
                try:
                    dut.disconnect()
                except Exception as e:
                    logger.warning(f"Error disconnecting {dut.name} in session process '{self.session_str}': {e}")


def run_session_worker(
    test_name: str,
    session_str: str,
    endpoint_settings: dict,
    config_manager: ConfigurationManager,
    tx_dir: Path,
    rx_dir: Path,
    results_dir: Path,
    log_queue: Optional[Any] = None,
) -> SessionMetrics:
    """
    Top-level worker function for executing a benchmark session in a separate process.
    Instantiates process-isolated DUT instances using WorkerSessionContext.
    """
    setup_worker_logging(log_queue)
    with WorkerSessionContext(endpoint_settings, session_str) as (tx_dut, rx_dut):
        executor = SessionExecutor(
            tx_dut=tx_dut,
            rx_dut=rx_dut,
            config_manager=config_manager,
            tx_dir=tx_dir,
            rx_dir=rx_dir,
            results_dir=results_dir,
        )
        metrics_mgr = MetricsManager(test_name)
        return executor.execute_session(
            test_name=test_name,
            session_str=session_str,
            metrics_manager=metrics_mgr,
        )
