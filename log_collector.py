import logging
from pathlib import Path
from dut import Dut

logger = logging.getLogger(__name__)


class LogCollector:
    """
    Collects logs from Tx and Rx DUTs and stores them in the session output directory.
    """

    def __init__(self, tx_dut: Dut, rx_dut: Dut) -> None:
        self.tx = tx_dut
        self.rx = rx_dut

    def collect_logs(self, target_dir: Path, session_name: str) -> dict[str, Path]:
        """
        Gathers system and service logs from DUTs and writes them to target_dir.
        """
        target_dir.mkdir(parents=True, exist_ok=True)
        collected_files = {}

        for dut in (self.tx, self.rx):
            try:
                log_file = target_dir / f"{dut.name}_{session_name}.log"
                # Collect journal logs for smartchannel or system services
                res = dut.ssh.run_checked("journalctl -u smartchannel --no-pager -n 200 || dmesg | tail -n 100")
                with open(log_file, "w", encoding="utf-8") as f:
                    f.write(f"=== Logs for {dut.name} (Session: {session_name}) ===\n")
                    f.write(res.stdout)
                collected_files[dut.name] = log_file
                logger.info(f"Collected logs for {dut.name} -> {log_file.name}")
            except Exception as e:
                logger.error(f"Failed to collect logs from {dut.name}: {e}")

        return collected_files
