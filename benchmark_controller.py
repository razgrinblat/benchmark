import logging
from pathlib import Path
from datetime import datetime
from logger import setup_logging, stop_logging
from dut import Dut
from config_manager import ConfigurationManager
from test_runner import TestRunner
from steps import SetupContext, ConnectStep, UploadBinaries, MountDirectories

logger = logging.getLogger(__name__)


class BenchmarkController:
    """
    Top-level orchestrator managing the full benchmark execution lifecycle.
    """

    def __init__(self, config_path: str = "config.json") -> None:
        self.config_path = config_path
        self.config_manager: ConfigurationManager = None
        self.tx: Dut = None
        self.rx: Dut = None
        self.results_dir: Path = None
        self.tx_dir: Path = None
        self.rx_dir: Path = None
        self.log_queue = None

    def _create_benchmark_directory(self, base_dir: str, timestamp: str) -> Path:
        """Creates and returns the timestamped results directory."""
        benchmark_dir = Path(base_dir) / "Tests" / timestamp
        (benchmark_dir / "Results").mkdir(parents=True, exist_ok=True)
        return benchmark_dir

    def start_benchmark(self) -> None:
        """Executes the full benchmark lifecycle."""
        logger.info("==========================================")
        logger.info("             START BENCHMARK              ")
        logger.info("==========================================")

        try:
            self._setup_environment()
            self._init_duts()
            self._run_setup_steps()
            self._run_tests()
        except Exception as exc:
            logger.exception("Benchmark run encountered a critical error")
            raise exc
        finally:
            self.finish_benchmark()

    def _setup_environment(self) -> None:
        """Loads configuration, creates benchmark directories, and configures logging."""
        self.config_manager = ConfigurationManager(self.config_path)

        host_settings = self.config_manager.host_settings
        results_path = host_settings.get("results_path", ".")
        tx_path = host_settings.get("tx", {}).get("path")
        rx_path = host_settings.get("rx", {}).get("path")

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.results_dir = self._create_benchmark_directory(results_path, timestamp)
        self.tx_dir = Path(tx_path) / "Tx"
        self.rx_dir = Path(rx_path) / "Rx"

        self.tx_dir.mkdir(parents=True, exist_ok=True)
        self.rx_dir.mkdir(parents=True, exist_ok=True)

        self.log_queue = setup_logging(log_directory=str(self.results_dir / "Results"))
        logger.info(f"Initialized benchmark directories: Results={self.results_dir}, Tx={self.tx_dir}, Rx={self.rx_dir}")

    def _init_duts(self) -> None:
        """Initializes Tx and Rx DUT instances from configuration."""
        endpoints = self.config_manager.endpoint_settings
        self.tx = Dut.from_config("Tx", endpoints["tx"])
        self.rx = Dut.from_config("Rx", endpoints["rx"])

    def _run_setup_steps(self) -> None:
        """Executes connection, binary upload, and directory mounting setup steps."""
        context = SetupContext(
            tx=self.tx,
            rx=self.rx,
            host_settings=self.config_manager.host_settings,
        )

        setup_steps = [
            ConnectStep(),
            # UploadBinaries(),
            # MountDirectories(),
        ]

        for step in setup_steps:
            logger.info(f"Running setup step: {step.__class__.__name__}")
            step.run(context)

    def _run_tests(self) -> None:
        """Instantiates TestRunner and executes all configured tests."""
        runner = TestRunner(
            tx_dut=self.tx,
            rx_dut=self.rx,
            config_manager=self.config_manager,
            tx_dir=self.tx_dir,
            rx_dir=self.rx_dir,
            results_dir=self.results_dir,
            log_queue=self.log_queue,
        )
        runner.run_all_tests()

    def finish_benchmark(self) -> None:
        """Cleans up resources and disconnects DUT SSH connections."""
        logger.info("==========================================")
        logger.info("            FINISH BENCHMARK              ")
        logger.info("==========================================")

        if self.rx:
            try:
                self.rx.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting Rx: {e}")

        if self.tx:
            try:
                self.tx.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting Tx: {e}")

        logger.info("Benchmark finished successfully.")
        stop_logging()
