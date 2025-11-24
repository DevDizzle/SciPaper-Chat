"""Google Cloud Storage helpers."""
from __future__ import annotations

import pathlib
import tempfile
from typing import Optional

from google.cloud import storage

import config

_storage_client: storage.Client | None = None


def get_client() -> storage.Client:
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=config.PROJECT_ID)
    return _storage_client


def upload_pdf(bytes_data: bytes, filename: str, bucket_name: Optional[str] = None) -> str:
    bucket_name = bucket_name or config.GCS_BUCKET
    if not bucket_name:
        raise config.SettingsError("GCS_BUCKET must be configured to upload PDFs.")
    bucket = get_client().bucket(bucket_name)
    blob = bucket.blob(filename)
    blob.upload_from_string(bytes_data, content_type="application/pdf")
    return f"gs://{bucket_name}/{blob.name}"


def download_to_temp(gs_uri: str) -> pathlib.Path:
    if not gs_uri.startswith("gs://"):
        raise ValueError("Only gs:// URIs are supported for downloads")
    _, path = gs_uri.split("gs://", 1)
    bucket_name, blob_name = path.split("/", 1)
    bucket = get_client().bucket(bucket_name)
    blob = bucket.blob(blob_name)
    temp_path = pathlib.Path(tempfile.mkstemp(suffix=".pdf")[1])
    blob.download_to_filename(str(temp_path))
    return temp_path
