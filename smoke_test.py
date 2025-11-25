import os
import sys

# Ensure we can import from the current directory
sys.path.append(os.getcwd())

import config
from services import storage, gcs
from ingestion.pipeline import ingest_pdf
from agents.adk_agent import PaperRAGAgent

# The ID is derived from the filename provided
PAPER_ID = "06cbe85c-a864-434c-b26e-fb7d2cc2cf71"
PDF_FILENAME = f"{PAPER_ID}.pdf"

def check_and_ingest():
    print(f"Checking status for Paper ID: {PAPER_ID}")

    # 1. Check if already indexed by looking for the summary in Firestore
    # This prevents duplicate embedding costs and index entries.
    summary = storage.fetch_summary(PAPER_ID)
    
    if summary:
        print(" [✓] Paper already indexed. Summary found.")
        print(f"     Summary excerpt: {summary[:100]}...")
    else:
        print(" [!] Paper not found in index. Starting ingestion...")
        
        # 2. Download from GCS since it's not in the index yet
        print(f"     Downloading {PDF_FILENAME} from bucket {config.GCS_BUCKET}...")
        try:
            client = gcs.get_client()
            bucket = client.bucket(config.GCS_BUCKET)
            blob = bucket.blob(PDF_FILENAME)
            
            if not blob.exists():
                print(f" [X] File {PDF_FILENAME} does not exist in bucket {config.GCS_BUCKET}.")
                return False

            pdf_bytes = blob.download_as_bytes()
            print("     Download complete. File size:", len(pdf_bytes), "bytes")
            
            # 3. Run Ingestion Pipeline
            print("     Ingesting PDF (Parsing -> Chunking -> Embedding -> Vector Search)...")
            # ingest_pdf returns (paper_id, summary)
            _, new_summary = ingest_pdf(pdf_bytes, paper_id=PAPER_ID)
            
            print(" [✓] Ingestion complete.")
            print(f"     Generated Summary: {new_summary[:100]}...")
            
        except Exception as e:
            print(f" [X] Error during ingestion: {e}")
            return False
            
    return True

def test_query():
    print("\nTesting Query Service...")
    # A generic question that requires reading the content to answer
    query_text = "What are the main contributions and findings of this paper?"
    print(f" Question: {query_text}")
    
    try:
        agent = PaperRAGAgent()
        
        # 4. Call the agent
        response = agent.answer_question(
            paper_id=PAPER_ID,
            session_id="smoke-test-session",
            question=query_text,
            top_k=config.DEFAULT_TOP_K
        )
        
        print(" [✓] Response received:")
        print("-" * 60)
        print(response)
        print("-" * 60)
    except Exception as e:
        print(f" [X] Error during query: {e}")

if __name__ == "__main__":
    if check_and_ingest():
        test_query()