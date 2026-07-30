import logging
import multiprocessing
from logging.handlers import QueueHandler, QueueListener
from pathlib import Path
from datetime import datetime
from typing import Optional

_listener: Optional[QueueListener] = None


def setup_logging(log_directory: str = "logs") -> multiprocessing.Queue:
    """
    Configure the root logger in the main process and start a QueueListener
    to capture log messages from child worker processes.
    """
    global _listener

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

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(console_handler)
    root.addHandler(file_handler)

    log_queue = multiprocessing.Manager().Queue()
    _listener = QueueListener(log_queue, console_handler, file_handler, respect_handler_level=True)
    _listener.start()

    return log_queue


def setup_worker_logging(log_queue: Optional[multiprocessing.Queue]) -> None:
    """
    Configures the root logger in a child worker process to route all logs to the main process queue.
    """
    if log_queue is None:
        return

    queue_handler = QueueHandler(log_queue)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(queue_handler)


def stop_logging() -> None:
    """Stops the queue listener when benchmark finishes."""
    global _listener
    if _listener:
        _listener.stop()
        _listener = None

