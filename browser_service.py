# browser_service.py
"""
Background service to manage persistent Playwright browser sessions and run the agent for each user/session.
Exposes an HTTP API for Streamlit to interact with.
"""

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uuid
import threading
from typing import Dict
from main import agent_executor, parser

# currently not in use: Session store: maps session_id to browser state (could be expanded)
session_lock = threading.Lock()
session_store: Dict[str, dict] = {}

app = FastAPI()

class AgentRequest(BaseModel):
    session_id: str
    query: str

@app.post("/run_agent")
def run_agent_endpoint(req: AgentRequest):
    # currently not in use: create a new session if not exists
    with session_lock:
        if req.session_id not in session_store:
            session_store[req.session_id] = {}  # Placeholder for browser/page objects if needed
    
    # Run the agent (this will use global Playwright for now, but can be extended)
    try:
        response = agent_executor.invoke({"query": req.query})
        output = response.get("output", "")
        # Try to parse structured output
        try:
            structured = parser.parse(output)
            screenshot_path = getattr(structured, 'screenshot_path', None)
            return JSONResponse({
                "status": "success",
                "output": structured.message,
                "raw_output": output,
                "structured": structured.model_dump(),
                "screenshot_path": screenshot_path
            })
        except Exception:
            return JSONResponse({
                "status": "success",
                "output": output,
                "raw_output": output,
                "structured": None,
                
            })
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "error": str(e)
        })

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
