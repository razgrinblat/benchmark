import logging
from pathlib import Path
from datetime import datetime


def setup_logging(log_directory: str = "logs") -> None:
    """
    Configure the root logger once at program startup.

    All module-level loggers created with logging.getLogger(__name__)
    will automatically propagate their records here.
    """
    Path(log_directory).mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = Path(log_directory) / f"benchmark_{timestamp}.log"

    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root = logging.getLogger()   # root logger — all child loggers propagate here
    root.setLevel(logging.INFO)
    root.addHandler(console_handler)
    root.addHandler(file_handler)
