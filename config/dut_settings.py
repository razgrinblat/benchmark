import configparser
import logging
from dataclasses import dataclass, fields
from pathlib import Path
from typing import ClassVar

logger = logging.getLogger(__name__)

# Default resolves to project root if placed in config/ subfolder
_DEFAULT_INI_PATH = Path(__file__).resolve().parent.parent / "dut_settings.ini"


@dataclass(frozen=True)
class _IniSettings:
    """Base class for settings loaded from a section of dut_settings.ini."""

    _section: ClassVar[str]

    @classmethod
    def load(cls, ini_path: Path = None) -> "_IniSettings":
        """Loads settings from the given INI file path."""
        target_path = ini_path if ini_path is not None else _DEFAULT_INI_PATH
        if not target_path.exists():
            # Fallback to local cwd
            target_path = Path("dut_settings.ini")
            if not target_path.exists():
                raise FileNotFoundError(f"DUT settings file not found at: {target_path}")

        parser = configparser.ConfigParser()
        parser.read(target_path, encoding="utf-8-sig")

        if cls._section not in parser:
            raise ValueError(f"Missing [{cls._section}] section in {target_path}")

        kwargs = {}
        for f in fields(cls):
            raw_val = parser.get(cls._section, f.name)
            if f.type is float or f.type == float:
                kwargs[f.name] = float(raw_val)
            elif f.type is int or f.type == int:
                kwargs[f.name] = int(raw_val)
            elif f.type is bool or f.type == bool:
                kwargs[f.name] = parser.getboolean(cls._section, f.name)
            else:
                kwargs[f.name] = raw_val
        settings = cls(**kwargs)
        logger.info(f"Loaded {cls.__name__} from {target_path}")
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
