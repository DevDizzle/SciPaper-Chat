"""PDF ingestion pipeline using Vertex AI embeddings and Vector Search."""
from __future__ import annotations

import io
import uuid
from typing import List, Optional, Tuple

from pypdf import PdfReader
import vertexai
from vertexai.generative_models import GenerativeModel, Part

import config
from services import embedding, storage, vector_search

vertexai.init(project=config.PROJECT_ID, location=config.REGION)


def _extract_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = []
    for page in reader.pages:
        text.append(page.extract_text() or "")
    return "\n".join(text)


def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return [c.strip() for c in chunks if c.strip()]


def _summarize(chunks: List[str]) -> str:
    if not chunks:
        return ""
    model = GenerativeModel(config.GENERATION_MODEL)
    prompt = (
        "You are summarizing a scientific paper for researchers. "
        "Provide a concise summary that captures main contributions and methods."
    )
    parts = [Part.from_text(prompt)] + [Part.from_text(chunk[:2000]) for chunk in chunks[:5]]
    response = model.generate_content(parts)
    return response.text if hasattr(response, "text") else str(response)


def ingest_pdf(pdf_bytes: bytes, paper_id: Optional[str] = None) -> Tuple[str, str]:
    paper_identifier = paper_id or str(uuid.uuid4())
    text = _extract_text(pdf_bytes)
    chunks = _chunk_text(text)
    embeddings = embedding.embed_texts(chunks)

    storage.persist_chunks(paper_identifier, chunks)
    vector_search.upsert_embeddings(
        paper_identifier,
        embeddings,
    )

    summary = _summarize(chunks)
    storage.persist_summary(paper_identifier, summary)
    return paper_identifier, summary
