from dataclasses import dataclass


@dataclass
class CommandResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration: float

@dataclass
class UploadResult:
    local_file: str
    remote_file: str
    duration: float


class BenchmarkError(Exception):
    """Base exception for benchmark framework."""


class SSHConnectionError(BenchmarkError):
    pass


class CommandExecutionError(BenchmarkError):

    def __init__(self, result: CommandResult):
        self.result = result

        super().__init__(
            f"Command '{result.command}' failed "
            f"(exit code={result.exit_code})\n"
            f"output:\n{result.stdout}"
        )

class UploadError(BenchmarkError):

    def __init__(
            self,
            local_file: str,
            remote_file: str,
            reason: Exception,
    ):
        super().__init__(
            f"Failed uploading '{local_file}' "
            f"to '{remote_file}': {reason}"
        )

        self.local_file = local_file
        self.remote_file = remote_file
        self.reason = reason