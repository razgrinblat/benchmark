import logging
from pathlib import Path

from dut import Dut
from config_manager import ConfigurationManager
from metrics_manager import MetricsManager
from result_manager import ResultManager
from session_executor import SessionExecutor

logger = logging.getLogger(__name__)


class TestRunner:
    """
    Orchestrates execution of tests defined in configuration.
    For each test, creates MetricsManager and ResultManager, executes sessions via SessionExecutor,
    and persists test results.
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

    def run_all_tests(self) -> list[Path]:
        """
        Iterates over all test definitions from configuration and runs their sessions.
        Returns list of saved result artifact paths.
        """
        tests = self.config_manager.tests
        result_files = []

        logger.info(f"TestRunner starting {len(tests)} test suite(s)...")

        for test_def in tests:
            test_name = test_def.get("name", "UnnamedTest")
            session_list = test_def.get("sessions", [])

            logger.info(f"=== Starting Test: '{test_name}' ({len(session_list)} sessions) ===")

            # Create Metrics Manager & Result Manager for this Test
            metrics_manager = MetricsManager(test_name)
            test_results_dir = self.benchmark_dir / "Results" / test_name
            result_manager = ResultManager(test_name, test_results_dir)

            # Create Session Executor
            session_executor = SessionExecutor(
                tx_dut=self.tx,
                rx_dut=self.rx,
                config_manager=self.config_manager,
                benchmark_dir=self.benchmark_dir,
            )

            # For each Session in Test:
            for session_str in session_list:
                logger.info(f"Running Session: {session_str} in {test_name}")
                session_executor.execute_session(
                    test_name=test_name,
                    session_str=session_str,
                    metrics_manager=metrics_manager,
                )

            # Save Test Results
            output_file = result_manager.save_test_results(metrics_manager.get_all_metrics())
            result_files.append(output_file)
            logger.info(f"=== Finished Test: '{test_name}' ===")

        return result_files
