from __future__ import annotations
import json
import logging

import azure.functions as func

from gateway.orchestrator import handle_request
from gateway.storage import get_recent_receipts
from shared.models import GatewayRequest
from shared.config import Config

logger = logging.getLogger(__name__)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

_CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


@app.route(route="gateway", methods=["POST", "OPTIONS"])
def gateway(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=_CORS_HEADERS)

    # Config check on first real request
    missing = Config.validate()
    if missing:
        return func.HttpResponse(
            json.dumps({"error": f"Missing env vars: {missing}"}),
            status_code=500,
            headers=_CORS_HEADERS,
        )

    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Request body must be valid JSON."}),
            status_code=400,
            headers=_CORS_HEADERS,
        )

    prompt = body.get("prompt", "").strip()
    if not prompt:
        return func.HttpResponse(
            json.dumps({"error": "'prompt' is required and must not be empty."}),
            status_code=400,
            headers=_CORS_HEADERS,
        )

    request = GatewayRequest(
        prompt=prompt,
        urgency=body.get("urgency", "realtime"),
        system_prompt=body.get("system_prompt"),
        max_tokens=int(body.get("max_tokens", 500)),
    )

    try:
        response = handle_request(request)
    except Exception as exc:
        logger.exception("Pipeline error")
        return func.HttpResponse(
            json.dumps({"error": "Internal pipeline error.", "detail": str(exc)}),
            status_code=500,
            headers=_CORS_HEADERS,
        )

    return func.HttpResponse(
        json.dumps(response.to_dict()),
        status_code=200,
        headers=_CORS_HEADERS,
    )


@app.route(route="receipts", methods=["GET", "OPTIONS"])
def receipts(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=_CORS_HEADERS)

    n = int(req.params.get("n", 100))
    data = get_recent_receipts(n)
    return func.HttpResponse(
        json.dumps({"receipts": data}),
        status_code=200,
        headers=_CORS_HEADERS,
    )
