from time import perf_counter
from utils import load_config
import paramiko
from exceptions import (
    SSHConnectionError,
    CommandExecutionError,
    CommandResult, UploadResult, UploadError
)


class SSHClient:

    def __init__(self, host: str, username: str, password: str, timeout: int = 10,):
        self._host = host
        self._username = username
        self._password = password
        self._timeout = timeout
        self._client = None

    def connect(self):

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
            raise SSHConnectionError(
                f"Failed connecting to {self._host}"
            ) from exc

    def disconnect(self):
        if self._client:
            self._client.close()

    def run(self, command: str, role: str = None) -> CommandResult:
        password = self._password
        if role.lower() in ("tx", "rx"):
            try:
                config = load_config()
                password = config["endpoint_setting"][role]["password"]
            except Exception:
                pass

        start = perf_counter()
        stdin, stdout, stderr = self._client.exec_command(command, get_pty=True)

        if password:
            stdin.write(password + "\n")
            stdin.flush()

        end = perf_counter()
        full_output = stdout.read().decode(errors="ignore")
        exit_code = stdout.channel.recv_exit_status()

        return CommandResult(
            command=command,
            exit_code=exit_code,
            stdout=full_output,
            stderr="",
            duration=end - start
        )

    def run_checked(self, command: str, role: str = None) -> CommandResult:
        result = self.run(command, role)
        if result.exit_code != 0:
            raise CommandExecutionError(result)
        return result

    def upload(self, local_file: str, remote_file: str) -> UploadResult:
        sftp = self._client.open_sftp()
        try:
            start = perf_counter()
            sftp.put(local_file, remote_file)
            end = perf_counter()
        except Exception as e:
            raise UploadError(local_file, remote_file, e) from e

        finally:
            sftp.close()

        return UploadResult(
            local_file=local_file,
            remote_file=remote_file,
            duration=end - start,
        )