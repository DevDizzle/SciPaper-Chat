# Scientific Paper Analyzer

FastAPI + Uvicorn service for ingesting scientific PDFs, indexing them with **Vertex AI Vector Search**, and answering grounded questions with **Gemini** via a lightweight **Google ADK–style agent**. Deployed to Cloud Run with Google-managed services for storage, embeddings, and retrieval.

## Architecture
- **Ingestion**: PDF upload → pypdf parsing → chunking → Vertex AI embeddings → upsert to Vertex AI Vector Search using only IDs + restricts.
- **Retrieval QA**: Paper-specific queries fetch relevant chunk IDs from Vector Search, load chunk text from Firestore, and Gemini generates grounded answers.
- **State**: Firestore stores chat history, chunk text, and running summaries.
- **Storage**: Raw PDFs live in Cloud Storage; summaries and chunk documents are persisted in Firestore.

### Key components
- `ingestion/pipeline.py` — PDF → chunks → embeddings → Vector Search upsert + Firestore chunk persistence + summary generation.
- `agents/adk_agent.py` — ADK-style agent that retrieves chunk IDs from Vector Search, fetches text from Firestore, and calls Gemini.
- `services/embedding.py` — Vertex AI text embedding helper.
- `services/vector_search.py` — Vertex AI Vector Search upsert/query helpers.
- `services/storage.py` — Firestore-backed summaries, chunk text, and chat history.
- `main.py` — FastAPI entrypoint exposing upload, query, and summary endpoints.

## API overview
- `GET /health` — liveness probe.
- `POST /upload` — upload a PDF file; ingests and indexes the paper and returns `paper_id` + initial summary.
- `POST /query` — JSON `{ "paper_id", "session_id", "question", "top_k" }`; runs retrieval + Gemini response.
- `GET /summary/{paper_id}` — fetch the latest stored summary for a paper.

## Running locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8080
```

Authentication uses Application Default Credentials for Firestore, Vertex AI, and Cloud Storage.

## Deployment (Cloud Run)
1. Ensure `requirements.txt` is regenerated from `requirements.in` with `pip-compile` after dependency changes.
2. Build and push the container image (Cloud Build or `docker build`).
3. Deploy to Cloud Run with environment variables:
   - `PROJECT_ID`, `REGION`
   - `GCS_BUCKET`
   - `VERTEX_INDEX_ENDPOINT_ID`, `VERTEX_DEPLOYED_INDEX_ID`
   - Optional: `EMBEDDING_MODEL`, `GENERATION_MODEL`, `DEFAULT_TOP_K`
4. Verify health at `/health`, then ingest a test PDF via `/upload` and query via `/query`.

## GCP-native RAG flow
1. **Upload**: PDF stored in GCS (optional) and parsed with pypdf.
2. **Chunk**: Simple character-based chunking with overlap for better context recall.
3. **Embed**: `text-embedding-004` (configurable) via Vertex AI.
4. **Index**: Upsert embeddings into Vertex AI Vector Search using `paper_id` namespace filters; only the datapoint ID and restricts are stored alongside the vector.
5. **Answer**: ADK-style agent retrieves top-k chunks, builds a grounded prompt, and calls Gemini (`gemini-1.5-flash-001` by default).

## Ingestion pipeline (local smoke test)
- POST `/upload` with a small PDF; confirms pypdf parsing, embedding calls, and Vector Search upserts.
- Use the returned `paper_id` with `/query` to validate retrieval + grounding.

## Notes
- LangChain and FAISS have been removed in favor of Vertex AI + Google client libraries to avoid resolver conflicts and align with GCP-native services.
- The service is backend-only; front-ends should call the HTTP API.
