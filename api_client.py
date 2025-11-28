"""
Simple API client for Streamlit to communicate with the background browser service.
"""
import os
import requests
from urllib.parse import urljoin

# API_BASE_URL to use if running application as container
#API_BASE_URL = os.environ["API_BASE_URL"].rstrip("/")

# API_BASE_URL to use if running application locally
API_BASE_URL = "http://localhost:8000"
_session = requests.Session()

def run_agent_via_api(session_id: str, query: str):
    payload = {"session_id": session_id, "query": query}
    # MODIFIED: Use /api/run_agent (no hardcoded backend:8000)
    url = urljoin(API_BASE_URL + "/", "api/run_agent")
    resp = _session.post(url, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()