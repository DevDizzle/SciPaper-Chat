# Scientific Paper Analyzer

A Cloud Run–ready Gradio application that ingests scientific PDFs or ArXiv entries, summarizes them, and answers grounded questions using Vertex AI and Firestore-backed session persistence.

## Features
- **PDF or ArXiv ingestion** with automatic chunking and FAISS vector store creation.
- **Summaries on upload** to give users immediate context.
- **Grounded Q&A** powered by Gemini 1.5 Flash and Vertex AI embeddings.
- **Persistent chat history** via Firestore to satisfy session continuity on stateless Cloud Run.

## Running Locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8080
```

Ensure Google application-default credentials are available so Firestore and Vertex AI can authenticate.

## Deployment
See [docs/deployment_plan.md](docs/deployment_plan.md) for Cloud Run deployment steps and verification checklist.
