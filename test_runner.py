import concurrent.futures
import logging
import shutil
from pathlib import Path
from typing import Optional, Any
from dut import Dut
from config_manager import ConfigurationManager
from dut_settings import DutPaths
from metrics_manager import SessionMetrics
from result_manager import ResultManager
from session_executor import run_session_worker

logger = logging.getLogger(__name__)


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
        results_dir: Path,
        log_queue: Optional[Any] = None,
    ) -> None:
        self.tx = tx_dut
        self.rx = rx_dut
        self.config_manager = config_manager
        self.results_dir = results_dir
        self.log_queue = log_queue
        self.dut_paths = DutPaths.load()

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

        test_results_dir = self.results_dir / "Results" / test_name
        result_manager = ResultManager(test_name, test_results_dir)

        session_metrics = []
        try:
            if session_list:
                session_metrics = self._execute_sessions_in_parallel(test_name, session_list)

            result_manager.save_test_results(session_metrics)
            logger.info(f"=== Finished Test: '{test_name}' ===")
        finally:
            self._test_cleanup(session_list)

    def _test_cleanup(self, session_list: list[str]) -> None:
        """delete all test files from Tx and Rx paths and delete all session 
        Configurations from the config directory"""
        logger.info("Running test cleanup: deleting local directories and remote config files...")
        config_dir = self.dut_paths.session_config_path
        
        for session_str in session_list:
            session_info = self.config_manager.parse_session_string(session_str)
            session_name = session_info["session_name"]
            
            # Clean local Tx and Rx directories
            tx_session_dir = self.tx.local_dir / session_name
            rx_session_dir = self.rx.local_dir / session_name
            
            if tx_session_dir.exists():
                shutil.rmtree(tx_session_dir, ignore_errors=True)
            if rx_session_dir.exists():
                shutil.rmtree(rx_session_dir, ignore_errors=True)
                
            # Clean remote config file
            remote_path = f"{config_dir}/{session_name}.json"
            for dut in [self.tx, self.rx]:
                if dut == self.rx and self.rx.ssh._host == self.tx.ssh._host:
                    continue  # We only uploaded to Tx in this case
                try:
                    dut.ssh.run_checked(f"rm -f {remote_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete remote config {remote_path} on {dut.ssh._host}: {e}")

    def _execute_sessions_in_parallel(
        self,
        test_name: str,
        session_list: list[str],
    ) -> list[SessionMetrics]:
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
                    config_manager=self.config_manager,
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

        # Preserve configured session order when returning results
        ordered_metrics = []
        for session_str in session_list:
            if session_str in results_by_session:
                ordered_metrics.append(results_by_session[session_str])
        
        return ordered_metrics

