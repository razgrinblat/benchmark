import logging


class GUILogHandler(logging.Handler):
    """Custom logging handler to route log records safely to the GUI queue."""

    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_queue.put((record.levelno, msg))
        except Exception:
            pass
