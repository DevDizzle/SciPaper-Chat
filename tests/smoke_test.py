import requests
import json

# The production URL for the scipaper-analyzer service
API_URL = "https://scipaper-analyzer-550651297425.us-central1.run.app"
ANALYZE_URL = f"{API_URL}/analyze_urls"

# The list of arXiv URLs provided by the user
ARXIV_URLS = [
    "https://arxiv.org/abs/2504.07139",
    "https://arxiv.org/abs/2508.11957",
    "https://arxiv.org/abs/2508.13678",
    "https://arxiv.org/abs/2511.09378",
    "https://arxiv.org/abs/2508.07407",
]

def test_production_summarization():
    """
    Tests the production /analyze_urls endpoint to diagnose the summarization issue.
    """
    print(f"--- Testing Production Endpoint: {ANALYZE_URL} ---")
    print(f"Sending {len(ARXIV_URLS)} URLs for analysis...")

    try:
        # Make the POST request to the production service
        payload = {"urls": ARXIV_URLS}
        response = requests.post(ANALYZE_URL, json=payload, timeout=600)  # 10 minute timeout

        # Print the raw response details
        print(f"\n--- Response ---")
        print(f"Status Code: {response.status_code}")
        print("Headers:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        
        # Try to parse and print the JSON body
        try:
            response_json = response.json()
            print("\nResponse Body (JSON):")
            print(json.dumps(response_json, indent=2))

            # Check for the 'summaries' key
            if "summaries" in response_json:
                print("\n[✓] 'summaries' key found in the response.")
                summaries = response_json["summaries"]
                if summaries:
                    print("\n--- Summaries ---")
                    for paper_id, summary in summaries.items():
                        print(f"  - {paper_id}:")
                        print(f"    {summary[:200]}...")
                else:
                    print("\n[!] The 'summaries' dictionary is empty.")
            else:
                print("\n[X] FATAL: 'summaries' key NOT found in the response body.")

        except json.JSONDecodeError:
            print("\n[X] FATAL: Failed to decode JSON from response body.")
            print("Raw Response Body (Text):")
            print(response.text)

    except requests.exceptions.RequestException as e:
        print(f"\n[X] FATAL: A request exception occurred: {e}")

if __name__ == "__main__":
    test_production_summarization()
