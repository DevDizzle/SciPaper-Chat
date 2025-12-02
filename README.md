# Scientific Paper Analyzer

A FastAPI + Uvicorn service for analyzing collections of scientific papers. The system accepts a list of arXiv URLs, expands the collection with related papers using a similarity search service, and provides multi-document Retrieval-Augmented Generation (RAG) capabilities using **Vertex AI Vector Search** and **Gemini**.

## Architecture & Workflow

The system operates in a multi-stage process to build a knowledge base and answer questions.

1.  **URL Submission**: The user submits a list of 1-10 public arXiv URLs.
2.  **Corpus Expansion**: For each submitted URL, the system queries an external similarity search service (`paperrec-search`) to find the top 5 related papers. This creates an expanded knowledge base for the session.
3.  **Ingestion**: The system downloads the PDF for every paper (both initial and similar), chunks the text, generates embeddings with Vertex AI, and upserts them into Vertex AI Vector Search. Each paper is indexed under its unique arXiv ID.
4.  **Summarization**: The system generates a running summary for each of the initial papers submitted by the user.
5.  **Multi-Document Q&A**: The user can ask questions against the entire collection of papers. The system retrieves relevant text chunks from across the whole corpus, constructs a grounded prompt, and uses the Gemini model to generate an answer with citations to the source papers.

### Key Components
- `main.py`: FastAPI entrypoint exposing the `/analyze_urls` and `/query` endpoints.
- `ingestion/pipeline.py`: Orchestrates PDF parsing, chunking, embedding, and indexing into Vertex AI Vector Search.
- `agents/adk_agent.py`: An ADK-style agent that retrieves context from multiple documents and calls Gemini to generate grounded, cited answers.
- `services/vector_search.py`: Wraps the Vertex AI Vector Search client to query across multiple paper IDs.
- `services/storage.py`: Firestore-backed storage for chat history, text chunks, and summaries.

## API Overview
- `GET /health`: Liveness probe.
- `POST /analyze_urls`: The primary endpoint. Accepts a JSON list of arXiv URLs (`{ "urls": ["...", "..."] }`). It orchestrates the entire ingestion and summarization workflow and returns a list of all processed paper IDs and the summaries for the initial papers.
- `POST /query`: Accepts a JSON payload with a list of paper IDs to search across, a session ID for history, and the user's question (`{ "paper_ids": ["...", "..."], "question": "..." }`).
- `GET /summary/{paper_id}`: Fetches the stored summary for one of the initial papers.
- `POST /upload`: A legacy endpoint for uploading a single PDF file directly.

## Running Locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8080
```
Authentication uses Application Default Credentials for Firestore, Vertex AI, and Cloud Storage.

## Deployment (Cloud Run)
1.  Ensure `requirements.txt` is up-to-date.
2.  Build and push the container image using Google Cloud Build:
    ```bash
    gcloud builds submit SciPaper-Chat --tag gcr.io/your-project-id/scipaper-analyzer
    ```
3.  Deploy to Cloud Run with the necessary environment variables:
    ```bash
    bash SciPaper-Chat/scripts/deploy.sh
    ```
4.  Verify the service is running by checking the `/health` endpoint.

## Notes
- The service is backend-only; a separate frontend should be used to interact with the API.
- The project is designed to be GCP-native, leveraging managed services for scalability and reliability.
