# config.py

import os
import tempfile as _tf

# When running in Docker, these are /pcap, /flow, /code
# When running locally (dummy mode), use temp directories
_local = os.getenv("CICFLOW_LOCAL", "false").lower() == "true"

PCAP_DIR = os.getenv("PCAP_DIR", os.path.join(_tf.gettempdir(), "cicflow_pcap") if _local else "/pcap")
FLOW_DIR = os.getenv("FLOW_DIR", os.path.join(_tf.gettempdir(), "cicflow_flow") if _local else "/flow")
CODE_DIR = os.getenv("CODE_DIR", "/code")

# ASSUMED FOR NOW:
# Only one job at a time, blocking execution
ALLOW_CONCURRENT_JOBS = False

# ASSUMED FOR NOW:
# This command is correct and blocking
GRADLE_COMMAND = [
    "gradle",
    "--no-daemon",
    "-Pcmdargs=/pcap:/flow",
    "runcmd"
]

# Optional safety (can tune later)
COMMAND_TIMEOUT_SECONDS = None  # None = wait forever


# ASSUMED FOR NOW:
# Dummy processing mode enabled (no Gradle execution)
DUMMY_PROCESSING_MODE = False


# Added CICFLOW_LOCAL environment variable support

# # Production defaults
