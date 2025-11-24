"""Vertex AI embedding utilities."""
from __future__ import annotations

from typing import List

import vertexai
from vertexai.language_models import TextEmbeddingModel

import config


def get_model() -> TextEmbeddingModel:
    vertexai.init(project=config.PROJECT_ID, location=config.REGION)
    return TextEmbeddingModel.from_pretrained(config.EMBEDDING_MODEL)


def embed_texts(chunks: List[str]) -> List[list[float]]:
    model = get_model()
    responses = model.get_embeddings(chunks)
    return [embedding.values for embedding in responses]
