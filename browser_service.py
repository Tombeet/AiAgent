import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import threading
from typing import Dict
from main import agent_executor, parser
from tools import close_browser
from fastapi.staticfiles import StaticFiles

import os

session_lock = threading.Lock()
session_store: Dict[str, dict] = {}

app = FastAPI()

# 👇 serve /screenshots folder via HTTP
if not os.path.exists("screenshots"):
    os.makedirs("screenshots")
app.mount("/screenshots", StaticFiles(directory="screenshots"), name="screenshots")

class AgentRequest(BaseModel):
    session_id: str
    query: str

@app.post("/run_agent")
async def run_agent_endpoint(req: AgentRequest, request: Request):
    with session_lock:
        if req.session_id not in session_store:
            session_store[req.session_id] = {}

    try:
        response = await agent_executor.ainvoke({"query": req.query})
        output = response.get("output", "")

        try:
            structured = parser.parse(output)
            screenshot_path = getattr(structured, 'screenshot_path', None)

            # 👇 dynamically detect public URL based on the incoming request
            if screenshot_path and os.path.exists(screenshot_path):
                filename = os.path.basename(screenshot_path)
                # Instead of returning a public URL, just return the filename
                screenshot_url = f"/app/screenshots/{filename}"
            else:
                screenshot_url = None

            return JSONResponse({
                "status": "success",
                "output": structured.message,
                "raw_output": output,
                "structured": structured.model_dump(),
                "screenshot_path": screenshot_url,  # dynamic URL returned
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
    await close_browser()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
