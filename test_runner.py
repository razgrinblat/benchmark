import concurrent.futures
import logging
import json
from pathlib import Path
from typing import Optional, Any
from dut import Dut
from config_manager import ConfigurationManager
from metrics_manager import MetricsManager
from result_manager import ResultManager
from session_executor import run_session_worker

logger = logging.getLogger(__name__)

REMOTE_SESSION_CONFIG_DIR = "/var/smartchannel/SessionConfig"

class TestRunner:
    """
    Orchestrates execution of tests defined in configuration.
    For each test, creates MetricsManager and ResultManager, executes sessions in parallel via ProcessPoolExecutor,
    and persists test results.
    """

    def __init__(
        self,
        tx_dut: Dut,
        rx_dut: Dut,
        config_manager: ConfigurationManager,
        tx_dir: Path,
        rx_dir: Path,
        results_dir: Path,
        log_queue: Optional[Any] = None,
    ) -> None:
        self.tx = tx_dut
        self.rx = rx_dut
        self.config_manager = config_manager
        self.tx_dir = tx_dir
        self.rx_dir = rx_dir
        self.results_dir = results_dir
        self.log_queue = log_queue

    def run_all_tests(self) -> None:
        """
        Iterates over all test definitions from configuration and runs their sessions.
        """
        tests = self.config_manager.tests
        logger.info(f"TestRunner starting {len(tests)} test suite(s)...")

        for test_def in tests:
            self._run_single_test_suite(test_def)


    def _run_single_test_suite(self, test_def: dict) -> None:
        """Runs all sessions for a single test definition and persists results."""
        test_name = test_def.get("name", "UnnamedTest")
        session_list = test_def.get("sessions", [])

        logger.info(f"=== Starting Test: '{test_name}' ({len(session_list)} parallel sessions) ===")

        metrics_manager = MetricsManager(test_name)
        test_results_dir = self.results_dir / "Results" / test_name
        result_manager = ResultManager(test_name, test_results_dir)

        if session_list:
            self._configure_test_sessions(session_list)
            self._execute_sessions_in_parallel(test_name, session_list, metrics_manager)

        result_manager.save_test_results(metrics_manager.get_all_metrics())
        logger.info(f"=== Finished Test: '{test_name}' ===")

    def _test_cleanup():
        """delete all test files from Tx and Rx paths and delete all seesion 
        Configurations from the config directory"""
        pass

    def _execute_sessions_in_parallel(
        self,
        test_name: str,
        session_list: list[str],
        metrics_manager: MetricsManager,
    ) -> None:
        """Launches process pool executor for parallel session execution."""
        max_workers = len(session_list)
        logger.info(f"Launching {max_workers} session processes in parallel for test '{test_name}'...")

        results_by_session = {}
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_session: dict = {
                executor.submit(
                    run_session_worker,
                    test_name=test_name,
                    session_str=session_str,
                    endpoint_settings=self.config_manager.endpoint_settings,
                    config_manager=self.config_manager,
                    tx_dir=self.tx_dir,
                    rx_dir=self.rx_dir,
                    results_dir=self.results_dir,
                    log_queue=self.log_queue,
                ): session_str
                for session_str in session_list
            }

            for future in concurrent.futures.as_completed(future_to_session):
                session_str = future_to_session[future]
                try:
                    session_metrics = future.result()
                    results_by_session[session_str] = session_metrics
                    logger.info(f"Session process '{session_str}' completed successfully.")
                except Exception as exc:
                    logger.exception(f"Session process for '{session_str}' failed with exception: {exc}")

        # Preserve configured session order when adding to metrics manager
        for session_str in session_list:
            if session_str in results_by_session:
                metrics_manager.add_session_metrics(results_by_session[session_str])


    def _upload_session_config(self, session_info: dict) -> None:
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

    
    def _configure_test_sessions(self, session_list: list[str]) -> None:
        """Upload session configurations for all sessions in the test."""
        for session_str in session_list:
            session_info = self.config_manager.get_session_info(session_str)
            self._upload_session_config(session_info)