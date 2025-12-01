"""FastAPI entrypoint for the SciPaper Analyzer service."""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

import requests
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from agents.adk_agent import PaperRAGAgent
import config
from ingestion.pipeline import ingest_pdf, _summarize
from models.api import (
    AnalyzeUrlsRequest,
    AnalyzeUrlsResponse,
    QueryRequest,
    QueryResponse,
    SummaryResponse,
    UploadResponse,
    UserRequest,
)
from services import gcs, storage

app = FastAPI(
    title="SciPaper Analyzer API",
    description=(
        "Ingest PDFs, index them in Vertex AI Vector Search, and answer questions via Gemini."
    ),
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = PaperRAGAgent()


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


def _get_similar_papers(url: str) -> list[dict[str, Any]]:
    """Call the paperrec-search service to find similar papers."""
    if not config.PAPERREC_SEARCH_URL:
        logging.warning("PAPERREC_SEARCH_URL is not set. Skipping similarity search.")
        return []
    try:
        # Ensure the URL ends with /search
        search_url = config.PAPERREC_SEARCH_URL.rstrip('/') + "/search"
        response = requests.post(search_url, json={"url": url, "k": 5})
        response.raise_for_status()
        return response.json().get("neighbors", [])
    except requests.RequestException as e:
        logging.error(f"Could not call paperrec-search service for url {url}: {e}")
        return []


def _download_pdf(url: str) -> bytes | None:
    """Download PDF content from a URL."""
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        logging.error(f"Failed to download PDF from {url}: {e}")
        return None


@app.post("/analyze_urls", response_model=AnalyzeUrlsResponse, tags=["ingestion"])
async def analyze_urls(request: AnalyzeUrlsRequest) -> AnalyzeUrlsResponse:
    """Orchestrates the analysis of multiple arXiv URLs."""
    initial_urls = request.urls
    if not initial_urls:
        raise HTTPException(status_code=400, detail="No URLs provided.")

    # --- 1. Corpus Expansion ---
    papers_to_process: dict[str, dict] = {}
    initial_paper_canonical_ids: list[str] = []

    # Add initial papers and find similar ones
    for url in initial_urls:
        # The paperrec-search service returns metadata for the query paper itself as the first result
        similar_papers = await run_in_threadpool(_get_similar_papers, url)

        # Capture the canonical ID of the initial paper from the search result
        if similar_papers:
            initial_paper_id = similar_papers[0].get("id")
            if initial_paper_id:
                initial_paper_canonical_ids.append(initial_paper_id)

        for paper in similar_papers:
            # Use arxiv_id (e.g., '2401.08406v1') as the unique key
            arxiv_id = paper.get("id")
            if arxiv_id and arxiv_id not in papers_to_process:
                papers_to_process[arxiv_id] = paper.get("metadata", {})
                papers_to_process[arxiv_id]["id"] = arxiv_id  # Ensure ID is in metadata

    # --- 2. Full-Text Ingestion ---
    ingestion_tasks = []
    for arxiv_id, paper_meta in papers_to_process.items():
        pdf_url = paper_meta.get("link_pdf")
        if not pdf_url:
            logging.warning(f"No PDF link found for paper {arxiv_id}. Skipping.")
            continue

        pdf_bytes = await run_in_threadpool(_download_pdf, pdf_url)
        if pdf_bytes:
            # Ingest the paper using its arXiv ID as the document ID
            task = run_in_threadpool(ingest_pdf, pdf_bytes, arxiv_id)
            ingestion_tasks.append(task)

    # Run all ingestion tasks concurrently
    await asyncio.gather(*ingestion_tasks)

    # --- 3. Individual Summarization ---
    summaries: dict[str, str] = {}
    unique_initial_ids = sorted(list(set(initial_paper_canonical_ids)))

    for paper_id in unique_initial_ids:
        summary_text = f"Could not generate a summary for paper {paper_id}."
        chunks = await run_in_threadpool(
            storage.fetch_chunks_for_papers, [paper_id]
        )

        if chunks:
            summary_text = await run_in_threadpool(_summarize, chunks)
        elif paper_id in papers_to_process:
            # Fallback to abstract if chunks are not found
            abstract = papers_to_process[paper_id].get("abstract", "")
            if abstract:
                summary_text = await run_in_threadpool(_summarize, [abstract])
        
        summaries[paper_id] = summary_text

    return AnalyzeUrlsResponse(
        session_paper_ids=list(papers_to_process.keys()),
        summaries=summaries,
    )


@app.post("/upload", response_model=UploadResponse, tags=["ingestion"])
async def upload_pdf(file: UploadFile = File(...)) -> UploadResponse:
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported.")

    contents = await file.read()
    paper_id = str(uuid.uuid4())
    gcs_uri = None
    if config.GCS_BUCKET:
        gcs_uri = await run_in_threadpool(
            gcs.upload_pdf, contents, f"{paper_id}.pdf", config.GCS_BUCKET
        )

    paper_id, summary = await run_in_threadpool(ingest_pdf, contents, paper_id)
    return UploadResponse(paper_id=paper_id, summary=summary, gcs_uri=gcs_uri)



@app.post("/query", response_model=QueryResponse, tags=["query"])
async def query(request: QueryRequest) -> QueryResponse:
    if not request.question:
        raise HTTPException(status_code=400, detail="Question is required")
    if not request.paper_ids:
        raise HTTPException(status_code=400, detail="At least one paper_id is required")
    response = await run_in_threadpool(
        agent.answer_question,
        paper_ids=request.paper_ids,
        session_id=request.session_id,
        question=request.question,
        top_k=request.top_k or config.DEFAULT_TOP_K,
    )
    return QueryResponse(response=response)


@app.get("/summary/{paper_id}", response_model=SummaryResponse, tags=["summary"])
async def get_summary(paper_id: str) -> SummaryResponse:
    summary = await run_in_threadpool(storage.fetch_summary, paper_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Summary not found")
    return SummaryResponse(paper_id=paper_id, summary=summary)


# --- NEW: User Management Endpoints ---

@app.post("/users", tags=["admin"])
async def create_user(request: UserRequest):
    success = await run_in_threadpool(storage.create_user, request.username, request.role)
    if not success:
        raise HTTPException(status_code=400, detail="User already exists or invalid data.")
    return {"status": "created", "username": request.username}


@app.get("/users", tags=["admin"])
async def list_users():
    users = await run_in_threadpool(storage.list_users)
    return {"users": users, "count": len(users)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)