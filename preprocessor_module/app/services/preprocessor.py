import io

import joblib
import numpy as np
import pandas as pd

from app.config import Config
from app.utils.logger import setup_logger


class PreprocessorService:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.logger = setup_logger(__name__, cfg.LOG_LEVEL)
        self.feature_columns = cfg.FEATURE_COLUMNS
        self.scaler = self._load_scaler(cfg.SCALER_PATH)

    def _load_scaler(self, path: str):
        try:
            scaler = joblib.load(path)
            self.logger.info("Scaler loaded", extra={"path": path})
            return scaler
        except FileNotFoundError:
            self.logger.error("Scaler file not found", extra={"path": path})
            raise

    # CICFlowMeter real output uses abbreviated names.
    # Map them to the CICIDS2017 dataset names used by our scaler.
    COLUMN_RENAME_MAP = {
        "Dst Port": "Destination Port",
        "Tot Fwd Pkts": "Total Fwd Packets",
        "Tot Bwd Pkts": "Total Backward Packets",
        "TotLen Fwd Pkts": "Total Length of Fwd Packets",
        "TotLen Bwd Pkts": "Total Length of Bwd Packets",
        "Fwd Pkt Len Max": "Fwd Packet Length Max",
        "Fwd Pkt Len Min": "Fwd Packet Length Min",
        "Fwd Pkt Len Mean": "Fwd Packet Length Mean",
        "Fwd Pkt Len Std": "Fwd Packet Length Std",
        "Bwd Pkt Len Max": "Bwd Packet Length Max",
        "Bwd Pkt Len Min": "Bwd Packet Length Min",
        "Bwd Pkt Len Mean": "Bwd Packet Length Mean",
        "Bwd Pkt Len Std": "Bwd Packet Length Std",
        "Flow Byts/s": "Flow Bytes/s",
        "Flow Pkts/s": "Flow Packets/s",
        "Fwd IAT Tot": "Fwd IAT Total",
        "Bwd IAT Tot": "Bwd IAT Total",
        "Fwd Header Len": "Fwd Header Length",
        "Bwd Header Len": "Bwd Header Length",
        "Fwd Pkts/s": "Fwd Packets/s",
        "Bwd Pkts/s": "Bwd Packets/s",
        "Pkt Len Min": "Min Packet Length",
        "Pkt Len Max": "Max Packet Length",
        "Pkt Len Mean": "Packet Length Mean",
        "Pkt Len Std": "Packet Length Std",
        "Pkt Len Var": "Packet Length Variance",
        "FIN Flag Cnt": "FIN Flag Count",
        "SYN Flag Cnt": "SYN Flag Count",
        "RST Flag Cnt": "RST Flag Count",
        "PSH Flag Cnt": "PSH Flag Count",
        "ACK Flag Cnt": "ACK Flag Count",
        "URG Flag Cnt": "URG Flag Count",
        "ECE Flag Cnt": "ECE Flag Count",
        "Pkt Size Avg": "Average Packet Size",
        "Fwd Seg Size Avg": "Avg Fwd Segment Size",
        "Bwd Seg Size Avg": "Avg Bwd Segment Size",
        "Fwd Byts/b Avg": "Fwd Avg Bytes/Bulk",
        "Fwd Pkts/b Avg": "Fwd Avg Packets/Bulk",
        "Fwd Blk Rate Avg": "Fwd Avg Bulk Rate",
        "Bwd Byts/b Avg": "Bwd Avg Bytes/Bulk",
        "Bwd Pkts/b Avg": "Bwd Avg Packets/Bulk",
        "Bwd Blk Rate Avg": "Bwd Avg Bulk Rate",
        "Subflow Fwd Pkts": "Subflow Fwd Packets",
        "Subflow Fwd Byts": "Subflow Fwd Bytes",
        "Subflow Bwd Pkts": "Subflow Bwd Packets",
        "Subflow Bwd Byts": "Subflow Bwd Bytes",
        "Init Fwd Win Byts": "Init_Win_bytes_forward",
        "Init Bwd Win Byts": "Init_Win_bytes_backward",
        "Fwd Act Data Pkts": "act_data_pkt_fwd",
        "Fwd Seg Size Min": "min_seg_size_forward",
    }

    def preprocess(self, csv_bytes: bytes) -> dict:
        df = pd.read_csv(io.BytesIO(csv_bytes))
        df.columns = df.columns.str.strip()

        if len(df) == 0:
            return {
                "row_count": 0,
                "feature_count": len(self.feature_columns),
                "features": [],
                "feature_names": self.feature_columns,
                "labels": None,
            }

        # Rename CICFlowMeter abbreviated column names to CICIDS2017 names
        df = df.rename(columns=self.COLUMN_RENAME_MAP)

        # Handle duplicate "Fwd Header Length" columns from CICFlowMeter.
        # The raw CSV has two columns named "Fwd Header Length".
        # pandas reads them as-is (both named "Fwd Header Length").
        # The scaler expects the second one as "Fwd Header Length.1".
        dupes = df.columns[df.columns.duplicated()].unique().tolist()
        if "Fwd Header Length" in dupes:
            cols = list(df.columns)
            seen = False
            for i, c in enumerate(cols):
                if c == "Fwd Header Length":
                    if seen:
                        cols[i] = "Fwd Header Length.1"
                    seen = True
            df.columns = cols

        # Extract labels if present
        labels = None
        if "Label" in df.columns:
            labels = df["Label"].tolist()
            df = df.drop(columns=["Label"])

        # Select the expected feature columns, fill missing ones with 0
        missing = [c for c in self.feature_columns if c not in df.columns]
        if missing:
            self.logger.warning(
                "CSV missing columns, filling with 0",
                extra={"missing_count": len(missing), "missing": missing[:5]},
            )
            for col in missing:
                df[col] = 0.0

        df = df[self.feature_columns]

        # Clean infinities and NaNs
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.fillna(df.median(numeric_only=True))

        # If any column is still all-NaN (e.g. single-row with inf), fill with 0
        df = df.fillna(0)

        # Scale
        scaled = self.scaler.transform(df).astype("float32")

        self.logger.info(
            "Preprocessing complete",
            extra={"rows": len(scaled), "features": scaled.shape[1]},
        )

        return {
            "row_count": int(scaled.shape[0]),
            "feature_count": int(scaled.shape[1]),
            "features": scaled.tolist(),
            "feature_names": self.feature_columns,
            "labels": labels,
        }
