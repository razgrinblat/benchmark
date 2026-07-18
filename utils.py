import json
import logging
from pathlib import Path
from datetime import datetime


def load_config(path: str = "config.json") -> dict:
    with open(path, 'r') as f:
        return json.load(f)


def create_benchmark_directory(base_dir: str = ".") -> Path:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    benchmark_dir = Path(base_dir) / "Tests" / timestamp

    (benchmark_dir / "Results").mkdir(parents=True, exist_ok=True)
    (benchmark_dir / "Tx").mkdir(exist_ok=True)
    (benchmark_dir / "Rx").mkdir(exist_ok=True)

    return benchmark_dir
