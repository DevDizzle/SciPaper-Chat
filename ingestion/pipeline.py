"""PDF ingestion pipeline using Vertex AI embeddings and Vector Search."""
from __future__ import annotations

import io
import re
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
    full_text = "\n".join(text)

    # Strategy 1: Explicit Headers
    # Look for standalone headers in the last 40% of the document
    headers = [
        r'\n\s*(?:References|Bibliography|Works Cited|Literature Cited|REFERENCES|BIBLIOGRAPHY)\s*(?:\n|$)',
        r'\n\s*\d{1,2}\.?\s*(?:References|Bibliography)\s*(?:\n|$)',
    ]
    
    for pattern in headers:
        matches = list(re.finditer(pattern, full_text, re.IGNORECASE))
        if matches:
            # Pick the last occurrence to avoid Table of Contents matches
            last_match = matches[-1]
            if last_match.start() > len(full_text) * 0.6:
                print(f" [INFO] Detected references header at position {last_match.start()}. Truncating.")
                return full_text[:last_match.start()]

    # Strategy 2: Fallback - Detect start of citation list
    # Look for "[1]" or "1. AuthorName" in the last 30% of the text
    # This catches cases where the "References" header is merged with other text
    start_check = int(len(full_text) * 0.7)
    tail_text = full_text[start_check:]
    
    # Pattern: Newline, optional space, [1], space
    citation_match = re.search(r'\n\s*\[1\]\s+', tail_text)
    if citation_match:
        real_cutoff = start_check + citation_match.start()
        print(f" [INFO] Detected start of citation list ([1]) at {real_cutoff}. Truncating.")
        return full_text[:real_cutoff]

    print(" [WARN] No References section detected. Indexing full text.")
    return full_text


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
    
    batch_size = 20
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i+batch_size]
        embeddings = embedding.embed_texts(batch_chunks)
        vector_search.upsert_embeddings(
            paper_identifier,
            embeddings,
            start_index=i,
        )

    storage.persist_chunks(paper_identifier, chunks)

    summary = _summarize(chunks)
    storage.persist_summary(paper_identifier, summary)
    return paper_identifier, summary