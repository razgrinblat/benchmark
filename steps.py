from dataclasses import dataclass
from abc import abstractmethod
from abc import ABC
from dut import Dut


@dataclass
class SetupContext:

    tx: Dut
    rx: Dut
    benchmark_directory: str

class SetupStep(ABC):

    @abstractmethod
    def run(self, context: SetupContext) -> None:
        pass

class ConnectStep(SetupStep):

    def run(self, context: SetupContext) -> None:

        context.logger.info("Connecting to Tx DUT...")
        context.tx.connect()

        context.logger.info("Connecting to Rx DUT...")
        context.rx.connect()


class UploadBinaries(SetupStep):

    def run(self, context: SetupContext) -> None:
        context.tx.upload("./tx-service", "/var/smartchannel")
        context.rx.upload("./rx-service", "/var/smartchannel")