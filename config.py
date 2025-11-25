"""Central configuration for SciPaper Analyzer service."""
import os
from typing import Optional

PROJECT_ID: Optional[str] = os.getenv("PROJECT_ID")
REGION: str = os.getenv("REGION", "us-central1")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
GENERATION_MODEL: str = os.getenv("GENERATION_MODEL", "gemini-2.0-flash-001")
GCS_BUCKET: Optional[str] = os.getenv("GCS_BUCKET")
VERTEX_INDEX_ID: Optional[str] = os.getenv("VERTEX_INDEX_ID")
VERTEX_INDEX_ENDPOINT_ID: Optional[str] = os.getenv("VERTEX_INDEX_ENDPOINT_ID")
VERTEX_DEPLOYED_INDEX_ID: Optional[str] = os.getenv("VERTEX_DEPLOYED_INDEX_ID")
DEFAULT_TOP_K: int = int(os.getenv("DEFAULT_TOP_K", "5"))

# Firestore collection names
SESSIONS_COLLECTION = os.getenv("SESSIONS_COLLECTION", "sessions")
SUMMARIES_COLLECTION = os.getenv("SUMMARIES_COLLECTION", "summaries")
CHUNKS_COLLECTION = os.getenv("CHUNKS_COLLECTION", "paper_chunks")


class SettingsError(Exception):
    """Raised when critical configuration is missing."""


