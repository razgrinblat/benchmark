import logging
from logger import setup_logging
from dut import Dut
from utils import load_config, create_benchmark_directory
from steps import SetupContext, ConnectStep, UploadBinaries, MountDirectories, DeploySessionConfig


def main():
    config = load_config()
    host_settings = config.get("host_settings", {})
    shared_local_path = host_settings.get("shared_directory_local_path", ".")

    benchmark_dir = create_benchmark_directory(shared_local_path)
    setup_logging(log_directory=str(benchmark_dir / "Results"))

    logger = logging.getLogger(__name__)
    logger.info("Starting benchmark setup")

    endpoints = config['endpoint_setting']

    tx = Dut.from_config("Tx", endpoints['tx'])
    rx = Dut.from_config("Rx", endpoints['rx'])

    context = SetupContext(
        tx=tx,
        rx=rx,
        benchmark_directory=str(benchmark_dir),
        host_settings=config['host_settings'],
    )

    steps = [
        ConnectStep(),
        UploadBinaries(),
        MountDirectories(),
        DeploySessionConfig(),
    ]

    for step in steps:
        logger.info(f"Running {step.__class__.__name__}")
        step.run(context)

    rx.disconnect()
    tx.disconnect()


if __name__ == "__main__":
    main()