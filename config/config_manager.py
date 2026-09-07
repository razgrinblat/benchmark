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

    @property
    def session_definitions(self) -> dict:
        return self.config_data.get("session_definitions", {})

    def parse_session_string(self, session_str: str) -> dict:
        """
        Parses a session identifier string. Resolves from session_definitions if present,
        otherwise parses legacy format like 'NoFec-ManyMediumFiles-LargeChunkSize-sequential'.
        """
        session_defs = self.config_data.get("session_definitions", {})
        if session_str in session_defs:
            s_data = session_defs[session_str]
            file_setting = s_data.get("file_setting")
            if not file_setting:
                file_setting = {
                    "file_count": int(s_data.get("file_count", 1)),
                    "file_size": int(s_data.get("file_size", 1)),
                    "file_scale": str(s_data.get("file_scale", "KB")),
                }
            return {
                "session_name": session_str,
                "fec_key": s_data.get("fec_key", "custom"),
                "fec_value": int(s_data.get("fec_value", 0)),
                "files_key": s_data.get("files_key", "custom"),
                "file_setting": file_setting,
                "chunk_key": s_data.get("chunk_key", "custom"),
                "chunk_value": int(s_data.get("chunk_value", 65000)),
                "mode": s_data.get("mode", "sequential"),
            }

        parts = session_str.split('-')
        if len(parts) == 4:
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

        raise ValueError(f"Invalid session format or unknown session name: '{session_str}'")
