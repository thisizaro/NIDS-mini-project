# utils/file_ops.py

import os
import zipfile
from fastapi import UploadFile

CHUNK_SIZE = 1024 * 1024  # 1 MB


def save_upload_file_streamed(upload_file: UploadFile, destination_path: str):
    """
    Saves uploaded file to disk in chunks.
    Safe for large files (500MB+).
    """
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)

    with open(destination_path, "wb") as out_file:
        while True:
            chunk = upload_file.file.read(CHUNK_SIZE)
            if not chunk:
                break
            out_file.write(chunk)


def zip_flow_csvs(flow_dir: str, zip_path: str):
    """
    Zips all CSV files from flow directory.
    ASSUMED FOR NOW: all CSVs belong to one run.
    """
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for filename in os.listdir(flow_dir):
            if filename.endswith(".csv"):
                full_path = os.path.join(flow_dir, filename)
                zipf.write(full_path, arcname=filename)


def clean_csv_files(dir_path: str):
    """
    Removes all CSV files from a directory.
    Minimal cleanup for single-job execution.
    """
    if not os.path.exists(dir_path):
        return

    for filename in os.listdir(dir_path):
        if filename.endswith(".csv"):
            os.remove(os.path.join(dir_path, filename))