"""Vertex AI Vector Search integration."""
from __future__ import annotations

from typing import List, Optional

from google.cloud import aiplatform
from google.cloud.aiplatform.matching_engine import matching_engine_index_endpoint as me_endpoint

import config


def _get_endpoint() -> me_endpoint.MatchingEngineIndexEndpoint:
    aiplatform.init(project=config.PROJECT_ID, location=config.REGION)
    if not config.VERTEX_INDEX_ENDPOINT_ID:
        raise config.SettingsError("VERTEX_INDEX_ENDPOINT_ID must be set for vector search.")
    return aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=config.VERTEX_INDEX_ENDPOINT_ID)


def upsert_embeddings(
    paper_id: str,
    embeddings: List[list[float]],
    metadatas: List[dict],
    *,
    deployed_index_id: Optional[str] = None,
) -> None:
    endpoint = _get_endpoint()
    deployed = deployed_index_id or config.VERTEX_DEPLOYED_INDEX_ID
    if not deployed:
        raise config.SettingsError("VERTEX_DEPLOYED_INDEX_ID must be set for upserts.")

    datapoints = []
    for i, (vector, metadata) in enumerate(zip(embeddings, metadatas)):
        datapoints.append(
            aiplatform.MatchingEngineIndexDatapoint(
                id=f"{paper_id}-{i}",
                embedding=vector,
                restricts=[{"namespace": "paper_id", "allow_tokens": [paper_id]}],
                attributes=metadata,
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

    filters = []
    if paper_id:
        filters.append({"namespace": "paper_id", "allow_tokens": [paper_id]})

    neighbors = endpoint.find_neighbors(
        deployed_index_id=deployed,
        queries=[
            aiplatform.matching_engine.matching_engine_index_endpoint.Query(
                embedding=query_vector, restricts=filters
            )
        ],
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
