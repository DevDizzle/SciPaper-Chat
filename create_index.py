from google.cloud import aiplatform
import os

# Configuration
PROJECT_ID = os.getenv("PROJECT_ID", "paperrec-ai")
REGION = os.getenv("REGION", "us-central1")

aiplatform.init(project=PROJECT_ID, location=REGION)

print(f"Creating Streaming Index in {PROJECT_ID}...")

# Create an Index with STREAM_UPDATE enabled
index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
    display_name="scipaper-streaming-index",
    description="Streaming index for SciPaper Chat",
    dimensions=768,  # Matches text-embedding-004
    approximate_neighbors_count=150,
    distance_measure_type="DOT_PRODUCT_DISTANCE",
    leaf_node_embedding_count=500,
    leaf_nodes_to_search_percent=7,
    index_update_method="STREAM_UPDATE",  # Crucial for upsert_datapoints
    shard_size="SHARD_SIZE_SMALL"
)

print(f"\n[✓] Index creation initiated.")
print(f"    Resource Name: {index.resource_name}")
print(f"    ID: {index.name}")
print("\nNote: Index creation takes 30-60 minutes. You can check status in the Cloud Console or by running:")
print(f"gcloud ai indexes list --region={REGION}")