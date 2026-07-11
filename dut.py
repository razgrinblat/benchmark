from exceptions import CommandResult, UploadResult
from ssh_client import SSHClient

class Dut:

    def __init__(self, name, ip, username, password):
        self.name = name
        self.ssh = SSHClient(ip ,username ,password)

    def connect(self):
        self.ssh.connect()
        self.ssh.run_checked("hostname")

    def disconnect(self):
        self.ssh.disconnect()

    def  execute(self, command) -> CommandResult:
        return self.ssh.run(command)

    def upload(self, local, remote) -> UploadResult:
        return self.ssh.upload(local, remote)

    def restart_service(self, service):
        command = f"systemctl restart {service}"
        return self.ssh.run_checked(command)

    def is_service_active(self,service: str,) -> bool:
        """
        Returns True if the service is active.
        """

        result = self.execute(
            f"systemctl is-active {service}"
        )

        return (
                result.exit_code == 0
                and result.stdout.strip() == "active"
        )

    def mount(self,share: str,mount_point: str,):
        """
        Mount a remote share.
        """

        commands = [
            f"mkdir -p {mount_point}",
            f"mount {share} {mount_point}",
        ]

        for cmd in commands:
            self.ssh.run_checked(cmd)