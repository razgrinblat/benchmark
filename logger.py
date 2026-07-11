import logging
from pathlib import Path
from datetime import datetime


class BenchmarkLogger:
    _logger = None

    @classmethod
    def initialize(cls, log_directory: str = "logs") -> None:
        """
        Initialize the global logger.
        Should be called once at program startup.
        """

        if cls._logger is not None:
            return

        Path(log_directory).mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        log_file = Path(log_directory) / f"benchmark_{timestamp}.log"

        logger = logging.getLogger("Benchmark")
        logger.setLevel(logging.INFO)
        logger.propagate = False

        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(message)s"
        )

        # Console output
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        # Log file
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        cls._logger = logger

    @classmethod
    def get_logger(cls) -> logging.Logger:

        if cls._logger is None:
            raise RuntimeError(
                "Logger has not been initialized."
            )

        return cls._logger