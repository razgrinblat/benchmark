import configparser
import logging
from dataclasses import dataclass, fields
from pathlib import Path
from typing import ClassVar

logger = logging.getLogger(__name__)

_DEFAULT_INI_PATH = Path(__file__).parent / "dut_settings.ini"


@dataclass(frozen=True)
class _IniSettings:
    """Base class for settings loaded from a section of dut_settings.ini."""

    _section: ClassVar[str]

    @classmethod
    def load(cls, ini_path: Path = _DEFAULT_INI_PATH) -> "_IniSettings":
        """Loads settings from the given INI file path."""
        if not ini_path.exists():
            raise FileNotFoundError(f"DUT settings file not found at: {ini_path}")

        parser = configparser.ConfigParser()
        parser.read(ini_path, encoding="utf-8-sig")

        if cls._section not in parser:
            raise ValueError(f"Missing [{cls._section}] section in {ini_path}")

        kwargs = {
            f.name: parser.get(cls._section, f.name)
            for f in fields(cls)
        }
        settings = cls(**kwargs)
        logger.info(f"Loaded {cls.__name__} from {ini_path}")
        return settings


@dataclass(frozen=True)
class LogFormats(_IniSettings):
    """Holds log formats loaded from dut_settings.ini."""

    _section: ClassVar[str] = "log_formats"

    success_log_format: str
    failure_log_format: str


@dataclass(frozen=True)
class DutPaths(_IniSettings):
    """
    Holds DUT-specific path constants and service name loaded from dut_settings.ini.
    All fields are strings representing remote paths on the DUT.
    """

    _section: ClassVar[str] = "paths"

    service_name: str
    tx_mount_point: str
    rx_mount_point: str
    session_config_path: str