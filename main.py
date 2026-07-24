from benchmark_controller import BenchmarkController


def main() -> None:
    controller = BenchmarkController(config_path="config.json")
    controller.start_benchmark()


if __name__ == "__main__":
    main()