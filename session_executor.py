import json
import logging
from pathlib import Path
from typing import Optional, Tuple, Any

from dut import Dut
from config_manager import ConfigurationManager
from file_generator import FileGenerator
from session_file_manager import SessionFileManager
from log_collector import LogCollector
from integrity_validator import IntegrityValidator
from metrics_manager import MetricsManager, SessionMetrics
from logger import setup_worker_logging

logger = logging.getLogger(__name__)

REMOTE_SESSION_CONFIG_DIR = "/var/smartchannel/SessionConfig"


class SessionExecutor:
    """
    Executes a single benchmark session following the lifecycle:
      1. Configure DUT
      2. Generate files
      3. Collect logs
      4. Validate files
      5. Report metrics
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
        self.log_collector = LogCollector(self.tx, self.rx)
        self.integrity_validator = IntegrityValidator()

    def execute_session(
        self,
        test_name: str,
        session_str: str,
        metrics_manager: MetricsManager,
    ) -> SessionMetrics:
        """Runs full session lifecycle."""
        session_info = self.config_manager.parse_session_string(session_str)
        session_name = session_info["session_name"]

        metrics = metrics_manager.start_session(session_name)
        session_file_mgr = self._prepare_session_files(test_name, session_name)

        tx_dir = session_file_mgr.get_tx_dir()
        rx_dir = session_file_mgr.get_rx_dir()
        results_dir = session_file_mgr.get_results_dir()

        total_files, total_bytes, is_success, validation_status, error_msg = (
            self._run_session_steps(session_info, session_str, session_name, tx_dir, rx_dir, results_dir)
        )

        metrics_manager.finish_session(
            metrics=metrics,
            total_files=total_files,
            total_bytes=total_bytes,
            is_successful=is_success,
            validation_status=validation_status,
            error_message=error_msg,
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

    def _run_session_steps(
        self,
        session_info: dict,
        session_str: str,
        session_name: str,
        tx_dir: Path,
        rx_dir: Path,
        results_dir: Path,
    ) -> Tuple[int, int, bool, str, Optional[str]]:
        """Executes session lifecycle steps (configure, generate files, collect logs, validate)."""
        total_files = 0
        total_bytes = 0
        error_msg: Optional[str] = None
        validation_status = "FAILED"
        is_success = False

        try:
            # Step 1: Configure DUT
            self._configure_dut(session_info)

            # Step 2: Generate files
            total_files, total_bytes = self._generate_payload_files(tx_dir, session_info, session_str)

            # Step 3: Collect logs
            self.log_collector.collect_logs(results_dir, session_name)

            # Step 4: Validate files
            val_result = self.integrity_validator.validate_session_files(tx_dir, rx_dir)
            is_success = val_result.is_valid
            validation_status = "PASSED" if val_result.is_valid else "FAILED"
            if not is_success:
                error_msg = val_result.details

        except Exception as exc:
            logger.exception(f"Error executing session '{session_name}'")
            error_msg = str(exc)
            validation_status = "ERROR"
            is_success = False

        return total_files, total_bytes, is_success, validation_status, error_msg

    def _configure_dut(self, session_info: dict) -> None:
        """Uploads session configuration JSON to both Tx and Rx DUTs."""
        session_name = session_info["session_name"]
        session_config = {
            "Name": session_name,
            "ChunkSize": session_info.get("chunk_value"),
            "PacketLossTolerance": session_info.get("fec_value"),
            "SyncDirectory": f"/SMART_CHANNEL/TX_SYNC/{session_name}",
        }
        config_json = json.dumps(session_config, indent=4)
        remote_path = f"{REMOTE_SESSION_CONFIG_DIR}/{session_name}.json"
        escaped = config_json.replace("'", "'\\''")

        logger.info(f"Configuring DUTs for session '{session_name}'")
        for dut in (self.tx, self.rx):
            dut.ssh.run_checked(f"mkdir -p {REMOTE_SESSION_CONFIG_DIR}")
            dut.ssh.run_checked(f"echo '{escaped}' > {remote_path}")

    def _generate_payload_files(
        self,
        tx_dir: Path,
        session_info: dict,
        session_str: str,
    ) -> Tuple[int, int]:
        """Generates test files in target Tx directory and returns total count and total bytes."""
        file_setting = session_info.get("file_setting")
        if not file_setting:
            raise ValueError(f"No file setting found for session '{session_str}'")

        generated_files = self.file_generator.generate_files(
            target_dir=tx_dir,
            file_setting=file_setting,
            mode=session_info.get("mode"),
        )
        total_files = len(generated_files)
        total_bytes = sum(f.stat().st_size for f in generated_files if f.exists())
        return total_files, total_bytes


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


