# main.py

import os
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

from config import PCAP_DIR, FLOW_DIR
from services.processor import (
    run_processing_command,
    ProcessingAlreadyRunning,
)
from utils.file_ops import save_upload_file_streamed, zip_flow_csvs, clean_csv_files

app = FastAPI(title="PCAP Processing API")


@app.post("/process")
def process_pcap(file: UploadFile = File(...)):
    """
    Accepts a single PCAP file, processes it, and returns CSVs as a ZIP.
    """

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    pcap_path = os.path.join(PCAP_DIR, file.filename)

    try:
        # Minimal cleanup: remove old CSVs
        clean_csv_files(FLOW_DIR)

        # 1. Save uploaded PCAP (streaming)
        print(f"Saving uploaded file to: {pcap_path}")
        save_upload_file_streamed(file, pcap_path)
        print("File saved successfully.")

        # 2. Run processing pipeline (blocking)
        run_processing_command()

        # 3. Zip CSV results
        tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        tmp_zip.close()

        zip_flow_csvs(FLOW_DIR, tmp_zip.name)
        # Minimal cleanup: remove uploaded PCAP
        if os.path.exists(pcap_path):
            os.remove(pcap_path)

        # 4. Return ZIP
        return FileResponse(
            tmp_zip.name,
            media_type="application/zip",
            filename="flow_results.zip",
        )

    except ProcessingAlreadyRunning:
        raise HTTPException(
            status_code=429,
            detail="Another processing job is already running",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
