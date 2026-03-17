import json
import logging
import numpy as np
import pandas as pd
import joblib
import tensorflow as tf
from scipy.stats import weibull_min
from app.config import (
    MODEL_PATH, OPENMAX_PARAMS_PATH, SCALER_PATH, FEATURE_COLS_PATH,
    NUM_KNOWN_CLASSES, ALPHA_RANK, DISTANCE_TYPE, CLASS_NAMES,
    IMAGE_SIZE, IMAGE_PIXELS,
)

logger = logging.getLogger(__name__)


class InferenceService:
    def __init__(self):
        self.model = None
        self.logit_model = None
        self.scaler = None
        self.feature_cols = None
        self.openmax_mavs = None
        self.openmax_weibull = None
        self._loaded = False

    def load(self):
        logger.info("Loading model assets...")

        # Load the CNN classifier
        self.model = tf.keras.models.load_model(MODEL_PATH)
        logger.info(f"Model loaded from {MODEL_PATH}")

        # Build a sub-model that outputs logits (pre-softmax)
        # class_output is the final Dense(6) layer — its output before activation
        # But in our model class_output already IS the final layer output (no separate softmax)
        # The model output IS the logits if there's no softmax, or softmax probs if there is
        # Let's check: the final layer is Dense(6) named 'class_output'
        # We need both penultimate features and logits
        logit_layer = self.model.get_layer("class_output")
        penultimate_layer = self.model.get_layer("penultimate")

        self.logit_model = tf.keras.Model(
            inputs=self.model.input,
            outputs={
                "logits": logit_layer.output,
                "penultimate": penultimate_layer.output,
            }
        )
        logger.info("Logit extraction model built")

        # Load scaler
        self.scaler = joblib.load(SCALER_PATH)
        logger.info(f"Scaler loaded from {SCALER_PATH}")

        # Load feature columns
        with open(FEATURE_COLS_PATH, "r") as f:
            self.feature_cols = json.load(f)
        logger.info(f"Feature columns loaded: {len(self.feature_cols)} features")

        # Load OpenMax parameters
        with open(OPENMAX_PARAMS_PATH, "r") as f:
            params = json.load(f)

        self.openmax_mavs = {}
        for k, v in params["mavs"].items():
            self.openmax_mavs[int(k)] = np.array(v, dtype=np.float64)

        self.openmax_weibull = {}
        for k, v in params["weibull_params"].items():
            self.openmax_weibull[int(k)] = tuple(v)

        logger.info("OpenMax parameters loaded")
        self._loaded = True

    @property
    def is_loaded(self):
        return self._loaded

    def _prepare_features(self, df: pd.DataFrame) -> np.ndarray:
        """Select features, scale, zero-pad, reshape to images."""
        # Select the required feature columns
        available = [c for c in self.feature_cols if c in df.columns]
        missing = [c for c in self.feature_cols if c not in df.columns]
        if missing:
            logger.warning(f"Missing {len(missing)} features, filling with 0: {missing[:5]}...")

        features = pd.DataFrame(index=df.index)
        for col in self.feature_cols:
            if col in df.columns:
                features[col] = df[col]
            else:
                features[col] = 0.0

        # Ensure numeric types
        features = features.apply(pd.to_numeric, errors="coerce")

        # Clean infinities and NaN
        features = features.replace([np.inf, -np.inf], np.nan)
        features = features.fillna(0.0)

        # Scale
        X = self.scaler.transform(features.values)

        # Clean any NaN/inf produced by scaling
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

        # Zero-pad to IMAGE_PIXELS (121)
        n_features = X.shape[1]
        if n_features < IMAGE_PIXELS:
            padding = np.zeros((X.shape[0], IMAGE_PIXELS - n_features), dtype=np.float32)
            X = np.concatenate([X, padding], axis=1)

        # Reshape to images
        X = X[:, :IMAGE_PIXELS].reshape(-1, IMAGE_SIZE, IMAGE_SIZE, 1).astype(np.float32)
        return X

    def _prepare_from_json(self, features: list, feature_names: list) -> np.ndarray:
        """Prepare features from preprocessor JSON output (already scaled).

        The preprocessor already cleaned and scaled the features with its own scaler.
        Here we just need to:
        1. Select the 67 features the CNN needs (from the 78 the preprocessor outputs)
        2. Zero-pad to 121
        3. Reshape to 11x11x1
        NO re-scaling — features are already normalized.
        """
        df = pd.DataFrame(features, columns=feature_names)

        # Select only the 67 CNN features, fill missing with 0
        selected = np.zeros((len(features), len(self.feature_cols)), dtype=np.float32)
        for i, col in enumerate(self.feature_cols):
            if col in df.columns:
                selected[:, i] = df[col].values.astype(np.float32)

        # Zero-pad to IMAGE_PIXELS (121)
        n_features = selected.shape[1]
        if n_features < IMAGE_PIXELS:
            padding = np.zeros((selected.shape[0], IMAGE_PIXELS - n_features), dtype=np.float32)
            selected = np.concatenate([selected, padding], axis=1)

        # Reshape to images
        X = selected[:, :IMAGE_PIXELS].reshape(-1, IMAGE_SIZE, IMAGE_SIZE, 1)
        return X

    def _openmax_predict(self, logits: np.ndarray) -> tuple:
        """Run OpenMax on logit vectors. Returns (predictions, probabilities)."""
        N = logits.shape[0]
        num_classes = NUM_KNOWN_CLASSES
        all_probs = np.zeros((N, num_classes + 1), dtype=np.float64)

        # Build MAV and Weibull arrays
        mav_matrix = np.zeros((num_classes, logits.shape[1]), dtype=np.float64)
        wb_shapes = np.zeros(num_classes, dtype=np.float64)
        wb_scales = np.zeros(num_classes, dtype=np.float64)
        wb_valid = np.zeros(num_classes, dtype=bool)

        for cls in range(num_classes):
            if cls in self.openmax_mavs:
                mav_matrix[cls] = self.openmax_mavs[cls]
            if self.openmax_weibull.get(cls) is not None:
                wb_shapes[cls] = self.openmax_weibull[cls][0]
                wb_scales[cls] = self.openmax_weibull[cls][2]
                wb_valid[cls] = True

        avs = logits.astype(np.float64)

        # Rank by logit magnitude
        ranked = np.argsort(avs[:, :num_classes], axis=1)[:, ::-1]

        rank_alpha = np.zeros((N, num_classes), dtype=np.float64)
        for j in range(min(ALPHA_RANK, num_classes)):
            cls_indices = ranked[:, j]
            weight = (ALPHA_RANK + 1 - (j + 1)) / ALPHA_RANK
            rank_alpha[np.arange(N), cls_indices] = weight

        # Cosine distances
        if DISTANCE_TYPE == "cosine":
            dot = avs @ mav_matrix.T
            norms_avs = np.linalg.norm(avs, axis=1, keepdims=True)
            norms_mav = np.linalg.norm(mav_matrix, axis=1, keepdims=True).T
            denom = np.maximum(norms_avs * norms_mav, 1e-10)
            dists = 1.0 - dot / denom
        else:
            dists = np.linalg.norm(avs[:, None, :] - mav_matrix[None, :, :], axis=2)

        # Weibull CDF → omega
        omega = np.ones((N, num_classes), dtype=np.float64)
        for cls in range(num_classes):
            if not wb_valid[cls]:
                continue
            scale = max(wb_scales[cls], 1e-10)
            weibull_cdf = 1.0 - np.exp(-((dists[:, cls] / scale) ** wb_shapes[cls]))
            omega[:, cls] = 1.0 - rank_alpha[:, cls] * weibull_cdf

        # Recalibrate logits
        avs_known = avs[:, :num_classes]
        recalibrated = avs_known * omega
        unknown_activation = np.sum(avs_known * (1.0 - omega), axis=1, keepdims=True)

        # Softmax over [recalibrated known, unknown]
        all_acts = np.concatenate([recalibrated, unknown_activation], axis=1)
        all_acts -= all_acts.max(axis=1, keepdims=True)
        exp_acts = np.exp(all_acts)
        probs = exp_acts / exp_acts.sum(axis=1, keepdims=True)

        predictions = np.argmax(probs, axis=1)
        return predictions, probs

    # CICFlowMeter real output uses abbreviated names.
    # Map to CICIDS2017 dataset names used by our scaler/feature_cols.
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

    def _profile_traffic(self, df: pd.DataFrame) -> dict:
        """Analyze raw flow data to extract traffic characteristics."""
        profile = {}

        # Destination port analysis
        dst_col = None
        for c in ["Destination Port", "Dst Port"]:
            if c in df.columns:
                dst_col = c
                break
        if dst_col:
            ports = pd.to_numeric(df[dst_col], errors="coerce").dropna().astype(int)
            if len(ports) > 0:
                top_ports = ports.value_counts().head(5)
                profile["top_dst_ports"] = {int(k): int(v) for k, v in top_ports.items()}
                profile["unique_dst_ports"] = int(ports.nunique())

        # Protocol analysis
        if "Protocol" in df.columns:
            protos = df["Protocol"].value_counts().head(5)
            proto_map = {6: "TCP", 17: "UDP", 1: "ICMP"}
            profile["protocols"] = {proto_map.get(int(k), str(k)): int(v) for k, v in protos.items()}

        # Source IP diversity
        for c in ["Source IP", "Src IP"]:
            if c in df.columns:
                profile["unique_src_ips"] = int(df[c].nunique())
                break

        # Flow duration stats
        for c in ["Flow Duration"]:
            if c in df.columns:
                durations = pd.to_numeric(df[c], errors="coerce").dropna()
                if len(durations) > 0:
                    profile["avg_flow_duration_us"] = int(durations.mean())

        # Packet size stats
        for c in ["Total Length of Fwd Packets", "TotLen Fwd Pkts"]:
            if c in df.columns:
                fwd = pd.to_numeric(df[c], errors="coerce").dropna()
                if len(fwd) > 0:
                    profile["avg_fwd_bytes"] = round(float(fwd.mean()), 1)
                break

        return profile

    def predict_from_csv(self, csv_bytes: bytes) -> dict:
        """Full inference from raw CSV bytes."""
        df = pd.read_csv(pd.io.common.BytesIO(csv_bytes))
        # Strip whitespace from column names (CICFlowMeter quirk)
        df.columns = df.columns.str.strip()
        # Rename CICFlowMeter abbreviated names to CICIDS2017 names
        df = df.rename(columns=self.COLUMN_RENAME_MAP)

        # Profile traffic before feature extraction
        traffic_profile = self._profile_traffic(df)

        if len(df) == 0:
            return {
                "flow_count": 0,
                "model_findings": {
                    "status": "normal",
                    "attack_detected": False,
                    "attack_type": None,
                    "confidence": 0.0,
                    "attack_ratio": 0.0,
                    "flow_count": 0,
                    "class_distribution": {},
                },
                "predictions": {
                    "summary": {"status": "normal", "attack_detected": False,
                                "dominant_class": "Normal", "confidence": 0.0, "attack_ratio": 0.0},
                    "class_distribution": {},
                    "per_flow": [],
                },
            }

        images = self._prepare_features(df)
        result = self._run_inference(images, len(df))
        result["model_findings"]["traffic_profile"] = traffic_profile
        return result

    def predict_from_features(self, features: list, feature_names: list) -> dict:
        """Inference from preprocessor output (already-extracted features)."""
        images = self._prepare_from_json(features, feature_names)
        return self._run_inference(images, len(features))

    def _run_inference(self, images: np.ndarray, flow_count: int) -> dict:
        """Run model + OpenMax on prepared image tensors."""
        # Forward pass
        outputs = self.logit_model.predict(images, verbose=0)
        logits = np.nan_to_num(outputs["logits"], nan=0.0, posinf=0.0, neginf=0.0)

        # OpenMax
        predictions, probabilities = self._openmax_predict(logits)
        probabilities = np.nan_to_num(probabilities, nan=0.0, posinf=0.0, neginf=0.0)

        # Build per-flow results
        per_flow = []
        class_counts = {}
        confidence_sum = 0.0

        for i in range(len(predictions)):
            pred_class = int(predictions[i])
            class_name = CLASS_NAMES.get(pred_class, "Unknown")
            confidence = float(probabilities[i, pred_class])

            per_flow.append({
                "flow_id": i,
                "prediction": class_name,
                "class_id": pred_class,
                "confidence": round(confidence, 4),
            })

            class_counts[class_name] = class_counts.get(class_name, 0) + 1
            confidence_sum += confidence

        # Determine dominant class
        dominant_class = max(class_counts, key=class_counts.get)
        avg_confidence = confidence_sum / max(len(predictions), 1)

        # Compute attack ratio (% of flows that are attacks)
        total_flows = len(predictions)
        attack_flows = total_flows - class_counts.get("Normal", 0)
        attack_ratio = attack_flows / max(total_flows, 1)

        # Detect attacks: if >20% of flows are classified as attacks, flag it
        # (the model has ~15% false positive rate on normal traffic)
        attack_detected = attack_ratio > 0.20

        # Find the top attack class (excluding Normal)
        attack_classes = {k: v for k, v in class_counts.items() if k != "Normal"}
        if attack_detected and attack_classes:
            top_attack = max(attack_classes, key=attack_classes.get)
        else:
            top_attack = None

        status = "abnormal" if attack_detected else "normal"

        return {
            "flow_count": flow_count,
            "model_findings": {
                "status": status,
                "attack_detected": attack_detected,
                "attack_type": top_attack,
                "confidence": round(avg_confidence, 4),
                "attack_ratio": round(attack_ratio, 4),
                "flow_count": flow_count,
                "class_distribution": class_counts,
            },
            "predictions": {
                "summary": {
                    "status": status,
                    "attack_detected": attack_detected,
                    "dominant_class": dominant_class,
                    "confidence": round(avg_confidence, 4),
                    "attack_ratio": round(attack_ratio, 4),
                },
                "class_distribution": class_counts,
                "per_flow": per_flow[:200],  # Cap at 200 for API response size
            },
        }


# Singleton
_service = InferenceService()


def get_inference_service() -> InferenceService:
    if not _service.is_loaded:
        _service.load()
    return _service

# Added nan_to_num after scaling and after inference

# # Adjusted threshold: attack_ratio > 0.20
