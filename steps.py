from json import decoder
import logging
from pathlib import Path
from abc import ABC, abstractmethod
from dataclasses import dataclass
from dut import Dut

logger = logging.getLogger(__name__)


@dataclass
class SetupContext:

    tx: Dut
    rx: Dut
    host_settings: dict


class SetupStep(ABC):

    @abstractmethod
    def run(self, context: SetupContext) -> None:
        pass


class ConnectStep(SetupStep):

    def run(self, context: SetupContext) -> None:
        logger.info("Connecting to Tx...")
        context.tx.connect()

        logger.info("Connecting to Rx...")
        context.rx.connect()


class UploadBinaries(SetupStep):

    def run(self, context: SetupContext) -> None:
        logger.info("Uploading binaries...")
        context.tx.upload("tx-service.exe", "/var/smartchannel/tx-service.exe")
        context.rx.upload("rx-service.exe", "/var/smartchannel/rx-service.exe")
        context.tx.ssh.run_checked("sudo whoami")
        
        logger.info("Binaries uploaded successfully")

class MountDirectories(SetupStep):

    def run(self, context: SetupContext) -> None:
        logger.info("Mounting directories...")

        context.tx.mount(
            share_name=context.host_settings.get("tx").get("share_name") + "/Tx",
            mount_point="/SMARTCHANNEL/TX",
            ip=context.host_settings.get("ip"),
            username=context.host_settings.get("username"),
            password=context.host_settings.get("password"),
        )   

        context.rx.mount(
            share_name=context.host_settings.get("rx").get("share_name") + "/Rx",
            mount_point="/SMARTCHANNEL/RX",
            ip=context.host_settings.get("ip"),
            username=context.host_settings.get("username"),
            password=context.host_settings.get("password"),
        )
        
