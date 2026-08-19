import re
import logging
from datetime import datetime
from typing import Optional, Any

from events import (
    TransferSuccessEvent,
    TransferFailedEvent,
)

logger = logging.getLogger(__name__)

# Matches ISO timestamps at the beginning of the log line
ISO_TS_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:?\d{2}|Z)?)")

# regexes to extract file names and transfer metrics
SUCCESS_PATTERNS = [
    re.compile(r"transfer\s+success(?:ful)?:\s*([\w\-\.]+)", re.IGNORECASE),
    re.compile(r"successfully\s+transferred\s+([\w\-\.]+)", re.IGNORECASE),
    re.compile(r"file\s+([\w\-\.]+)\s+transferred\s+successfully", re.IGNORECASE),
    re.compile(r"([\w\-\.]+)\s+transferred\s+successfully", re.IGNORECASE),
]

FAILURE_PATTERNS = [
    re.compile(r"transfer\s+failed?:\s*([\w\-\.]+)(?:\s*-\s*(.*))?", re.IGNORECASE),
    re.compile(r"failed\s+to\s+transfer\s+([\w\-\.]+)(?:\s*:\s*(.*))?", re.IGNORECASE),
    re.compile(r"file\s+([\w\-\.]+)\s+transfer\s+failed?(?:\s*:\s*(.*))?", re.IGNORECASE),
    re.compile(r"([\w\-\.]+)\s+transfer\s+failed?(?:\s*:\s*(.*))?", re.IGNORECASE),
]

TIME_PATTERN = re.compile(r"in\s+(\d+)\s*ms", re.IGNORECASE)


class LogParser:
    """
    Parses remote system/service log lines into strongly typed benchmark events,
    matching the existing definitions in events.py.
    """

    def __init__(self, session_name: str) -> None:
        self.session_name = session_name

    def parse(self, line: str) -> Optional[Any]:
        """
        Parses a log line and returns a benchmark event if matched, or None.
        """
        line = line.strip()
        if not line:
            return None

        timestamp = self._parse_timestamp(line)
        msg = self._clean_log_message(line)

        # Try to parse as success event
        success_event = self._match_success(msg, timestamp)
        if success_event:
            return success_event

        # Try to parse as failure event
        failure_event = self._match_failure(msg, timestamp)
        if failure_event:
            return failure_event

        return None

    def _parse_timestamp(self, line: str) -> datetime:
        """
        Extracts and parses the ISO timestamp from the beginning of the log line.
        Defaults to datetime.now() if no timestamp is found or if parsing fails.
        """
        ts_match = ISO_TS_PATTERN.match(line)
        if not ts_match:
            return datetime.now()

        ts_str = ts_match.group(1)
        try:
            # Normalize timezones without colons (e.g., +0300 to +03:00)
            if len(ts_str) >= 5 and (ts_str[-5] in ('+', '-')) and (':' not in ts_str[-3:]):
                ts_str = ts_str[:-2] + ":" + ts_str[-2:]
            return datetime.fromisoformat(ts_str)
        except Exception:
            return datetime.now()

    def _clean_log_message(self, line: str) -> str:
        """
        Strips journalctl prefix if the line is journalctl output.
        Removes the 'smartchannel[pid]:' prefix.
        """
        if "smartchannel[" in line:
            parts = line.split("smartchannel[", 1)
            if len(parts) > 1 and "]:" in parts[1]:
                return parts[1].split("]:", 1)[1].strip()
        return line

    def _match_success(self, msg: str, timestamp: datetime) -> Optional[TransferSuccessEvent]:
        """
        Checks if the message indicates a successful transfer.
        If matched, parses transfer time and returns TransferSuccessEvent.
        """
        for pattern in SUCCESS_PATTERNS:
            match = pattern.search(msg)
            if match:
                filename = match.group(1)
                time_match = TIME_PATTERN.search(msg)
                transfer_time_ms = int(time_match.group(1)) if time_match else 0

                return TransferSuccessEvent(
                    session_name=self.session_name,
                    filename=filename,
                    transfer_time_ms=transfer_time_ms,
                    timestamp=timestamp,
                )
        return None

    def _match_failure(self, msg: str, timestamp: datetime) -> Optional[TransferFailedEvent]:
        """
        Checks if the message indicates a failed transfer.
        If matched, extracts the reason and returns TransferFailedEvent.
        """
        for pattern in FAILURE_PATTERNS:
            match = pattern.search(msg)
            if match:
                filename = match.group(1)
                reason = "Unknown transfer failure"
                if len(match.groups()) > 1 and match.group(2):
                    reason = match.group(2).strip()

                return TransferFailedEvent(
                    session_name=self.session_name,
                    filename=filename,
                    reason=reason,
                    timestamp=timestamp,
                )
        return None
