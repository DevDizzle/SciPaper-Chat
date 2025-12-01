#!/bin/bash
# Deployment script for the SciPaper Analyzer service

# --- Configuration ---
PROJECT_ID="paperrec-ai"
SERVICE_NAME="scipaper-analyzer"
REGION="us-central1"
GCS_BUCKET="paperrec-ai-scipaper-bucket"
VERTEX_INDEX_ENDPOINT_ID="1277458788638523392"
VERTEX_DEPLOYED_INDEX_ID="scipaper_streaming_deploye_1764082870549"
VERTEX_INDEX_ID="3405084157129261056"
PAPERREC_SEARCH_URL="https://paperrec-search-550651297425.us-central1.run.app"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# --- Deployment Command ---
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars="PROJECT_ID=${PROJECT_ID},REGION=${REGION},GCS_BUCKET=${GCS_BUCKET},VERTEX_INDEX_ENDPOINT_ID=${VERTEX_INDEX_ENDPOINT_ID},VERTEX_DEPLOYED_INDEX_ID=${VERTEX_DEPLOYED_INDEX_ID},VERTEX_INDEX_ID=${VERTEX_INDEX_ID},PAPERREC_SEARCH_URL=${PAPERREC_SEARCH_URL}"
