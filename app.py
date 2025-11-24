"""FastAPI entrypoint for the Scientific Paper Analyzer backend service."""

import os
import tempfile
import uuid
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from chain import answer_question, process_document

app = FastAPI(
    title="Scientific Paper Analyzer API",
    description=(
        "REST API for ingesting scientific papers, generating summaries, and "
        "answering grounded questions via Vertex AI and Firestore-backed persistence."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str


class AnalyzeResponse(BaseModel):
    status: str
    summary: str
    session_id: str


def get_session_id() -> str:
    return str(uuid.uuid4())


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/session", tags=["session"])
def create_session() -> dict[str, str]:
    return {"session_id": get_session_id()}


@app.post("/analyze", response_model=AnalyzeResponse, tags=["analysis"])
async def analyze(
    file: UploadFile | None = File(default=None, description="PDF upload"),
    arxiv_id: Optional[str] = Form(default=None, description="ArXiv identifier"),
) -> AnalyzeResponse:
    if not file and not arxiv_id:
        raise HTTPException(status_code=400, detail="Provide a PDF upload or an ArXiv ID.")

    temp_path = None
    try:
        if file:
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                contents = await file.read()
                temp_file.write(contents)
                temp_path = temp_file.name

        status, summary = await run_in_threadpool(process_document, temp_path, arxiv_id)
        session_id = get_session_id()
        return AnalyzeResponse(status=status, summary=summary, session_id=session_id)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@app.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat(request: ChatRequest) -> ChatResponse:
    if not request.message:
        raise HTTPException(status_code=400, detail="Message is required.")

    response = await run_in_threadpool(answer_question, request.message, [], request.session_id)
    return ChatResponse(response=response)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
