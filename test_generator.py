import os
import logging
import datetime
import concurrent.futures
from pathlib import Path

logger = logging.getLogger(__name__)

_SCALE_TO_BYTES = {
    "KB": 1024,
    "MB": 1024 ** 2,
    "GB": 1024 ** 3,
}

_CHUNK_SIZE = 1024 * 1024  # 1MB read/write chunk


def _generate_file(file_path: Path, size_in_bytes: int):
    """Writes a file of exactly `size_in_bytes` bytes filled with random data."""
    random_chunk = os.urandom(min(_CHUNK_SIZE, size_in_bytes))

    with open(file_path, 'wb') as f:
        bytes_written = 0
        while bytes_written < size_in_bytes:
            write_size = min(len(random_chunk), size_in_bytes - bytes_written)
            f.write(random_chunk[:write_size])
            bytes_written += write_size

    logger.info(f"Generated: {file_path.name} ({size_in_bytes:,} bytes)")


def _create_test_files(test_dir: Path, test_name: str, file_settings: dict, mode: str):
    """Generates test files into `test_dir` either sequentially or in parallel."""
    file_count = file_settings['file_count']
    file_size = file_settings['file_size']
    file_scale = file_settings['file_scale'].upper()

    size_in_bytes = file_size * _SCALE_TO_BYTES[file_scale]
    file_paths = [test_dir / f"test_file_{i + 1}.bin" for i in range(file_count)]

    logger.info(f"[{test_name}] Generating {file_count} x {file_size}{file_scale} ({mode} mode)")

    if mode == 'parallel':
        with concurrent.futures.ProcessPoolExecutor() as executor:
            futures = [executor.submit(_generate_file, path, size_in_bytes) for path in file_paths]
            concurrent.futures.wait(futures)
    else:
        for path in file_paths:
            _generate_file(path, size_in_bytes)

    logger.info(f"[{test_name}] Done.")


def generate_all_tests(config: dict, base_tests_dir: Path):
    """
    Iterates over the tests in `config` and generates the corresponding
    test files under `base_tests_dir/<timestamp>/<test_name>/`.
    """
    timestamp = datetime.datetime.now().strftime("%d.%m.%Y-%H-%M-%S")
    run_dir = base_tests_dir / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    for test_name in config.get('tests', []):
        fec_key, files_key, chunk_key, mode = test_name.split('-')

        file_settings = config['file_settings'].get(files_key)
        if not file_settings:
            logger.error(f"[{test_name}] Unknown file_settings key: '{files_key}', skipping.")
            continue

        test_dir = run_dir / test_name
        test_dir.mkdir(exist_ok=True)

        try:
            _create_test_files(test_dir, test_name, file_settings, mode)
        except Exception:
            logger.exception(f"[{test_name}] File generation failed.")
