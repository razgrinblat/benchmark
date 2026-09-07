import re
import logging
from datetime import datetime
from typing import Optional, Any

from config.dut_settings import LogFormats
from core.events import (
    TransferSuccessEvent,
    TransferFailedEvent,
)

logger = logging.getLogger(__name__)

# Matches ISO timestamps at the beginning of the log line
ISO_TS_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:?\d{2}|Z)?)")


class LogParser:
    """
    Parses remote system/service log lines into strongly typed benchmark events,
    matching the existing definitions in events.py.
    """

    def __init__(self, session_name: str) -> None:
        self.session_name = session_name
        log_formats = LogFormats.load()
        self.success_pattern = self._format_to_regex(log_formats.success_log_format)
        self.failure_pattern = self._format_to_regex(log_formats.failure_log_format)

    def _format_to_regex(self, format_str: str) -> re.Pattern:
        """
        Converts a user-defined log format string containing placeholders
        into a regular expression pattern with named capture groups.
        """
        placeholders = {
            "{filename}": r"(?P<filename>[\w\-\.]+)",
            "{time}": r"(?P<time>\d+)",
            "{error}": r"(?P<reason>.+)",
            "{reason}": r"(?P<reason>.+)",
        }

        # Split format string by placeholders (braces with word inside)
        parts = re.split(r"(\{[a-zA-Z_]+\})", format_str)
        regex_parts = []
        for part in parts:
            if part in placeholders:
                regex_parts.append(placeholders[part])
            elif part.startswith("{") and part.endswith("}"):
                # Capture any unknown placeholder as a named group with a general pattern
                group_name = part[1:-1]
                regex_parts.append(f"(?P<{group_name}>.+)")
            else:
                regex_parts.append(re.escape(part))

        return re.compile("".join(regex_parts), re.IGNORECASE)

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
        match = self.success_pattern.search(msg)
        if match:
            groups = match.groupdict()
            filename = groups.get("filename")
            
            transfer_time_ms = 0
            if "time" in groups:
                try:
                    transfer_time_ms = int(groups["time"])
                except ValueError:
                    logger.warning(f"Failed to parse time group: {groups['time']}")

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
        match = self.failure_pattern.search(msg)
        if match:
            groups = match.groupdict()
            filename = groups.get("filename")
            reason = groups.get("reason", "Unknown transfer failure").strip()

            return TransferFailedEvent(
                session_name=self.session_name,
                filename=filename,
                reason=reason,
                timestamp=timestamp,
            )
        return None
