# api_client.py
"""
Simple API client for Streamlit to communicate with the background browser service.
"""
import requests

def run_agent_via_api(session_id: str, query: str, api_url: str = "http://backend:8000/run_agent"):
    payload = {"session_id": session_id, "query": query}
    resp = requests.post(api_url, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()
