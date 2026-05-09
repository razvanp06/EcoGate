from __future__ import annotations
import logging
import os
import uuid
from typing import Optional

import tiktoken
from openai import AzureOpenAI

from shared.models import GatewayRequest, GatewayResponse, GreenReceipt
from shared.config import Config
from gateway.receipt import build_receipt
from gateway.storage import append_receipt
from cache.cache_service import check_cache, store_in_cache
from compression.compressor import compress_prompt
from scheduler.carbon_scheduler import get_routing_decision

logger = logging.getLogger(__name__)

_encoder = tiktoken.get_encoding("cl100k_base")

# One client per region, created once at module load and reused across requests.
_clients: dict[str, AzureOpenAI] = {}


def _get_client(endpoint: str, api_key: str) -> AzureOpenAI:
    if endpoint not in _clients:
        _clients[endpoint] = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=Config.AZURE_OAI_API_VERSION,
        )
    return _clients[endpoint]


def _call_model(
    prompt: str,
    system_prompt: Optional[str],
    model: str,
    endpoint: str,
    api_key: str,
    max_tokens: int,
) -> tuple[str, int]:
    """Returns (response_text, total_tokens_used)."""
    client = _get_client(endpoint, api_key)
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
    )
    text = completion.choices[0].message.content or ""
    total_tokens = completion.usage.total_tokens if completion.usage else len(_encoder.encode(text))
    return text, total_tokens


def handle_request(request: GatewayRequest) -> GatewayResponse:
    original_tokens = len(_encoder.encode(request.prompt))

    # ── Stage 1: Semantic Cache ───────────────────────────────────────────────
    cache_result = check_cache(request.prompt)

    if cache_result.hit:
        receipt = build_receipt(
            cache_result=cache_result,
            compression=None,
            routing=None,
            total_tokens=original_tokens,
            original_prompt_tokens=original_tokens,
        )
        append_receipt(receipt)
        logger.info("Cache hit — similarity %.3f", cache_result.similarity)
        return GatewayResponse(response=cache_result.response, green_receipt=receipt)

    # ── Stage 2: Prompt Compression ──────────────────────────────────────────
    compression = compress_prompt(request.prompt)
    logger.info(
        "Compression: %d → %d tokens (%.0f%% saved)",
        compression.original_tokens,
        compression.compressed_tokens,
        (1 - compression.ratio) * 100,
    )

    # ── Stage 3+4: Complexity Routing + Carbon-Aware Scheduling ──────────────
    routing = get_routing_decision(compression.compressed_prompt, request.urgency)
    logger.info("Routing: %s @ %s (%.0f gCO₂/kWh)", routing.model, routing.region, routing.carbon_intensity)

    if routing.defer:
        receipt = build_receipt(
            cache_result=cache_result,
            compression=compression,
            routing=routing,
            total_tokens=compression.compressed_tokens,
            original_prompt_tokens=original_tokens,
        )
        append_receipt(receipt)
        return GatewayResponse(
            response=None,
            green_receipt=receipt,
            job_id=str(uuid.uuid4()),
            status="queued",
        )

    # ── Model call ────────────────────────────────────────────────────────────
    api_key = os.environ.get(routing.api_key_env, "")
    response_text, total_tokens = _call_model(
        prompt=compression.compressed_prompt,
        system_prompt=request.system_prompt,
        model=routing.model,
        endpoint=routing.endpoint,
        api_key=api_key,
        max_tokens=request.max_tokens,
    )

    # Store original (uncompressed) prompt in cache so future lookups match naturally
    store_in_cache(request.prompt, response_text)

    # ── Green Receipt ─────────────────────────────────────────────────────────
    receipt = build_receipt(
        cache_result=cache_result,
        compression=compression,
        routing=routing,
        total_tokens=total_tokens,
        original_prompt_tokens=original_tokens,
    )
    append_receipt(receipt)

    return GatewayResponse(response=response_text, green_receipt=receipt)
