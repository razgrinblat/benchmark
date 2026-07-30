import hashlib
import logging
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

logger = logging.getLogger(__name__)

MD5_CHUNK_SIZE = 1024 * 1024
BIN_FILE_PATTERN = "*.bin"


@dataclass
class ValidationResult:
    is_valid: bool
    total_files: int
    matched_files: int
    missing_files: list[str]
    size_mismatched_files: list[str]
    corrupted_files: list[str]
    details: str


class ValidationStatus(Enum):
    MATCH = auto()
    SIZE_MISMATCH = auto()
    CORRUPTED = auto()


def _calculate_md5(file_path: Path) -> str:
    """Calculates MD5 hash of a file."""
    hash_md5 = hashlib.md5()

    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(MD5_CHUNK_SIZE), b""):
            hash_md5.update(chunk)

    return hash_md5.hexdigest()


class IntegrityValidator:
    """
    Validates file delivery and integrity between Tx payload folder and Rx target folder.
    """

    def validate_session_files(self, tx_dir: Path, rx_dir: Path) -> ValidationResult:
        """
        Compares transmitted files in tx_dir against received files in rx_dir.
        Verifies file existence, sizes, and MD5 hashes.
        """
        tx_files = self._get_bin_files(tx_dir)
        rx_files = self._get_bin_files(rx_dir)

        logger.info(f"Validating file integrity: Tx ({len(tx_files)} files) vs Rx ({len(rx_files)} files)")

        matched, missing_files, size_mismatched_files, corrupted_files = self._validate_files(
            tx_files,
            rx_files,
        )

        return self._build_validation_result(
            len(tx_files),
            matched,
            missing_files,
            size_mismatched_files,
            corrupted_files,
        )

    def _validate_files(self, tx_files: dict[str, Path], rx_files: dict[str, Path]) -> tuple[int, list[str], list[str], list[str]]:
        matched = 0
        missing_files: list[str] = []
        size_mismatched_files: list[str] = []
        corrupted_files: list[str] = []

        for name, tx_file in tx_files.items():
            if name not in rx_files:
                missing_files.append(name)
                logger.warning(f"File missing in Rx: {name}")
                continue

            rx_file = rx_files[name]
            status = self._verify_file_integrity(tx_file, rx_file)

            if status == ValidationStatus.MATCH:
                matched += 1
            elif status == ValidationStatus.SIZE_MISMATCH:
                size_mismatched_files.append(name)
            elif status == ValidationStatus.CORRUPTED:
                corrupted_files.append(name)

        return matched, missing_files, size_mismatched_files, corrupted_files

    def _build_validation_result(self, total_files: int, matched: int, missing_files: list[str], size_mismatched_files: list[str], corrupted_files: list[str]) -> ValidationResult:
        is_valid = (
            matched == total_files
            and not missing_files
            and not size_mismatched_files
            and not corrupted_files
        )

        status_str = "PASSED" if is_valid else "FAILED"

        details = (
            f"Validation {status_str}: {matched}/{total_files} matched. "
            f"Missing: {len(missing_files)}, "
            f"Size Mismatched: {len(size_mismatched_files)}, "
            f"Corrupted: {len(corrupted_files)}"
        )

        logger.info(details)

        return ValidationResult(
            is_valid=is_valid,
            total_files=total_files,
            matched_files=matched,
            missing_files=missing_files,
            size_mismatched_files=size_mismatched_files,
            corrupted_files=corrupted_files,
            details=details,
        )

    def _get_bin_files(self, directory: Path) -> dict[str, Path]:
        """Returns a mapping of filename to Path for all .bin files in a directory."""
        return {file.name: file for file in directory.glob(BIN_FILE_PATTERN)}

    def _verify_file_integrity(self, tx_file: Path, rx_file: Path) -> ValidationStatus:
        """
        Verifies size and MD5 hash between tx_file and rx_file.
        """
        if not self._check_size_match(tx_file, rx_file):
            return ValidationStatus.SIZE_MISMATCH

        if not self._check_md5_match(tx_file, rx_file):
            return ValidationStatus.CORRUPTED

        return ValidationStatus.MATCH

    def _check_size_match(self, tx_file: Path, rx_file: Path) -> bool:
        """Compares file sizes of tx_file and rx_file."""
        tx_size = tx_file.stat().st_size
        rx_size = rx_file.stat().st_size

        if tx_size != rx_size:
            logger.warning(
                f"File size mismatch for {tx_file.name}: Tx={tx_size}, Rx={rx_size}"
            )
            return False

        return True

    def _check_md5_match(self, tx_file: Path, rx_file: Path) -> bool:
        """Compares MD5 checksums of tx_file and rx_file."""
        tx_md5 = _calculate_md5(tx_file)
        rx_md5 = _calculate_md5(rx_file)

        if tx_md5 != rx_md5:
            logger.warning(
                f"MD5 mismatch for {tx_file.name}: Tx={tx_md5}, Rx={rx_md5}"
            )
            return False

        return True