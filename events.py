
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
    """
    Event generated when a file transfer completes successfully.

    Attributes:
        session_name:
            Unique identifier of the benchmark session.

        filename:
            Name of the transferred file.

        transfer_time_ms:
            Time required to transfer the file in milliseconds.

        timestamp:
            Time when the event was generated.
    """

    session_name: str
    filename: str
    transfer_time_ms: int
    timestamp: datetime



@dataclass(frozen=True)
class TransferFailedEvent:
    """
    Event generated when a file transfer fails.

    Attributes:
        session_name:
            Unique identifier of the benchmark session.

        filename:
            Name of the file that failed to transfer.

        reason:
            Error description extracted from SmartChannel logs.

        timestamp:
            Time when the event was generated.
    """

    session_name: str
    filename: str
    reason: str
    timestamp: datetime



@dataclass(frozen=True)
class LogMonitorErrorEvent:
    """
    Event generated when the log monitoring mechanism fails.

    Examples:
        - SSH connection lost.
        - journalctl command failed.
        - Remote command terminated unexpectedly.

    Attributes:
        reason:
            Description of the monitoring failure.

        timestamp:
            Time when the error happened.
    """

    reason: str
    timestamp: datetime



@dataclass(frozen=True)
class FileGenerationFailedEvent:
    """
    Event generated when payload file generation fails.

    This event is produced by FileGenerator and consumed
    by SessionManager.

    Examples:
        - Disk full.
        - Permission denied.
        - Cannot create file.

    Attributes:
        reason:
            Description of the generation failure.

        timestamp:
            Time when the failure occurred.
    """

    reason: str
    timestamp: datetime