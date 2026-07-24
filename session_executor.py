import json
import logging
from pathlib import Path
from typing import Optional

from dut import Dut
from config_manager import ConfigurationManager
from file_generator import FileGenerator
from session_file_manager import SessionFileManager
from log_collector import LogCollector
from integrity_validator import IntegrityValidator
from metrics_manager import MetricsManager, SessionMetrics

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
        benchmark_dir: Path,
    ) -> None:
        self.tx = tx_dut
        self.rx = rx_dut
        self.config_manager = config_manager
        self.benchmark_dir = Path(benchmark_dir)

        self.file_generator = FileGenerator()
        self.log_collector = LogCollector(self.tx, self.rx)
        self.integrity_validator = IntegrityValidator()

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
            dut.ssh.run_checked(f"mkdir -p {REMOTE_SESSION_CONFIG_DIR}", role=dut.name)
            dut.ssh.run_checked(f"echo '{escaped}' > {remote_path}", role=dut.name)

    def execute_session(
        self,
        test_name: str,
        session_str: str,
        metrics_manager: MetricsManager,
    ) -> None:
        """Runs full session lifecycle."""
        session_info = self.config_manager.parse_session_string(session_str)
        session_name = session_info["session_name"]

        metrics = metrics_manager.start_session(session_name)
        session_file_mgr = SessionFileManager(self.benchmark_dir, test_name, session_name)
        session_file_mgr.prepare_directories()

        tx_dir = session_file_mgr.get_tx_dir()
        rx_dir = session_file_mgr.get_rx_dir()
        results_dir = session_file_mgr.get_results_dir()

        total_files = 0
        total_bytes = 0
        error_msg: Optional[str] = None
        validation_status = "FAILED"
        is_success = False

        try:
            # Step 1: Configure DUT
            self._configure_dut(session_info)

            # Step 2: Generate files
            file_setting = session_info.get("file_setting")
            if not file_setting:
                raise ValueError(f"No file setting found for session '{session_str}'")

            generated_files = self.file_generator.generate_files(
                target_dir=tx_dir,
                file_setting=file_setting,
                mode=session_info.get("mode", "sequential"),
            )
            total_files = len(generated_files)
            total_bytes = sum(f.stat().st_size for f in generated_files if f.exists())

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

        finally:
            # Step 5: Report metrics
            metrics_manager.finish_session(
                metrics=metrics,
                total_files=total_files,
                total_bytes=total_bytes,
                is_successful=is_success,
                validation_status=validation_status,
                error_message=error_msg,
            )
