import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from dut import Dut
from config import DutPaths

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


class MountDirectories(SetupStep):

    def run(self, context: SetupContext) -> None:
        logger.info("Mounting directories...")
        dut_paths = DutPaths.load()

        context.tx.mount(
            share_name=context.host_settings.get("tx").get("share_name") + "/Tx",
            mount_point=dut_paths.tx_mount_point,
            ip=context.host_settings.get("ip"),
            username=context.host_settings.get("username"),
            password=context.host_settings.get("password"),
        )

        context.rx.mount(
            share_name=context.host_settings.get("rx").get("share_name") + "/Rx",
            mount_point=dut_paths.rx_mount_point,
            ip=context.host_settings.get("ip"),
            username=context.host_settings.get("username"),
            password=context.host_settings.get("password"),
        )
