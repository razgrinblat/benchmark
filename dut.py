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
        result = self.ssh.run_checked(f"systemctl restart {service}", role=self.name)
        logger.info(f"Restarted {service} on {self.name} ({result.duration:.2f}s)")

    def is_service_active(self, service: str) -> bool:
        """Returns True if the systemd service is currently active."""
        result = self.ssh.run_checked(f"systemctl is-active {service}", role=self.name)
        return result.exit_code == 0 and result.stdout.strip() == "active"

    # ------------------------------------------------------------------
    # Mount
    # ------------------------------------------------------------------

    def mount(self, share: str, mount_point: str, host_settings: dict) -> None:
        """
        Mount a remote CIFS share using credentials from host_settings.
        Expected host_settings keys: ip, username, password, share_name, shared_directory_local_path
        """
        ip = host_settings["ip"]
        username = host_settings["username"]
        password = host_settings["password"]
        share_name = host_settings.get("share_name", "BenchmarkShare")
        local_base = Path(host_settings.get("shared_directory_local_path", "."))

        # share is the absolute local path on the Windows host.
        # Find the path relative to the shared base directory (e.g. "Tests/2026-07-18_11-56-40/Tx")
        try:
            relative_path = Path(share).relative_to(local_base)
        except ValueError:
            # Fall back to using the last parts of the path if not matching base_dir
            relative_path = Path(share)

        # Ensure path separators are forward slashes for Linux CIFS mount
        share_str = str(relative_path).replace("\\", "/")

        options = f"username={username},password={password},uid=$(id -u),gid=$(id -g)"
        mount_cmd = f"sudo mount -t cifs //{ip}/{share_name}/{share_str} {mount_point} -o {options}"

        for cmd in [f"mkdir -p {mount_point}", mount_cmd]:
            self.ssh.run_checked(cmd, role=self.name)

    def unmount(self, mount_point: str) -> None:
        """Unmount a mount point."""
        self.ssh.run_checked(f"sudo umount {mount_point}", role=self.name)