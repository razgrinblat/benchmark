import argparse
from pathlib import Path
from core import BenchmarkController
from config import dut_settings


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "SmartChannel Benchmark Orchestrator\n\n"
            "This script automates the full lifecycle of transferring files between a Tx and Rx DUT "
            "(Device Under Test) via SSH and evaluating throughput/performance. It is capable of:\n"
            "  - Parallel or sequential file generation\n"
            "  - Live event-driven log monitoring via SSH\n"
            "  - Real-time throughput metrics aggregation\n"
            "  - MD5 file integrity validation\n"
            "  - Detailed results and CSV reporting"
        ),
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "-c", "--config", 
        type=str, 
        default="config.json", 
        help="Path to the benchmark configuration JSON file. (default: config.json)"
    )
    
    parser.add_argument(
        "--dut-settings", 
        type=str, 
        default="dut_settings.ini", 
        help="Path to the DUT settings INI file. (default: dut_settings.ini)"
    )

    parser.add_argument(
        "-m", "--mount", 
        action="store_true", 
        help="Automatically mount remote directories on the DUTs after establishing the SSH connection."
    )

    parser.add_argument(
        "-t", "--test", 
        type=str, 
        default=None, 
        help="Name of a specific test suite to run (e.g., 'test-1'). If omitted, all tests in the config are executed."
    )

    parser.add_argument(
        "-v", "--verbose", 
        action="store_true", 
        help="Enable verbose (DEBUG) logging output in the console."
    )

    args = parser.parse_args()

    # Override the default INI path globally if provided
    dut_settings._DEFAULT_INI_PATH = Path(args.dut_settings)

    # Initialize the benchmark controller with parsed arguments
    controller = BenchmarkController(args)
    controller.start_benchmark()


if __name__ == "__main__":
    main()