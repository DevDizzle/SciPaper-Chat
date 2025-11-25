"""Firestore-backed persistence utilities."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

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


def persist_chunks(paper_id: str, chunks: List[str]) -> None:
    """Persist chunk text in Firestore keyed by vector ID.

    Uses a dedicated collection where each document ID matches the vector search
    datapoint ID (`{paper_id}-{chunk_index}`) so retrieval can map directly from
    Vector Search results.
    """

    if not paper_id or not chunks:
        return

    client = get_client()
    collection = client.collection(config.CHUNKS_COLLECTION)
    batch = client.batch()

    for idx, text in enumerate(chunks):
        doc_id = f"{paper_id}-{idx}"
        doc_ref = collection.document(doc_id)
        batch.set(
            doc_ref,
            {
                "paper_id": paper_id,
                "chunk_index": idx,
                "text": text,
                "updated_at": datetime.utcnow(),
            },
        )

    batch.commit()


def fetch_chunks(chunk_ids: List[str]) -> Dict[str, Dict]:
    if not chunk_ids:
        return {}

    client = get_client()
    collection = client.collection(config.CHUNKS_COLLECTION)
    doc_refs = [collection.document(cid) for cid in chunk_ids]
    documents = client.get_all(doc_refs)

    found: Dict[str, Dict] = {}
    for doc in documents:
        if doc.exists:
            found[doc.id] = doc.to_dict() or {}
    return found
