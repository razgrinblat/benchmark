from pathlib import Path
from datetime import datetime

from logger import BenchmarkLogger
from dut import Dut

from steps import ConnectStep, UploadBinaries , SetupContext

logger = BenchmarkLogger.get_logger()

def create_benchmark_directory():

    timestamp = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    benchmark_dir = Path("Test") / timestamp

    results_dir = benchmark_dir / "Results"
    tx_dir = benchmark_dir / "Tx"
    rx_dir = benchmark_dir / "Rx"

    results_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    tx_dir.mkdir(exist_ok=True)
    rx_dir.mkdir(exist_ok=True)

    return benchmark_dir


def main():

    benchmark_directory = create_benchmark_directory()
    BenchmarkLogger.initialize(log_directory=str(benchmark_directory / "Results"))
    logger.info( "Starting benchmark setup")

    tx = Dut(name="Tx" ,ip="192.168.1.10" ,username="root" ,password="root")
    rx = Dut(name="Rx" ,ip="192.168.1.11" , username="root" ,password="root")

    context = SetupContext(tx= tx ,rx= rx ,benchmark_directory= str(benchmark_directory))

    steps = [ConnectStep(), UploadBinaries]

    for step in steps:
        logger.info(
            f"Running {step.__class__.__name__}"
        )
        step.run(context)



if __name__ == "__main__":
    main()