# Agent 1 — Gateway Orchestrator & Green Receipt Engine
**This file is your complete implementation brief. Read it fully before writing a single line.**

---

## Your Role
You are building the **central nervous system** of EcoGateway: the main Azure Function that receives every incoming AI request, coordinates the 4-stage pipeline, assembles the Green Receipt, and returns the final response. Every other agent's work flows through you.

You also own the **SCI (Software Carbon Intensity) calculator** and the **Green Receipt JSON schema** — the transparency layer that makes this project defensible to the jury.

---

## Full Project Context

EcoGateway is an AI API proxy that intercepts requests destined for Azure OpenAI and passes them through a 4-stage sustainability pipeline:

1. **Semantic Cache** (Agent 2) — checks if a semantically similar query was answered before. Cache hits skip all compute.
2. **Prompt Compression** (Agent 3) — strips tokens from novel prompts before sending them to the model.
3. **Carbon-Aware Scheduler** (Agent 4) — picks the Azure OpenAI region with the lowest live carbon intensity, and defers non-urgent batch requests to a greener time window.
4. **Green Receipt** (you) — appended to every response: exact resources saved, route taken, SCI score.

The frontend (Agent 5) reads Green Receipts from a storage endpoint you expose and renders dashboards.

**Tech stack:**
- Backend: Python 3.11, Azure Functions v4
- Azure OpenAI (not raw OpenAI) — you call it with the `openai` Python SDK pointed at an Azure endpoint
- All config via environment variables, never hardcoded keys
- Inter-module communication: direct Python function calls (all agents run in the same Azure Function app)

---

## Your Deliverables

### Files to create
```
backend/
├── gateway/
│   ├── __init__.py
│   ├── function.json          # Azure Function HTTP trigger config
│   ├── orchestrator.py        # Main pipeline coordinator (YOUR primary file)
│   ├── receipt.py             # Green Receipt assembly + SCI calculation
│   └── storage.py             # Receipt log storage (in-memory + file)
├── shared/
│   ├── __init__.py
│   ├── models.py              # Shared dataclasses: GatewayRequest, GatewayResponse, GreenReceipt
│   └── config.py              # Environment variable loading
├── host.json                  # Azure Functions host config
├── local.settings.json        # Local dev env vars (gitignored)
└── requirements.txt
```

---

## Interface Contract

### What you EXPOSE (other agents call these)

**HTTP endpoint** — the only public surface of the entire backend:
```
POST /api/gateway
Content-Type: application/json

{
  "prompt": "string — the user's query",
  "urgency": "realtime" | "batch",          // batch = deferrable to greener window
  "system_prompt": "string (optional)",
  "max_tokens": 500                          // optional, default 500
}
```

**Response:**
```json
{
  "response": "the model's answer",
  "green_receipt": { ... }                   // see GreenReceipt schema below
}
```

**GET /api/receipts** — returns last 100 receipts for the dashboard
```json
{ "receipts": [ ...GreenReceipt objects... ] }
```

### What you CONSUME (you call these)

From Agent 2 (cache/cache_service.py):
```python
from cache.cache_service import check_cache, store_in_cache

result = check_cache(prompt: str) -> CacheResult
# CacheResult: { hit: bool, response: str | None, similarity: float }

store_in_cache(prompt: str, response: str) -> None
```

From Agent 3 (compression/compressor.py):
```python
from compression.compressor import compress_prompt

result = compress_prompt(prompt: str) -> CompressionResult
# CompressionResult: { compressed_prompt: str, original_tokens: int, compressed_tokens: int, ratio: float }
```

From Agent 4 (scheduler/carbon_scheduler.py):
```python
from scheduler.carbon_scheduler import get_routing_decision, get_deferred_response

decision = get_routing_decision(prompt: str, urgency: str) -> RoutingDecision
# RoutingDecision: {
#   model: str,           # "gpt-4o-mini" | "gpt-4o"
#   region: str,          # Azure region name e.g. "westeurope"
#   endpoint: str,        # Full Azure OpenAI endpoint URL
#   api_key_env: str,     # Name of the env var holding the key for this region
#   defer: bool,
#   defer_until: str | None,   # ISO8601 if deferred
#   carbon_intensity: float,   # gCO2/kWh
#   carbon_intensity_baseline: float  # baseline region for comparison
# }
```

---

## Green Receipt Schema

This is the most important output of the project. Every field must be real — no fake numbers.

```python
@dataclass
class GreenReceipt:
    request_id: str          # uuid4
    timestamp: str           # ISO8601

    # Stage 1
    cache_hit: bool
    cache_similarity: float  # 0.0 if miss

    # Stage 2
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float  # compressed/original, e.g. 0.72
    tokens_saved_by_compression: int

    # Stage 3 + 4
    complexity_tier: int      # 1=mini, 2=standard, 3=large
    model_used: str
    region_used: str
    carbon_intensity: float   # gCO2/kWh at time of request
    deferred: bool
    defer_until: str | None

    # SCI Calculation (Green Software Foundation formula)
    # SCI = (E * I + M) / R
    # E = energy in kWh
    # I = carbon intensity gCO2/kWh
    # M = embodied carbon (fixed estimate per request: 0.000001 kgCO2)
    # R = functional unit (per request)
    energy_kwh: float         # calculated from token count × model energy factor
    gco2_this_request: float  # E * I + M
    gco2_baseline: float      # what gpt-4o in eastus would have cost
    gco2_saved: float         # baseline - this_request (can be negative, be honest)
    sci_score: float          # gCO2 per request

    # Human summary
    savings_pct: float        # percentage saved vs baseline
    route_explanation: str    # one sentence: why this route was chosen
```

**SCI calculation constants (use these, cite sources in comments):**
```python
# Energy per 1000 tokens (kWh) — from published ML CO2 benchmarks
# Source: Patterson et al. 2021, ML CO2 Impact calculator
MODEL_ENERGY_FACTORS = {
    "gpt-4o":      0.00090,   # kWh per 1k tokens
    "gpt-4o-mini": 0.00009,   # 10x more efficient
}

# Embodied carbon per request (amortized hardware manufacturing)
EMBODIED_CARBON_PER_REQUEST = 0.000001  # kgCO2, small but honest
```

---

## Implementation Order

**Do these in order. Do not skip ahead.**

### Step 1 — Shared models (shared/models.py)
Define all dataclasses: `GatewayRequest`, `GatewayResponse`, `GreenReceipt`, `CacheResult`, `CompressionResult`, `RoutingDecision`. These are the contracts every other agent depends on. Use Python `dataclasses` with `dataclasses_json` for serialization.

### Step 2 — Config loader (shared/config.py)
```python
import os

class Config:
    # Azure OpenAI — one entry per region
    AZURE_OAI_WESTEUROPE_ENDPOINT = os.environ["AZURE_OAI_WESTEUROPE_ENDPOINT"]
    AZURE_OAI_WESTEUROPE_KEY = os.environ["AZURE_OAI_WESTEUROPE_KEY"]
    AZURE_OAI_EASTUS_ENDPOINT = os.environ["AZURE_OAI_EASTUS_ENDPOINT"]
    AZURE_OAI_EASTUS_KEY = os.environ["AZURE_OAI_EASTUS_KEY"]
    AZURE_OAI_API_VERSION = os.environ.get("AZURE_OAI_API_VERSION", "2024-02-01")
```
Never put real values here. They come from local.settings.json locally and Azure Function App Settings in production.

### Step 3 — Receipt builder (gateway/receipt.py)
Implement `build_receipt(...)` that takes all pipeline stage outputs and produces a `GreenReceipt`. Implement `calculate_sci(model, tokens, carbon_intensity)` using the constants above.

### Step 4 — Storage (gateway/storage.py)
Simple in-memory deque of last 500 receipts, also written to a local JSON file (`/tmp/receipts.json`) for persistence across warm starts. Expose `append_receipt(receipt)` and `get_recent_receipts(n=100)`.

### Step 5 — Orchestrator (gateway/orchestrator.py)
```python
async def handle_request(request: GatewayRequest) -> GatewayResponse:
    # Stage 1: Cache check
    cache_result = check_cache(request.prompt)
    if cache_result.hit:
        receipt = build_receipt(cache_hit=True, ...)
        append_receipt(receipt)
        return GatewayResponse(response=cache_result.response, green_receipt=receipt)

    # Stage 2: Compress
    compression = compress_prompt(request.prompt)

    # Stage 3+4: Route
    routing = get_routing_decision(compression.compressed_prompt, request.urgency)

    if routing.defer:
        # For batch deferred requests, return immediately with a job_id
        # The scheduler will process it and store the result
        return GatewayResponse(
            response=None,
            job_id=str(uuid4()),
            status="queued",
            green_receipt=build_receipt(deferred=True, ...)
        )

    # Call Azure OpenAI
    response_text = await call_azure_openai(
        prompt=compression.compressed_prompt,
        system_prompt=request.system_prompt,
        model=routing.model,
        endpoint=routing.endpoint,
        api_key=os.environ[routing.api_key_env],
        max_tokens=request.max_tokens
    )

    # Store in cache
    store_in_cache(request.prompt, response_text)

    # Build receipt
    receipt = build_receipt(
        cache_hit=False,
        cache_similarity=cache_result.similarity,
        compression=compression,
        routing=routing,
        model=routing.model,
        response_tokens=len(response_text.split())  # rough estimate
    )
    append_receipt(receipt)

    return GatewayResponse(response=response_text, green_receipt=receipt)
```

### Step 6 — Azure Function HTTP trigger (gateway/__init__.py)
Wire `handle_request` to an Azure Function HTTP trigger. Accept POST to `/api/gateway`, parse body into `GatewayRequest`, return JSON.

Also wire GET `/api/receipts` to return `get_recent_receipts()`.

### Step 7 — Stubs for other agents
If other agents aren't ready, implement stub versions in their expected locations:
```python
# cache/cache_service.py stub
def check_cache(prompt): return CacheResult(hit=False, response=None, similarity=0.0)
def store_in_cache(prompt, response): pass

# compression/compressor.py stub
def compress_prompt(prompt):
    tokens = len(prompt.split())
    return CompressionResult(compressed_prompt=prompt, original_tokens=tokens, compressed_tokens=tokens, ratio=1.0)

# scheduler/carbon_scheduler.py stub
def get_routing_decision(prompt, urgency):
    return RoutingDecision(model="gpt-4o-mini", region="westeurope", ...)
```
This lets you test the full pipeline end-to-end before the other agents are done.

---

## Requirements.txt
```
azure-functions
openai>=1.0.0
dataclasses-json
tiktoken
python-dotenv
```

---

## local.settings.json (gitignored — never commit)
```json
{
  "IsEncrypted": false,
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AZURE_OAI_WESTEUROPE_ENDPOINT": "https://YOUR-RESOURCE.openai.azure.com/",
    "AZURE_OAI_WESTEUROPE_KEY": "YOUR_KEY",
    "AZURE_OAI_EASTUS_ENDPOINT": "https://YOUR-RESOURCE-2.openai.azure.com/",
    "AZURE_OAI_EASTUS_KEY": "YOUR_KEY_2",
    "ELECTRICITY_MAPS_KEY": "YOUR_KEY"
  }
}
```

---

## Definition of Done
- [ ] `POST /api/gateway` accepts a prompt and returns a response + green receipt with real numbers
- [ ] `GET /api/receipts` returns the last 100 receipts as JSON
- [ ] Cache hit returns in <50ms with `cache_hit: true` and `gco2_this_request: 0`
- [ ] SCI score is calculated using real token counts, not guesses
- [ ] No API keys appear anywhere in source code
- [ ] Stubs exist for all three dependency modules so the gateway runs standalone
