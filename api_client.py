# api_client.py
"""
Simple API client for Streamlit to communicate with the background browser service.
"""
import os
import requests

def run_agent_via_api(session_id: str, query: str):
    # Use environment variable for backend URL
    backend_url = os.getenv('BACKEND_URL', 'http://aiagent-prod-alb-63082312.us-east-1.elb.amazonaws.com')
    api_url = f"{backend_url}/run_agent"
    
    payload = {"session_id": session_id, "query": query}
    resp = requests.post(api_url, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()