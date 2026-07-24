import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigurationManager:
    """
    Manages loading, parsing, and accessing benchmark configuration parameters.
    """

    def __init__(self, config_path: str = "config.json") -> None:
        self.config_path = Path(config_path)
        self.config_data = self._load_config()

    def _load_config(self) -> dict:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"Loaded configuration from {self.config_path}")
        return data

    @property
    def endpoint_settings(self) -> dict:
        return self.config_data.get("endpoint_setting", {})

    @property
    def host_settings(self) -> dict:
        return self.config_data.get("host_settings", {})

    @property
    def file_settings(self) -> dict:
        return self.config_data.get("file_settings", {})

    @property
    def fec_settings(self) -> dict:
        return self.config_data.get("fec_settings", {})

    @property
    def chunk_size_settings(self) -> dict:
        return self.config_data.get("chunkSize_setting", {})

    @property
    def tests(self) -> list:
        return self.config_data.get("tests", [])

    def parse_session_string(self, session_str: str) -> dict:
        """
        Parses a session identifier string like 'NoFec-ManyMediumFiles-LargeChunkSize-sequential'
        and resolves settings from the configuration.
        """
        parts = session_str.split('-')
        if len(parts) != 4:
            raise ValueError(f"Invalid session string format: '{session_str}'")

        fec_key, files_key, chunk_key, mode = parts

        file_setting = self.file_settings.get(files_key)
        fec_value = self.fec_settings.get(fec_key)
        chunk_value = self.chunk_size_settings.get(chunk_key)

        return {
            "session_name": session_str,
            "fec_key": fec_key,
            "fec_value": fec_value,
            "files_key": files_key,
            "file_setting": file_setting,
            "chunk_key": chunk_key,
            "chunk_value": chunk_value,
            "mode": mode,
        }
