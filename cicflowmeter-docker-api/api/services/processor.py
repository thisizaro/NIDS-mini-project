# services/processor.py

import subprocess
import threading
import time
import os
import csv
import random
from config import (
    GRADLE_COMMAND,
    CODE_DIR,
    COMMAND_TIMEOUT_SECONDS,
    ALLOW_CONCURRENT_JOBS,
    DUMMY_PROCESSING_MODE,
    FLOW_DIR,
)

_processing_lock = threading.Lock()


class ProcessingAlreadyRunning(Exception):
    pass


# CICFlowMeter output columns (matches real output)
CICFLOW_COLUMNS = [
    "Flow ID", "Source IP", "Source Port", "Destination IP", "Destination Port",
    "Protocol", "Timestamp", "Flow Duration", "Total Fwd Packets",
    "Total Backward Packets", "Total Length of Fwd Packets",
    "Total Length of Bwd Packets", "Fwd Packet Length Max",
    "Fwd Packet Length Min", "Fwd Packet Length Mean", "Fwd Packet Length Std",
    "Bwd Packet Length Max", "Bwd Packet Length Min", "Bwd Packet Length Mean",
    "Bwd Packet Length Std", "Flow Bytes/s", "Flow Packets/s",
    "Flow IAT Mean", "Flow IAT Std", "Flow IAT Max", "Flow IAT Min",
    "Fwd IAT Total", "Fwd IAT Mean", "Fwd IAT Std", "Fwd IAT Max",
    "Fwd IAT Min", "Bwd IAT Total", "Bwd IAT Mean", "Bwd IAT Std",
    "Bwd IAT Max", "Bwd IAT Min", "Fwd PSH Flags", "Bwd PSH Flags",
    "Fwd URG Flags", "Bwd URG Flags", "Fwd Header Length", "Bwd Header Length",
    "Fwd Packets/s", "Bwd Packets/s", "Min Packet Length", "Max Packet Length",
    "Packet Length Mean", "Packet Length Std", "Packet Length Variance",
    "FIN Flag Count", "SYN Flag Count", "RST Flag Count", "PSH Flag Count",
    "ACK Flag Count", "URG Flag Count", "CWE Flag Count", "ECE Flag Count",
    "Down/Up Ratio", "Average Packet Size", "Avg Fwd Segment Size",
    "Avg Bwd Segment Size", "Fwd Header Length", "Fwd Avg Bytes/Bulk",
    "Fwd Avg Packets/Bulk", "Fwd Avg Bulk Rate", "Bwd Avg Bytes/Bulk",
    "Bwd Avg Packets/Bulk", "Bwd Avg Bulk Rate", "Subflow Fwd Packets",
    "Subflow Fwd Bytes", "Subflow Bwd Packets", "Subflow Bwd Bytes",
    "Init_Win_bytes_forward", "Init_Win_bytes_backward", "act_data_pkt_fwd",
    "min_seg_size_forward", "Active Mean", "Active Std", "Active Max",
    "Active Min", "Idle Mean", "Idle Std", "Idle Max", "Idle Min", "Label",
]


def _generate_dummy_csvs():
    """Generate realistic CICFlowMeter-style CSV output for testing."""
    os.makedirs(FLOW_DIR, exist_ok=True)
    file_path = os.path.join(FLOW_DIR, "flows.csv")

    with open(file_path, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CICFLOW_COLUMNS)

        labels = ["BENIGN", "BENIGN", "BENIGN", "DDoS", "DDoS",
                  "PortScan", "BENIGN", "DDoS", "BENIGN", "BENIGN"]

        for i in range(50):
            row = []
            for col in CICFLOW_COLUMNS:
                if col == "Flow ID":
                    row.append(f"192.168.1.{random.randint(1,254)}-10.0.0.{random.randint(1,254)}-{random.randint(1024,65535)}-{random.randint(80,8080)}-6")
                elif col == "Source IP":
                    row.append(f"192.168.1.{random.randint(1,254)}")
                elif col == "Destination IP":
                    row.append(f"10.0.0.{random.randint(1,254)}")
                elif col in ("Source Port", "Destination Port"):
                    row.append(random.randint(1, 65535))
                elif col == "Protocol":
                    row.append(6)
                elif col == "Timestamp":
                    row.append("2024-01-15 10:30:00")
                elif col == "Label":
                    row.append(labels[i % len(labels)])
                elif "Flag" in col or "Count" in col:
                    row.append(random.randint(0, 5))
                elif "Ratio" in col:
                    row.append(round(random.uniform(0, 2), 4))
                elif "Bytes/s" in col or "Packets/s" in col:
                    row.append(round(random.uniform(0, 100000), 2))
                elif "Duration" in col:
                    row.append(random.randint(0, 120000000))
                else:
                    row.append(round(random.uniform(0, 10000), 4))
            writer.writerow(row)


def run_processing_command():
    """Run CICFlowMeter or generate dummy output."""
    if not ALLOW_CONCURRENT_JOBS:
        if not _processing_lock.acquire(blocking=False):
            raise ProcessingAlreadyRunning()

    try:
        if DUMMY_PROCESSING_MODE:
            time.sleep(2)  # simulate processing time
            _generate_dummy_csvs()
        else:
            subprocess.run(
                GRADLE_COMMAND,
                cwd=CODE_DIR,
                check=True,
                timeout=COMMAND_TIMEOUT_SECONDS,
            )
    finally:
        if not ALLOW_CONCURRENT_JOBS:
            _processing_lock.release()

# Added realistic column generation for testing

# Handle zero-flow PCAP edge case
