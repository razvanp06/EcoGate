"""ASGI entrypoint for Vercel (Python runtime).

Mirrors the HTTP routes in function_app.py (Azure Functions) so both hosts
expose the same API. Vercel forwards the original request path, so every
route here keeps the public `/api` prefix.
"""
from __future__ import annotations
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from gateway.orchestrator import handle_request
from gateway.storage import get_recent_receipts
from scheduler.deferred_queue import get_all_jobs
from scheduler.worker import process_ready_jobs
from shared.models import GatewayRequest
from shared.config import Config

logger = logging.getLogger(__name__)

app = FastAPI(title="EcoGate API")

# Same-origin on Vercel; CORS kept for running the Vite dev server separately.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.post("/api/gateway")
async def gateway(req: Request) -> JSONResponse:
    missing = Config.validate()
    if missing:
        return JSONResponse({"error": f"Missing env vars: {missing}"}, status_code=500)

    try:
        body = await req.json()
    except ValueError:
        return JSONResponse({"error": "Request body must be valid JSON."}, status_code=400)
    if not isinstance(body, dict):
        return JSONResponse({"error": "Request body must be a JSON object."}, status_code=400)

    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        return JSONResponse(
            {"error": "'prompt' is required and must not be empty."}, status_code=400
        )

    request = GatewayRequest(
        prompt=prompt,
        urgency=body.get("urgency", "realtime"),
        system_prompt=body.get("system_prompt"),
        max_tokens=int(body.get("max_tokens", 2000)),
    )

    try:
        response = handle_request(request)
    except Exception as exc:
        logger.exception("Pipeline error")
        return JSONResponse(
            {"error": "Internal pipeline error.", "detail": str(exc)}, status_code=500
        )

    return JSONResponse(response.to_dict())


@app.get("/api/receipts")
def receipts(n: int = 100) -> dict:
    return {"receipts": get_recent_receipts(n)}


@app.get("/api/jobs")
def jobs() -> dict:
    """Expose the deferred-job queue so the dashboard can show pending work."""
    return {"jobs": [j.to_dict() for j in get_all_jobs()]}


@app.post("/api/jobs/process")
def process_jobs_now() -> dict:
    """Drain ready deferred jobs (replaces the Azure timer trigger on Vercel)."""
    return {"completed": process_ready_jobs()}
