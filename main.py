"""FastAPI entrypoint for the SciPaper Analyzer service."""
from __future__ import annotations

import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from agents.adk_agent import PaperRAGAgent
import config
from ingestion.pipeline import ingest_pdf
from models.api import QueryRequest, QueryResponse, SummaryResponse, UploadResponse
from services import gcs, storage

app = FastAPI(
    title="SciPaper Analyzer API",
    description=(
        "Ingest PDFs, index them in Vertex AI Vector Search, and answer questions via Gemini."
    ),
    version="2.0.0",
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

    paper_id, summary = await run_in_threadpool(
        ingest_pdf, contents, paper_id
    )
    return UploadResponse(paper_id=paper_id, summary=summary, gcs_uri=gcs_uri)


@app.post("/query", response_model=QueryResponse, tags=["query"])
async def query(request: QueryRequest) -> QueryResponse:
    if not request.question:
        raise HTTPException(status_code=400, detail="Question is required")
    response = await run_in_threadpool(
        agent.answer_question,
        paper_id=request.paper_id,
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
