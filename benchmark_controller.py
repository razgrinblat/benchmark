import logging
from pathlib import Path
import datetime
from logger import setup_logging
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
        self.benchmark_dir: Path = None

    def _create_benchmark_directory(self,base_dir: str = ".") -> Path:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        benchmark_dir = Path(base_dir) / "Tests" / timestamp

        (benchmark_dir / "Results").mkdir(parents=True, exist_ok=True)
        (benchmark_dir / "Tx").mkdir(exist_ok=True)
        (benchmark_dir / "Rx").mkdir(exist_ok=True)

        return benchmark_dir

    def start_benchmark(self) -> None:
        """
        Executes the benchmark lifecycle:
          1. Start Benchmark
          2. Load Config
          3. Initialize Logging, Paths, & DUT Connections
          4. Execute Tests via TestRunner
          5. Finish Benchmark
        """
        logger.info("==========================================")
        logger.info("             START BENCHMARK              ")
        logger.info("==========================================")

        try:
            # Load Config via Configuration Manager
            self.config_manager = ConfigurationManager(self.config_path)

            host_settings = self.config_manager.host_settings
            shared_local_path = host_settings.get("shared_directory_local_path", ".")

            # Prepare Benchmark Directory and Logging
            self.benchmark_dir = self._create_benchmark_directory(shared_local_path)
            setup_logging(log_directory=str(self.benchmark_dir / "Results"))

            logger.info(f"Initialized benchmark directory: {self.benchmark_dir}")

            # Initialize DUTs
            endpoints = self.config_manager.endpoint_settings
            self.tx = Dut.from_config("Tx", endpoints["tx"])
            self.rx = Dut.from_config("Rx", endpoints["rx"])

            # Setup context and initial steps
            context = SetupContext(
                tx=self.tx,
                rx=self.rx,
                benchmark_directory=str(self.benchmark_dir),
                host_settings=host_settings,
            )

            setup_steps = [
                ConnectStep(),
                UploadBinaries(),
                MountDirectories(),
            ]

            for step in setup_steps:
                logger.info(f"Running setup step: {step.__class__.__name__}")
                step.run(context)

            # Delegate test execution to TestRunner
            runner = TestRunner(
                tx_dut=self.tx,
                rx_dut=self.rx,
                config_manager=self.config_manager,
                benchmark_dir=self.benchmark_dir,
            )
            runner.run_all_tests()

        except Exception as exc:
            logger.exception("Benchmark run encountered a critical error")
            raise exc
        finally:
            self.finish_benchmark()

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
