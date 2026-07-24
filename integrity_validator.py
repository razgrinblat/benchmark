import hashlib
import logging
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    is_valid: bool
    total_files: int
    matched_files: int
    missing_files: list[str]
    corrupted_files: list[str]
    details: str


def _calculate_md5(file_path: Path) -> str:
    """Calculates MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
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
        tx_files = {f.name: f for f in tx_dir.glob("*.bin")}
        rx_files = {f.name: f for f in rx_dir.glob("*.bin")}

        total_tx = len(tx_files)
        missing_files = []
        corrupted_files = []
        matched = 0

        logger.info(f"Validating file integrity: Tx ({total_tx} files) vs Rx ({len(rx_files)} files)")

        for name, tx_file in tx_files.items():
            if name not in rx_files:
                missing_files.append(name)
                logger.warning(f"File missing in Rx: {name}")
                continue

            rx_file = rx_files[name]

            # Compare file size first
            if tx_file.stat().st_size != rx_file.stat().st_size:
                corrupted_files.append(name)
                logger.warning(f"File size mismatch for {name}: Tx={tx_file.stat().st_size}, Rx={rx_file.stat().st_size}")
                continue

            # Compare MD5 checksums
            tx_md5 = _calculate_md5(tx_file)
            rx_md5 = _calculate_md5(rx_file)

            if tx_md5 != rx_md5:
                corrupted_files.append(name)
                logger.warning(f"MD5 mismatch for {name}: Tx={tx_md5}, Rx={rx_md5}")
            else:
                matched += 1

        is_valid = (len(missing_files) == 0) and (len(corrupted_files) == 0) and (matched == total_tx)
        status_str = "PASSED" if is_valid else "FAILED"

        details = (
            f"Validation {status_str}: {matched}/{total_tx} matched. "
            f"Missing: {len(missing_files)}, Corrupted: {len(corrupted_files)}"
        )
        logger.info(details)

        return ValidationResult(
            is_valid=is_valid,
            total_files=total_tx,
            matched_files=matched,
            missing_files=missing_files,
            corrupted_files=corrupted_files,
            details=details,
        )
