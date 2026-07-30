import os
import logging
import concurrent.futures
from pathlib import Path

logger = logging.getLogger(__name__)

_SCALE_TO_BYTES = {
    "KB": 1024,
    "MB": 1024 ** 2,
    "GB": 1024 ** 3,
}

_CHUNK_SIZE = 1024 * 1024  # 1MB chunk size


def _generate_single_file(file_path: Path, size_in_bytes: int) -> None:
    """Writes a file of exactly size_in_bytes filled with pseudo-random data."""
    random_chunk = os.urandom(min(_CHUNK_SIZE, size_in_bytes))
    with open(file_path, 'wb') as f:
        bytes_written = 0
        while bytes_written < size_in_bytes:
            write_size = min(len(random_chunk), size_in_bytes - bytes_written)
            f.write(random_chunk[:write_size])
            bytes_written += write_size


class FileGenerator:
    """
    Handles payload file generation for benchmark sessions (sequential or parallel).
    """

    def __init__(self, default_chunk_size: int = _CHUNK_SIZE) -> None:
        self.chunk_size = default_chunk_size

    def generate_files(self, target_dir: Path, file_setting: dict, mode: str) -> list[Path]:
        """
        Generates dummy test files in target_dir based on file_setting (file_count, file_size, file_scale).
        Mode can be 'sequential' or 'parallel'.
        Returns list of generated file paths.
        """
        target_dir.mkdir(parents=True, exist_ok=True)
        file_count = file_setting['file_count']
        file_size = file_setting['file_size']
        file_scale = file_setting['file_scale'].upper()

        size_in_bytes = file_size * _SCALE_TO_BYTES[file_scale]
        file_paths = [target_dir / f"{target_dir.name}_{i + 1}.bin" for i in range(file_count)]

        logger.info(f"Generating {file_count} x {file_size}{file_scale} in {target_dir.name} ({mode} mode)")

        if mode == 'parallel':
            with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
                futures = [executor.submit(_generate_single_file, path, size_in_bytes) for path in file_paths]
                concurrent.futures.wait(futures)
        else:
            for path in file_paths:
                _generate_single_file(path, size_in_bytes)

        logger.info(f"Successfully generated {file_count} files in {target_dir}")
        return file_paths
