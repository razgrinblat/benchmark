from time import perf_counter, sleep
from typing import Optional, List
import threading
import paramiko
import logging
from paramiko import Channel

from exceptions import (
    SSHConnectionError,
    CommandExecutionError,
    CommandResult,
    UploadResult,
    UploadError,
)

PASSWORD_PROMPT_KEYWORDS = ("password", "[sudo]", "passcode")
CHUNK_SIZE = 1024

logger = logging.getLogger(__name__)

class SSHClient:
    """
    SSH Client wrapper over Paramiko with support for interactive password prompts,
    checked command execution, and SFTP file uploads.
    """

    def __init__(self, host: str, username: str, password: str, timeout: int = 10) -> None:
        self._host = host
        self._username = username
        self._password = password
        self._timeout = timeout
        self._client: Optional[paramiko.SSHClient] = None

    def __enter__(self) -> "SSHClient":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()

    def connect(self) -> None:
        """Establishes SSH connection to the remote host."""
        try:
            self._client = paramiko.SSHClient()
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._client.connect(
                hostname=self._host,
                username=self._username,
                password=self._password,
                timeout=self._timeout,
            )
        except Exception as exc:
            raise SSHConnectionError(f"Failed connecting to {self._host}") from exc

    def disconnect(self) -> None:
        """Closes active SSH client connection."""
        if self._client:
            self._client.close()
            self._client = None

    def run(self, command: str) -> CommandResult:
        """
        Executes a command interactively over PTY, handling password prompts if requested.

        Note: stdin MUST be kept alive for the duration of the call. Discarding it
        causes ChannelStdinFile.close() -> channel.shutdown_write() -> eof_sent=True,
        which makes all subsequent channel.send() calls silently return 0.
        """
        start = perf_counter()
        stdin, stdout, _ = self._client.exec_command(command, get_pty=True)
        channel = stdout.channel

        stdout_str, stderr_str = self._read_channel_interactively(channel, stdin)
        exit_code = channel.recv_exit_status()
        end = perf_counter()

        return CommandResult(
            command=command,
            exit_code=exit_code,
            stdout=stdout_str,
            stderr=stderr_str,
            duration=end - start,
        )

    def run_checked(self, command: str) -> CommandResult:
        """Executes a command and raises CommandExecutionError if exit code is non-zero."""
        result = self.run(command)
        if result.exit_code != 0:
            raise CommandExecutionError(result)
        return result

    def upload(self, local_file: str, remote_file: str) -> UploadResult:
        """Uploads a local file to a remote destination via SFTP."""
        sftp = self._client.open_sftp()
        try:
            start = perf_counter()
            sftp.put(local_file, remote_file)
            end = perf_counter()
        except Exception as exc:
            raise UploadError(local_file, remote_file, exc) from exc
        finally:
            sftp.close()

        return UploadResult(
            local_file=local_file,
            remote_file=remote_file,
            duration=end - start,
        )

    # ------------------------------------------------------------------
    # Helper methods for interactive stream processing
    # ------------------------------------------------------------------

    def _read_channel_interactively(self, channel: Channel, stdin) -> tuple[str, str]:
        """Reads output chunks from channel while listening for password prompts."""
        stdout_chunks: List[str] = []
        stderr_chunks: List[str] = []
        password_sent = False

        while not channel.exit_status_ready():
            if channel.recv_ready():
                chunk = channel.recv(CHUNK_SIZE).decode(errors="ignore")
                stdout_chunks.append(chunk)

                if not password_sent and self._is_password_prompt("".join(stdout_chunks)):
                    stdin.write(f"{self._password}\n")
                    stdin.flush()
                    password_sent = True

            elif channel.recv_stderr_ready():
                chunk = channel.recv_stderr(CHUNK_SIZE).decode(errors="ignore")
                stderr_chunks.append(chunk)
            else:
                sleep(0.02)

        self._drain_remaining_output(channel, stdout_chunks, stderr_chunks)
        return "".join(stdout_chunks), "".join(stderr_chunks)

    @staticmethod
    def _is_password_prompt(output: str) -> bool:
        """Returns True if the buffered output contains a password prompt."""
        lower_output = output.lower()
        return any(keyword in lower_output for keyword in PASSWORD_PROMPT_KEYWORDS)

    @staticmethod
    def _drain_remaining_output(channel: Channel, stdout_chunks: List[str], stderr_chunks: List[str]) -> None:
        """Drains any leftover bytes in stdout/stderr buffers after process exit."""
        while channel.recv_ready():
            stdout_chunks.append(channel.recv(CHUNK_SIZE).decode(errors="ignore"))

        while channel.recv_stderr_ready():
            stderr_chunks.append(channel.recv_stderr(CHUNK_SIZE).decode(errors="ignore"))