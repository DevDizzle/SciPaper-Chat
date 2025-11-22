# Deployment Plan - Scientific Paper Analyzer

## Prerequisites
- Google Cloud project with Vertex AI and Firestore enabled.
- Authenticated gcloud CLI with application-default credentials for local testing.
- Docker installed locally for image builds.

## Build and Push Container
```bash
PROJECT_ID=<your-project-id>
REGION=us-central1
SERVICE=scipaper-analyzer

# Build
gcloud builds submit --tag gcr.io/${PROJECT_ID}/${SERVICE}
```

## Deploy to Cloud Run
```bash
gcloud run deploy ${SERVICE} \
  --image gcr.io/${PROJECT_ID}/${SERVICE} \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=${PROJECT_ID} \
  --min-instances=0 \
  --max-instances=10
```

## Firestore Indexing
Firestore in Native mode requires no additional indexes for the simple ordering used here.

## Verification Checklist
1. **TC-UR1.1 Upload**: Upload a PDF in the Gradio UI; expect summary within 10 seconds.
2. **TC-NFR6 Persistence**: Ask a question, refresh the UI, then ask "What did I just ask you?" to confirm history retrieval from Firestore.
3. **TC-UR3.3 Scalability**: Confirm the Cloud Run service shows `min-instances=0` and `max-instances=10` in the deployment parameters.
