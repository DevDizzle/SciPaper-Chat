# Scientific Paper Analyzer

A Cloud Run–ready FastAPI service that ingests scientific PDFs or ArXiv entries, summarizes them, and answers grounded questions using Vertex AI and Firestore-backed session persistence.

## Features
- **PDF or ArXiv ingestion** with automatic chunking and FAISS vector store creation.
- **Summaries on upload** to give users immediate context.
- **Grounded Q&A** powered by Gemini 1.5 Flash and Vertex AI embeddings.
- **Persistent chat history** via Firestore to satisfy session continuity on stateless Cloud Run.
- **Backend-only container**: The production image runs FastAPI + Uvicorn exclusively; UI clients connect over HTTP.

## API overview
- `GET /health` — liveness probe.
- `POST /session` — returns a new session ID for Firestore-backed history.
- `POST /analyze` — accepts a PDF upload (`file`) or ArXiv ID (`arxiv_id` form field), builds embeddings, and returns status, running summary, and a session ID.
- `POST /chat` — accepts JSON `{ "message": "...", "session_id": "..." }` and returns `{ "response": "..." }`, grounded by the current vector store and persisted history.

## Running Locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8080
```

Ensure Google application-default credentials are available so Firestore and Vertex AI can authenticate.

For local UI experiments you can install optional dev dependencies:

```bash
pip install -r requirements-dev.txt
```

Then run your preferred UI (e.g., Streamlit or a React dev server) against the FastAPI endpoints.

## Deployment
See [docs/deployment_plan.md](docs/deployment_plan.md) for Cloud Run deployment steps and verification checklist.

## UI direction
- **Backend:** FastAPI on Cloud Run.
- **Frontend options:**
  - Streamlit app (for demos/internal usage) that calls the FastAPI API.
  - React SPA (Vite/Next.js) that uploads PDFs, shows summaries, and chats with the backend.
- **Gradio:** no longer used in production; keep only in dev dependencies if you want a local Gradio prototype.
