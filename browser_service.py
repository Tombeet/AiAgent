# browser_service.py

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import threading
from typing import Dict
from main import agent_executor, parser
from tools import close_browser  # so we can close nicely on shutdown

session_lock = threading.Lock()
session_store: Dict[str, dict] = {}

app = FastAPI()

class AgentRequest(BaseModel):
    session_id: str
    query: str

@app.post("/run_agent")
async def run_agent_endpoint(req: AgentRequest):
    # currently not in use: create a new session if not exists
    with session_lock:
        if req.session_id not in session_store:
            session_store[req.session_id] = {}

    try:
        # IMPORTANT: use ainvoke so async tools are awaited properly
        response = await agent_executor.ainvoke({"query": req.query})
        output = response.get("output", "")

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
                "structured": None
            })
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "error": str(e)
        })

@app.on_event("shutdown")
async def _shutdown():
    # close Playwright cleanly on container stop
    await close_browser()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
