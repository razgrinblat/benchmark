"""Events used for communication between benchmark components.

The event flow:

    LogMonitor
        |
        v
    Event Queue
        |
        v
    SessionManager
        |
        v
    MetricsManager

Events are immutable messages that describe something
that happened during the benchmark session.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TransferSuccessEvent:
    session_name: str
    filename: str
    transfer_time_ms: int
    timestamp: datetime


@dataclass(frozen=True)
class TransferFailedEvent:
    session_name: str
    filename: str
    reason: str
    timestamp: datetime


@dataclass(frozen=True)
class LogMonitorErrorEvent:
    reason: str
    timestamp: datetime


@dataclass(frozen=True)
class FileGenerationFailedEvent:
    reason: str
    timestamp: datetime
