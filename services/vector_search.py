"""Vertex AI Vector Search integration."""
from __future__ import annotations

from typing import List, Optional

from google.cloud import aiplatform
# Use v1 types for the Datapoint definition
from google.cloud.aiplatform_v1.types import IndexDatapoint

import config


def _get_endpoint() -> aiplatform.MatchingEngineIndexEndpoint:
    aiplatform.init(project=config.PROJECT_ID, location=config.REGION)
    if not config.VERTEX_INDEX_ENDPOINT_ID:
        raise config.SettingsError("VERTEX_INDEX_ENDPOINT_ID must be set for vector search.")
    return aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=config.VERTEX_INDEX_ENDPOINT_ID)


def _get_index() -> aiplatform.MatchingEngineIndex:
    """Retrieve the Vector Search Index resource (for upserts)."""
    aiplatform.init(project=config.PROJECT_ID, location=config.REGION)
    if not config.VERTEX_INDEX_ID:
        raise config.SettingsError("VERTEX_INDEX_ID must be set for upserts.")
    return aiplatform.MatchingEngineIndex(index_name=config.VERTEX_INDEX_ID)


def upsert_embeddings(
    paper_id: str,
    embeddings: List[list[float]],
    *,
    deployed_index_id: Optional[str] = None,
    start_index: int = 0,
) -> None:
    # Upserts must be done on the Index resource, not the Endpoint
    index = _get_index()

    datapoints = []
    for i, vector in enumerate(embeddings):
        # Construct the v1 IndexDatapoint
        datapoints.append(
            IndexDatapoint(
                datapoint_id=f"{paper_id}-{start_index + i}",
                feature_vector=vector,
                restricts=[
                    IndexDatapoint.Restriction(
                        namespace="paper_id", 
                        allow_list=[paper_id]
                    )
                ],
            )
        )
    
    # Call upsert on the Index object
    index.upsert_datapoints(datapoints=datapoints)


def query(
    *,
    query_vector: list[float],
    paper_ids: list[str],
    top_k: int,
    deployed_index_id: Optional[str] = None,
) -> List[dict]:
    # Queries must be done on the Index Endpoint
    endpoint = _get_endpoint()
    deployed = deployed_index_id or config.VERTEX_DEPLOYED_INDEX_ID
    if not deployed:
        raise config.SettingsError("VERTEX_DEPLOYED_INDEX_ID must be set for queries.")

    # Import namespace helper for filtering
    from google.cloud.aiplatform.matching_engine.matching_engine_index_endpoint import Namespace

    categorical_filters = []
    if paper_ids:
        categorical_filters.append(Namespace(name="paper_id", allow_tokens=paper_ids))

    # find_neighbors returns a list of lists (one per query)
    neighbors_list = endpoint.find_neighbors(
        deployed_index_id=deployed,
        queries=[query_vector],
        num_neighbors=top_k,
        filter=categorical_filters,
    )
    
    if not neighbors_list:
        return []

    # Get results for the single query we sent
    matches = neighbors_list[0]
    results = []
    for match in matches:
        # MatchNeighbor object has 'id' and 'distance' properties
        results.append(
            {
                "id": match.id,
                "score": match.distance,
                # Safe defaults since accessing metadata caused issues
                "metadata": {}, 
                "namespace_filters": [],
            }
        )
    return results