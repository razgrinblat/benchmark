import time
import logging
import json
import tempfile
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Any
from queue import Queue
from dut import Dut
from dut_settings import DutPaths
from config_manager import ConfigurationManager
from file_generator import FileGenerator, _SCALE_TO_BYTES
from session_file_manager import SessionFileManager
from integrity_validator import IntegrityValidator
from metrics_manager import SessionMetrics
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
        results_dir: Path,
    ) -> None:
        self.tx = tx_dut
        self.rx = rx_dut
        self.config_manager = config_manager
        self.results_dir = results_dir
        self.dut_paths = DutPaths.load()

        self.file_generator = FileGenerator()
        self.integrity_validator = IntegrityValidator()

    def execute_session(
        self,
        test_name: str,
        session_str: str,
    ) -> SessionMetrics:
        """Runs the asynchronous event-driven session lifecycle."""
        session_info = self.config_manager.parse_session_string(session_str)
        session_name = session_info["session_name"]

        session_file_mgr = self._prepare_session_files(test_name, session_name)

        return self._run_asynchronous_session(
            session_info=session_info,
            session_name=session_name,
            session_str=session_str,
            tx_dir=session_file_mgr.get_tx_dir(),
            rx_dir=session_file_mgr.get_rx_dir(),
        )

    def _prepare_session_files(self, test_name: str, session_name: str) -> SessionFileManager:
        """Initializes and prepares local directory structure for the session."""
        session_file_mgr = SessionFileManager(
            tx_dut=self.tx,
            rx_dut=self.rx,
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
    ) -> SessionMetrics:
        """Coordinates LogMonitor, FileGenerator, and SessionManager asynchronously."""
        file_setting, expected_filenames, size_in_bytes, dynamic_timeout = self._parse_session_config(
            session_info, session_name, session_str
        )

        events_queue = Queue()

        log_monitor = LogMonitor(
            session_name=session_name,
            events_queue=events_queue,
            rx_dut=self.rx,
        )
        session_manager = SessionManager(
            session_name=session_name,
            expected_files=expected_filenames,
            file_size_bytes=size_in_bytes,
            events_queue=events_queue,
            timeout=dynamic_timeout,
        )

        metrics = self._execute_transfer(
            session_name=session_name,
            session_info=session_info,
            file_setting=file_setting,
            tx_dir=tx_dir,
            dynamic_timeout=dynamic_timeout,
            events_queue=events_queue,
            log_monitor=log_monitor,
            session_manager=session_manager
        )

        return self._post_validation(metrics, tx_dir, rx_dir, size_in_bytes, dynamic_timeout)

    def _parse_session_config(self, session_info: dict, session_name: str, session_str: str):
        file_setting = session_info.get("file_setting")
        if not file_setting:
            raise ValueError(f"No file setting found for session '{session_str}'")

        file_count = file_setting["file_count"]
        file_size = file_setting["file_size"]
        file_scale = file_setting["file_scale"].upper()

        size_in_bytes = file_size * _SCALE_TO_BYTES.get(file_scale, 1024)
        total_expected_bytes = file_count * size_in_bytes

        expected_filenames = [f"{session_name}_{i + 1}.bin" for i in range(file_count)]
        # Add per-file overhead (0.5s per file) to ensure tests with many small files don't time out
        dynamic_timeout = max(30.0, 10.0 + (total_expected_bytes / (1024 * 1024 * 2.0)) + (file_count * 0.5))

        return file_setting, expected_filenames, size_in_bytes, dynamic_timeout

    def _execute_transfer(
        self,
        session_name: str,
        session_info: dict,
        file_setting: dict,
        tx_dir: Path,
        dynamic_timeout: float,
        events_queue: Queue,
        log_monitor: LogMonitor,
        session_manager: SessionManager
    ) -> SessionMetrics:
        log_monitor.start()
        session_manager.start()

        try:
            if not log_monitor.stream_ready_event.wait(timeout=10.0):
                logger.warning("LogMonitor did not signal stream_ready_event in time.")
            
            # Give journalctl a moment to fully attach to the stream
            time.sleep(0.5)

            try:
                # Upload config first so the daemon starts watching the directory
                self._upload_session_config(session_info)
                
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

            logger.info(f"Main thread waiting for SessionManager to finish (Timeout: {dynamic_timeout:.1f}s)...")
            metrics = session_manager.wait_until_finished()
            logger.info(f"SessionManager finished. Result: {metrics}")
            return metrics
        finally:
            log_monitor.stop()

    def _post_validation(
        self,
        metrics: SessionMetrics,
        tx_dir: Path,
        rx_dir: Path,
        expected_size: int,
        dynamic_timeout: float
    ) -> SessionMetrics:
        if metrics.validation_status not in ("ERROR", "TIMEOUT"):
            logger.info(f"Waiting up to {dynamic_timeout:.1f}s for SMB share to synchronize {metrics.total_files} files...")
            start_time = time.perf_counter()
            
            while time.perf_counter() - start_time < dynamic_timeout:
                rx_files = list(rx_dir.glob("*.bin"))
                if len(rx_files) == metrics.total_files:
                    # Verify all files have exactly the expected size
                    if all(f.stat().st_size == expected_size for f in rx_files):
                        logger.info("SMB share synchronization complete.")
                        break
                time.sleep(1.0)
            else:
                logger.warning("SMB sync wait reached timeout; proceeding with validation anyway.")

            try:
                val_result = self.integrity_validator.validate_session_files(tx_dir, rx_dir)
                if not val_result.is_valid:
                    metrics.is_successful = False
                    metrics.validation_status = "FAILED"
                    metrics.error_message = val_result.details
                elif metrics.is_successful:
                    metrics.validation_status = "PASSED"
            except Exception as exc:
                logger.exception("File integrity validation failed due to exception")
                metrics.is_successful = False
                metrics.validation_status = "ERROR"
                metrics.error_message = f"Integrity validation error: {exc}"
        return metrics

    def _upload_session_config(self, session_info: dict) -> None:
        """Uploads session configuration JSON to Tx and Rx DUTs with role-specific SyncDirectory paths."""
        session_name = session_info["session_name"]
        config_dir = self.dut_paths.session_config_path
        remote_path = f"{config_dir}/{session_name}.json"

        dut_sync_dirs = {
            self.tx: f"{self.dut_paths.tx_mount_point}/{session_name}",
        }

        logger.info(f"Configuring DUTs for session '{session_name}'")
        for dut, sync_directory in dut_sync_dirs.items():
            session_config = {
                "Name": session_name,
                "ChunkSize": session_info.get("chunk_value"),
                "PacketLossTolerance": session_info.get("fec_value"),
                "SyncDirectory": sync_directory,
            }
            
            # Write config locally to a temporary file
            fd, local_temp_path = tempfile.mkstemp(suffix=".json")
            try:
                with os.fdopen(fd, 'w') as f:
                    json.dump(session_config, f, indent=4)
                
                # Upload via SFTP instead of fragile bash echo
                dut.ssh.run_checked(f"mkdir -p {config_dir}")
                dut.ssh.upload(local_temp_path, remote_path)
            finally:
                os.remove(local_temp_path)


# ----------------------------------------------------------------------
# Process Worker Context & Helper Functions
# ----------------------------------------------------------------------

class WorkerSessionContext:
    """Context manager for managing DUT connections and lifecycle inside a worker process."""

    def __init__(self, endpoint_settings: dict, host_settings: dict, session_str: str) -> None:
        self.endpoint_settings = endpoint_settings
        self.host_settings = host_settings
        self.session_str = session_str
        self.tx_dut: Optional[Dut] = None
        self.rx_dut: Optional[Dut] = None

    def __enter__(self) -> Tuple[Dut, Dut]:
        self.tx_dut = Dut.from_config("Tx", self.endpoint_settings["tx"], self.host_settings)
        self.rx_dut = Dut.from_config("Rx", self.endpoint_settings["rx"], self.host_settings)

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
    results_dir: Path,
    log_queue: Optional[Any] = None,
) -> SessionMetrics:
    """
    Top-level worker function for executing a benchmark session in a separate process.
    Instantiates process-isolated DUT instances using WorkerSessionContext.
    """
    setup_worker_logging(log_queue)
    with WorkerSessionContext(endpoint_settings, config_manager.host_settings, session_str) as (tx_dut, rx_dut):
        executor = SessionExecutor(
            tx_dut=tx_dut,
            rx_dut=rx_dut,
            config_manager=config_manager,
            results_dir=results_dir,
        )
        return executor.execute_session(
            test_name=test_name,
            session_str=session_str,
        )
