import os
import sys

# Ensure we can import from the current directory
sys.path.append(os.getcwd())

import config
from services import storage, gcs
from ingestion.pipeline import ingest_pdf
from agents.adk_agent import PaperRAGAgent

# Use the existing _v4 ID since we are just testing a different query against the same index
PAPER_ID = "06cbe85c-a864-434c-b26e-fb7d2cc2cf71_v4"

def check_and_ingest():
    print(f"Checking status for Paper ID: {PAPER_ID}")
    summary = storage.fetch_summary(PAPER_ID)
    
    if summary:
        print(" [✓] Paper already indexed. Summary found.")
        print(f"     Summary excerpt: {summary[:100]}...")
        return True
    else:
        print(" [!] Paper not found. Please revert PAPER_ID to a fresh version if you need to re-ingest.")
        return False

def test_query():
    print("\nTesting Query Service...")
    # [UPDATE] A specific question based on the summary to target the body text
    query_text = "How does the Agentic Context Engineering (ACE) framework manage context?"
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