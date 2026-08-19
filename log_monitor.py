import threading
import logging
from datetime import datetime
from queue import Queue

from dut import Dut
from ssh_client import SSHClient
from log_parser import LogParser
from events import LogMonitorErrorEvent

logger = logging.getLogger(__name__)

SERVICE_NAME = "smartchannel"

class LogMonitor:
    """
    Monitors SmartChannel logs from the Rx DUT asynchronously in a background thread.

    Responsibilities:
        - Establishes a dedicated, isolated SSH client connection to the RX DUT.
        - Streams systemd journalctl output in a non-blocking loop.
        - Filters and parses log messages into typed events.
        - Gracefully cleans up SSH connections and threads upon termination.
    """

    def __init__(self, session_name: str, events_queue: Queue, rx_dut: Dut):
        self.session_name = session_name
        self.events_queue: Queue = events_queue
        self.rx = rx_dut
        self.parser = LogParser(session_name=session_name)

        # Dedicated, isolated SSH connection for streaming logs
        self.ssh_client = SSHClient(
            host=rx_dut.ssh._host,
            username=rx_dut.ssh._username,
            password=rx_dut.ssh._password,
        )

        self.thread = None
        self.stop_event = threading.Event()

    def start(self) -> None:
        """
        Starts the log monitoring background thread.
        """
        logger.info(f"Starting log monitor for session: {self.session_name}")
        self.stop_event.clear()
        self.thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self.thread.start()

    def _monitor_loop(self) -> None:
        """
        Connects via SSH and processes remote journalctl log stream.
        """
        try:
            logger.info("LogMonitor background thread establishing SSH connection...")
            self.ssh_client.connect()
        except Exception as exc:
            logger.exception("LogMonitor failed to connect via SSH")
            self.events_queue.put(LogMonitorErrorEvent(reason=f"SSH connection failed: {exc}", timestamp=datetime.now()))
            return

        command = self._build_journalctl_command()
        try:
            logger.info(f"LogMonitor streaming command: {command}")
            for line in self.ssh_client.stream_lines(command):
                logger.info(f"LogMonitor received line: {line}")
                if self.stop_event.is_set():
                    break

                if self.session_name not in line:
                    continue

                event = self.parser.parse(line)
                if event:
                    logger.debug(f"LogMonitor publishing event: {event}")
                    self.events_queue.put(event)

        except Exception as exc:
            if not self.stop_event.is_set():
                logger.exception("LogMonitor encountered an error while streaming logs")
                self.events_queue.put(LogMonitorErrorEvent(reason=f"Log stream failed: {exc}", timestamp=datetime.now()))
        finally:
            logger.info("LogMonitor disconnecting SSH connection...")
            try:
                self.ssh_client.disconnect()
            except Exception as exc:
                logger.warning(f"Error disconnecting log monitor SSH client: {exc}")

    def stop(self) -> None:
        """
        Stops the log monitor stream and waits for the thread to exit.
        """
        logger.info("Stopping log monitor")
        self.stop_event.set()
        self.ssh_client.disconnect()

        if self.thread:
            self.thread.join(timeout=5)
            self.thread = None

    def _build_journalctl_command(self) -> str:
        """
        Builds the journalctl streaming command using sudo with stdbuf line buffering.
        Session filtering is handled in Python to avoid journalctl --grep streaming issues on older systemd versions.
        """
        return (
            f"sudo stdbuf -oL journalctl -u {SERVICE_NAME} "
            f"-f "
            f"--no-pager "
            f"-o short-iso"
        )