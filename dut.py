import logger
from multiprocessing import sharedctypes
import logging
from pathlib import Path

from exceptions import CommandResult, UploadResult
from ssh_client import SSHClient

logger = logging.getLogger(__name__)


class Dut:

    def __init__(self, name: str, ip: str, username: str, password: str) -> None:
        self.name = name
        self.ssh = SSHClient(ip, username, password)

    @classmethod
    def from_config(cls, name: str, endpoint: dict) -> "Dut":
        """Creates a Dut instance from a config endpoint dict."""
        return cls(
            name=name,
            ip=endpoint["ip"],
            username=endpoint["username"],
            password=endpoint["password"],
        )

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self) -> None:
        self.ssh.connect()

    def disconnect(self) -> None:
        self.ssh.disconnect()

    def __enter__(self) -> "Dut":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        try:
            self.disconnect()
        except Exception as e:
            logger.warning(f"Error disconnecting {self.name}: {e}")

    # ------------------------------------------------------------------
    # File transfer
    # ------------------------------------------------------------------

    def upload(self, local: str, remote: str) -> UploadResult:
        result = self.ssh.upload(local, remote)
        logger.info(f"Uploaded {local} to {remote} on {self.name} ({result.duration:.2f}s)")
        return result

    # ------------------------------------------------------------------
    # Service management
    # ------------------------------------------------------------------

    def restart_service(self, service: str) -> None:
        result = self.ssh.run_checked(f"systemctl restart {service}")
        logger.info(f"Restarted {service} on {self.name} ({result.duration:.2f}s)")

    def is_service_active(self, service: str) -> bool:
        """Returns True if the systemd service is currently active."""
        result = self.ssh.run_checked(f"systemctl is-active {service}")
        return result.exit_code == 0 and result.stdout.strip() == "active"

    # ------------------------------------------------------------------
    # Mount
    # ------------------------------------------------------------------

    def mount(self, share_name: str, mount_point: str, ip: str, username: str, password: str) -> None:
        """
        Mount a remote CIFS share using credentials from host_settings.
        """

        options = f"username={username},password={password},uid=$(id -u),gid=$(id -g)"
        mount_cmd = f"sudo -S mount -t cifs //{ip}/{share_name} {mount_point} -o {options}"
        self.ssh.run_checked(mount_cmd)

    def unmount(self, mount_point: str) -> None:
        """Unmount a mount point."""
        self.ssh.run_checked(f"sudo umount {mount_point}")