import logging
from pathlib import Path
from abc import ABC, abstractmethod
from dataclasses import dataclass
from dut import Dut
from session_config_deploy import deploy_to_duts

logger = logging.getLogger(__name__)


@dataclass
class SetupContext:

    tx: Dut
    rx: Dut
    benchmark_directory: str
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
        logger.info("Binaries uploaded successfully")

class MountDirectories(SetupStep):
    def run(self, context: SetupContext) -> None:
        logger.info("Mounting directories...")
        context.tx.mount(share=Path(context.benchmark_directory) / "Tx", mount_point="/SMARTCHANNEL/TX", host_settings=context.host_settings)
        context.rx.mount(share=Path(context.benchmark_directory) / "Rx", mount_point="/SMARTCHANNEL/RX", host_settings=context.host_settings)


class DeploySessionConfig(SetupStep):

    def run(self, context: SetupContext) -> None:
        deploy_to_duts(context.tx, context.rx, context.config)