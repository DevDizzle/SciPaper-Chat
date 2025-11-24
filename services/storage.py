"""Firestore-backed persistence utilities."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from google.cloud import firestore

import config

_db: firestore.Client | None = None


def get_client() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.Client(project=config.PROJECT_ID)
    return _db


def save_chat_history(session_id: str, role: str, content: str) -> None:
    if not session_id:
        return
    doc_ref = (
        get_client()
        .collection(config.SESSIONS_COLLECTION)
        .document(session_id)
        .collection("messages")
    )
    doc_ref.add({"role": role, "content": content, "timestamp": datetime.utcnow()})


def load_chat_history(session_id: Optional[str], limit: int = 10) -> List[str]:
    if not session_id:
        return []
    messages = (
        get_client()
        .collection(config.SESSIONS_COLLECTION)
        .document(session_id)
        .collection("messages")
        .order_by("timestamp")
        .limit(limit)
        .stream()
    )
    return [f"{m.to_dict()['role'].upper()}: {m.to_dict()['content']}" for m in messages]


def persist_summary(paper_id: str, summary: str) -> None:
    if not paper_id:
        return
    summaries = get_client().collection(config.SUMMARIES_COLLECTION)
    summaries.document(paper_id).set(
        {"summary": summary, "updated_at": datetime.utcnow()}, merge=True
    )


def fetch_summary(paper_id: str) -> Optional[str]:
    if not paper_id:
        return None
    doc = get_client().collection(config.SUMMARIES_COLLECTION).document(paper_id).get()
    if not doc.exists:
        return None
    return doc.to_dict().get("summary")
