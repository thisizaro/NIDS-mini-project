import io
import logging
import zipfile
import httpx
from app.config import (
    CICFLOWMETER_URL, PREPROCESSOR_URL, MODEL_SERVICE_URL,
    DECISION_ENGINE_URL, REQUEST_TIMEOUT,
)

logger = logging.getLogger(__name__)


async def run_full_pipeline(pcap_bytes: bytes, pcap_filename: str, context: dict) -> dict:
    """
    Run the complete IDS pipeline:
    PCAP → CICFlowMeter → Preprocessor (info) + Model (predict-csv) → Decision Engine

    The preprocessor and model service use DIFFERENT scalers:
    - Preprocessor: 78-feature scaler (models/scaler.pkl)
    - Model: 67-feature scaler (scaler_infogan_kaggle.pkl)
    So the model gets the raw CSV and does its own feature selection + scaling.
    """
    steps = {}

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:

        # Step 1: CICFlowMeter — PCAP to CSV
        logger.info("Step 1: CICFlowMeter processing...")
        resp = await client.post(
            f"{CICFLOWMETER_URL}/process",
            files={"file": (pcap_filename, pcap_bytes, "application/octet-stream")},
        )
        resp.raise_for_status()
        zip_bytes = resp.content

        # Extract first CSV from ZIP
        csv_bytes = None
        csv_filename = None
        csv_names = []
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            csv_names = [n for n in zf.namelist() if n.endswith(".csv")]
            if not csv_names:
                raise ValueError("No CSV files found in CICFlowMeter output")
            csv_filename = csv_names[0]
            csv_bytes = zf.read(csv_filename)

        steps["cicflowmeter"] = {
            "status": "complete",
            "csv_files": csv_names,
            "csv_filename": csv_filename,
            "csv_size_bytes": len(csv_bytes),
        }
        logger.info(f"Step 1 complete: {csv_filename} ({len(csv_bytes)} bytes)")

        # Step 2: Preprocessor — CSV to feature stats (for display purposes)
        logger.info("Step 2: Preprocessing...")
        resp = await client.post(
            f"{PREPROCESSOR_URL}/api/v1/preprocess",
            files={"file": (csv_filename, csv_bytes, "text/csv")},
        )
        resp.raise_for_status()
        preprocess_result = resp.json()

        steps["preprocessor"] = {
            "status": "complete",
            "row_count": preprocess_result.get("row_count"),
            "feature_count": preprocess_result.get("feature_count"),
        }
        logger.info(f"Step 2 complete: {preprocess_result.get('row_count')} rows")

        # Step 3: Model Inference — send raw CSV directly (model has its own scaler)
        logger.info("Step 3: Model inference...")
        resp = await client.post(
            f"{MODEL_SERVICE_URL}/api/v1/predict-csv",
            files={"file": (csv_filename, csv_bytes, "text/csv")},
        )
        resp.raise_for_status()
        model_result = resp.json()

        steps["model"] = {
            "status": "complete",
            "flow_count": model_result.get("flow_count"),
            "summary": model_result.get("predictions", {}).get("summary"),
            "class_distribution": model_result.get("predictions", {}).get("class_distribution"),
        }
        logger.info(f"Step 3 complete: {model_result.get('predictions', {}).get('summary')}")

        # Step 4: Decision Engine — findings to verdict
        logger.info("Step 4: Decision engine...")
        model_findings = model_result.get("model_findings", {})
        resp = await client.post(
            f"{DECISION_ENGINE_URL}/api/v1/verdict",
            json={
                "modelFindings": model_findings,
                "context": context,
            },
        )
        resp.raise_for_status()
        verdict_result = resp.json()

        steps["verdict"] = {
            "status": "complete",
            **verdict_result,
        }
        logger.info(f"Step 4 complete: {verdict_result.get('verdict')}")

    return {
        "steps": steps,
        "model_findings": model_findings,
        "verdict": verdict_result,
        "predictions": model_result.get("predictions"),
    }

# Added per-step error handling and tracking
