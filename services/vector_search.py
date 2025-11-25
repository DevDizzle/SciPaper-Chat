"""Vertex AI Vector Search integration."""
from __future__ import annotations

from typing import List, Optional

from google.cloud import aiplatform
from google.cloud import aiplatform

import config


def _get_endpoint() -> aiplatform.MatchingEngineIndexEndpoint:
    aiplatform.init(project=config.PROJECT_ID, location=config.REGION)
    if not config.VERTEX_INDEX_ENDPOINT_ID:
        raise config.SettingsError("VERTEX_INDEX_ENDPOINT_ID must be set for vector search.")
    return aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=config.VERTEX_INDEX_ENDPOINT_ID)


def upsert_embeddings(
    paper_id: str,
    embeddings: List[list[float]],
    *,
    deployed_index_id: Optional[str] = None,
    start_index: int = 0,
) -> None:
    endpoint = _get_endpoint()
    deployed = deployed_index_id or config.VERTEX_DEPLOYED_INDEX_ID
    if not deployed:
        raise config.SettingsError("VERTEX_DEPLOYED_INDEX_ID must be set for upserts.")

    datapoints = []
    for i, vector in enumerate(embeddings):
        datapoints.append(
            aiplatform.MatchingEngineIndexDatapoint(
                id=f"{paper_id}-{start_index + i}",
                embedding=vector,
                restricts=[{"namespace": "paper_id", "allow_tokens": [paper_id]}],
            )
        )
    endpoint.upsert_datapoints(datapoints=datapoints, deployed_index_id=deployed)


def query(
    *,
    query_vector: list[float],
    paper_id: Optional[str],
    top_k: int,
    deployed_index_id: Optional[str] = None,
) -> List[dict]:
    endpoint = _get_endpoint()
    deployed = deployed_index_id or config.VERTEX_DEPLOYED_INDEX_ID
    if not deployed:
        raise config.SettingsError("VERTEX_DEPLOYED_INDEX_ID must be set for queries.")

    categorical_filters = []
    if paper_id:
        categorical_filters.append(aiplatform.matching_engine.matching_engine_index_endpoint.Namespace(name="paper_id", allow_tokens=[paper_id]))

    neighbors = endpoint.find_neighbors(
        deployed_index_id=deployed,
        queries=[query_vector],
        num_neighbors=top_k,
        return_full_datapoint=True,
    )
    results = []
    for neighbor in neighbors[0].neighbors:
        datapoint = neighbor.datapoint
        metadata = datapoint.restricts or []
        attributes = getattr(datapoint, "attributes", {}) or {}
        results.append(
            {
                "score": neighbor.distance,
                "metadata": attributes,
                "namespace_filters": metadata,
            }
        )
    return results
