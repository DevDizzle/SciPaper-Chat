"""Firestore-backed persistence utilities."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from google.cloud import firestore

import config

_db: firestore.Client | None = None
USERS_COLLECTION = "users"


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
    """Persist chunk text in Firestore keyed by vector ID."""
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


def fetch_chunks_for_papers(paper_ids: List[str]) -> List[str]:
    """Fetches all chunk texts for a list of paper IDs."""
    if not paper_ids:
        return []

    client = get_client()
    collection = client.collection(config.CHUNKS_COLLECTION)
    
    # Firestore 'in' query supports up to 30 values.
    # If more are needed, chunk the requests.
    text_chunks = []
    for i in range(0, len(paper_ids), 30):
        chunk_of_ids = paper_ids[i:i+30]
        query = collection.where(filter=firestore.FieldFilter("paper_id", "in", chunk_of_ids))
        documents = query.stream()
        for doc in documents:
            data = doc.to_dict()
            if data and "text" in data:
                text_chunks.append(data["text"])
    
    return text_chunks


# --- NEW: User Management for Demo ---

def create_user(username: str, role: str) -> bool:
    """Registers a new user for the demo."""
    if not username:
        return False
    
    # Check if user exists using the username as the document ID
    doc_ref = get_client().collection(USERS_COLLECTION).document(username)
    if doc_ref.get().exists:
        return False 
        
    doc_ref.set({
        "username": username,
        "role": role,
        "joined_at": datetime.utcnow()
    })
    return True


def list_users() -> List[Dict]:
    """Fetches all users for the Admin dashboard."""
    users_ref = get_client().collection(USERS_COLLECTION).stream()
    users = []
    for doc in users_ref:
        users.append(doc.to_dict())
    return users