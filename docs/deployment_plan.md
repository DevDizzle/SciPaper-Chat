# Deployment Plan - Scientific Paper Analyzer

## Prerequisites
- Google Cloud project with Vertex AI, Firestore, and Cloud Storage enabled.
- Application Default Credentials available for build/runtime (Cloud Build + Cloud Run).
- Docker or Cloud Build access to build the container image.

## Build and Push Container
```bash
PROJECT_ID=<your-project-id>
REGION=us-central1
SERVICE=scipaper-analyzer

gcloud builds submit --tag gcr.io/${PROJECT_ID}/${SERVICE}
```

## Deploy to Cloud Run
```bash
gcloud run deploy ${SERVICE} \
  --image gcr.io/${PROJECT_ID}/${SERVICE} \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars PROJECT_ID=${PROJECT_ID},REGION=${REGION},GCS_BUCKET=<your-bucket>,VERTEX_INDEX_ENDPOINT_ID=<endpoint-id>,VERTEX_DEPLOYED_INDEX_ID=<deployed-id>
```

Optional overrides: `EMBEDDING_MODEL`, `GENERATION_MODEL`, `DEFAULT_TOP_K`, `SESSIONS_COLLECTION`, `SUMMARIES_COLLECTION`.

## Firestore setup
Firestore in Native mode suffices; collections are created on demand:
- `sessions/{session_id}/messages`
- `summaries/{paper_id}`

## Verification Checklist
1. **Health**: `GET /health` returns `{ "status": "ok" }`.
2. **Ingestion**: `POST /upload` with a PDF returns `paper_id` and summary; verify Vector Search upserts in logs.
3. **Query**: `POST /query` using returned `paper_id` yields grounded Gemini answers.
4. **Summary retrieval**: `GET /summary/{paper_id}` returns the stored summary.
5. **Scaling**: Confirm Cloud Run min/max instances per deployment parameters.
