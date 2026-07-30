import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class SessionFileManager:
    """
    Manages local and remote directory paths for a benchmark session.
    """

    def __init__(
        self,
        tx_dir: Path,
        rx_dir: Path,
        results_dir: Path,
        test_name: str,
        session_name: str,
    ) -> None:
        self.tx_dir = Path(tx_dir)
        self.rx_dir = Path(rx_dir)
        self.results_dir = Path(results_dir)
        self.test_name = test_name
        self.session_name = session_name

        self.tx_session_dir = self.tx_dir / session_name
        self.rx_session_dir = self.rx_dir / session_name
        self.results_session_dir = self.results_dir / "Results" / test_name / session_name

    def prepare_directories(self) -> None:
        """Creates required local session directories."""
        self.tx_session_dir.mkdir(parents=True, exist_ok=True)
        self.rx_session_dir.mkdir(parents=True, exist_ok=True)
        self.results_session_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Prepared directories for session {self.session_name}")

    def get_tx_dir(self) -> Path:
        return self.tx_session_dir

    def get_rx_dir(self) -> Path:
        return self.rx_session_dir

    def get_results_dir(self) -> Path:
        return self.results_session_dir
