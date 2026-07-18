import json
import logging
from dut import Dut

logger = logging.getLogger(__name__)

REMOTE_SESSION_CONFIG_DIR = "/var/smartchannel/SessionConfig"


def _build_session_config(test_name: str, config: dict) -> dict:
    """
    Parses a test name like 'NoFec-ManyMediumFiles-LargeChunkSize-sequential'
    and returns the corresponding session config dict.
    """
    fec_key, _, chunk_key, _ = test_name.split('-')

    return {
        "ChunkSize": config['chunkSize_setting'][chunk_key],
        "PacketLossTolerance": config['fec_settings'][fec_key],
        "SyncDirectory": f"/SMART_CHANNEL/TX_SYNC/{test_name}",
    }


def _write_config_to_dut(dut: Dut, test_name: str, config_json: str):
    """Writes a session config JSON string to a file on the DUT over SSH."""
    remote_path = f"{REMOTE_SESSION_CONFIG_DIR}/{test_name}.json"
    escaped = config_json.replace("'", "'\\''")
    dut.ssh.run_checked(f"echo '{escaped}' > {remote_path}")


def deploy_to_duts(tx: Dut, rx: Dut, config: dict):
    """
    Uploads a session config JSON file for each test to both Tx and Rx DUTs.
    Assumes both DUTs are already connected.
    """
    for test_name in config.get('tests', []):
        session_config = _build_session_config(test_name, config)
        config_json = json.dumps(session_config, indent=4)

        logger.info(f"Deploying session config: {test_name}")
        _write_config_to_dut(tx, test_name, config_json)
        _write_config_to_dut(rx, test_name, config_json)
        logger.info(f"Deployed: {test_name}")
