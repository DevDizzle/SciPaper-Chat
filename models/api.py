"""Pydantic models for FastAPI requests and responses."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    paper_id: str = Field(..., description="Identifier for the ingested paper")
    summary: str = Field(..., description="Initial summary generated from the paper")
    gcs_uri: str | None = Field(
        default=None,
        description="Location of the uploaded PDF in Cloud Storage (if configured)",
    )


class QueryRequest(BaseModel):
    paper_ids: list[str] = Field(..., description="List of identifiers for papers to search across")
    session_id: Optional[str] = Field(
        default=None, description="Session identifier for chat continuity"
    )
    question: str = Field(..., description="User question about the paper")
    top_k: int = Field(default=5, description="Number of chunks to retrieve")


class QueryResponse(BaseModel):
    response: str


class SummaryResponse(BaseModel):
    paper_id: str
    summary: str


class UserRequest(BaseModel):
    username: str
    role: str = "student"


class AnalyzeUrlsRequest(BaseModel):
    urls: list[str] = Field(..., description="List of arXiv URLs to analyze and use as seeds")


class AnalyzeUrlsResponse(BaseModel):
    session_paper_ids: list[str] = Field(
        ..., description="List of all paper IDs (arXiv IDs) ingested for this session"
    )
    summaries: dict[str, str] = Field(
        ..., description="A dictionary mapping initial paper IDs to their summaries"
    )