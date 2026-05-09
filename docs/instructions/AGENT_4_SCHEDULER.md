# Agent 4 — Carbon-Aware Scheduler & Neural Router
**This file is your complete implementation brief. Read it fully before writing a single line.**

---

## Your Role
You are building **stages 3 and 4** of the EcoGateway pipeline:
- **Stage 3 (Neural Router):** Classify the complexity of the compressed prompt and assign it to the cheapest model tier that can handle it.
- **Stage 4 (Carbon-Aware Scheduler):** Query live grid carbon intensity data and route to the Azure OpenAI region with the lowest carbon footprint. For non-urgent requests, defer execution to a greener time window.

You own exactly one module: `backend/scheduler/`. Nothing else.

---

## Full Project Context

EcoGateway is an AI API proxy with a 4-stage sustainability pipeline:
1. Semantic Cache (Agent 2) — cache hit skips everything.
2. Prompt Compression (Agent 3) — strips tokens from novel prompts.
3. **Neural Router (you, Stage 3)** — routes to the cheapest model for the task.
4. **Carbon-Aware Scheduler (you, Stage 4)** — picks the greenest Azure region; defers batch jobs.

The Orchestrator (Agent 1) calls `get_routing_decision(prompt, urgency)` and uses your decision to make the actual Azure OpenAI call. You never call the model yourself — you only decide who calls it and when.

**Azure OpenAI deployments available (assume these exist, Agent 1 configures the keys):**
| Region | Env var prefix | Grid avg gCO₂/kWh | Models deployed |
|--------|---------------|-------------------|-----------------|
| West Europe (Netherlands) | `AZURE_OAI_WESTEUROPE` | ~150 | gpt-4o-mini, gpt-4o |
| East US | `AZURE_OAI_EASTUS` | ~350 | gpt-4o-mini, gpt-4o |

Two regions is enough for the demo. The carbon difference is real and significant.

---

## Your Deliverables

### Files to create
```
backend/
└── scheduler/
    ├── __init__.py
    ├── carbon_scheduler.py   # YOUR primary file — the public function
    ├── complexity_router.py  # Prompt complexity classification → model tier
    ├── carbon_client.py      # Electricity Maps API client
    └── deferred_queue.py     # In-memory queue for batch/deferred requests
```

---

## Interface Contract

### What you EXPOSE (Agent 1 calls this — do not change signature)

```python
# scheduler/carbon_scheduler.py

from shared.models import RoutingDecision

def get_routing_decision(prompt: str, urgency: str) -> RoutingDecision:
    """
    1. Classify prompt complexity → model tier
    2. Fetch live carbon intensity for each available Azure region
    3. Select lowest-carbon region that has the required model tier
    4. If urgency == "batch" and carbon intensity is above threshold, set defer=True
    Returns a RoutingDecision with everything Agent 1 needs to make the API call.
    """
    ...
```

### Shared model (defined in shared/models.py by Agent 1)
```python
@dataclass
class RoutingDecision:
    model: str               # "gpt-4o-mini" or "gpt-4o"
    region: str              # e.g. "westeurope"
    endpoint: str            # Full Azure OpenAI endpoint URL
    api_key_env: str         # Name of env var for this region's API key
    complexity_tier: int     # 1 = mini, 2 = standard (gpt-4o)
    defer: bool              # True = queue this request, don't call model yet
    defer_until: str | None  # ISO8601 datetime if deferred, else None
    carbon_intensity: float  # Live gCO₂/kWh for chosen region
    carbon_intensity_baseline: float  # eastus baseline for comparison
    routing_reason: str      # One sentence: why this route was chosen
```

If Agent 1 hasn't published shared/models.py yet, define RoutingDecision locally and move it later.

---

## Stage 3: Complexity Router (complexity_router.py)

Routing is **per-request** — every prompt is classified independently. A simple follow-up after a complex question goes back to the cheap model. This is intentional and correct: the cache handles repeated context, and per-request routing avoids locking a session into an expensive model unnecessarily.

The classifier uses a **layered scoring system**. Each layer adds to a `complexity_score`. The final score determines the tier. This is transparent, tunable, and has no external dependencies.

### Scoring layers (applied in order)

```python
import re
import tiktoken

_encoder = tiktoken.get_encoding("cl100k_base")

# Layer 2: keyword signals and their weights
COMPLEX_KEYWORDS = {
    # High-weight: strong indicators of multi-step reasoning
    "step by step": 3,
    "compare and contrast": 3,
    "design": 3,
    "architect": 3,
    "prove": 3,
    "derive": 3,
    "trade-offs": 3,
    "pros and cons": 3,
    # Medium-weight
    "explain in detail": 2,
    "analyze": 2,
    "evaluate": 2,
    "implement": 2,
    "debug": 2,
    "optimize": 2,
    "refactor": 2,
    # Low-weight: mild complexity indicators
    "difference between": 1,
    "how does": 1,
    "why does": 1,
    "what happens when": 1,
}

TIER_THRESHOLD = 4   # score >= this → tier 2 (gpt-4o)
BORDERLINE_LOW  = 2  # score in [2, 3] → borderline, optionally escalate via cheap model

def classify_complexity(prompt: str) -> int:
    """
    Returns 1 (gpt-4o-mini) or 2 (gpt-4o).
    Uses a multi-layer scoring system. Routing is per-request.
    """
    score = 0
    prompt_lower = prompt.lower()

    # Layer 1 — simple rules: trivially short prompts skip all scoring
    token_count = len(_encoder.encode(prompt))
    if token_count < 20:
        return 1

    # Layer 2 — keyword detection with weights
    for keyword, weight in COMPLEX_KEYWORDS.items():
        if keyword in prompt_lower:
            score += weight

    # Layer 3 — prompt length scoring
    if token_count >= 500:
        score += 4
    elif token_count >= 300:
        score += 2
    elif token_count >= 150:
        score += 1

    # Layer 4 — regex structural signals
    if re.search(r'```[\s\S]*?```|```', prompt):   # code block
        score += 3
    if re.search(r'`[^`]+`', prompt):               # inline code
        score += 1
    if re.search(r'[\∑\∫\∂\∇]|\\[a-zA-Z]+\{|\$[^$]+\$', prompt):  # math
        score += 3
    if re.search(r'^\s*[-*\d]+[.)]\s', prompt, re.MULTILINE):       # list items
        score += 1
    if prompt.count('?') >= 3:                      # multiple questions
        score += 2

    # Layer 5 — borderline escalation via a cheap model call (optional)
    # If score is in the ambiguous zone [BORDERLINE_LOW, TIER_THRESHOLD),
    # call gpt-4o-mini itself to classify. This adds ~200ms latency but
    # is more accurate than a hard threshold for borderline cases.
    # Only enable if latency budget allows.
    if BORDERLINE_LOW <= score < TIER_THRESHOLD:
        escalated = _escalate_via_model(prompt)
        if escalated:
            return 2

    return 2 if score >= TIER_THRESHOLD else 1


def _escalate_via_model(prompt: str) -> bool:
    """
    Uses gpt-4o-mini to classify borderline prompts.
    Returns True if the prompt needs the full model.
    Falls back to False (stay on mini) if the call fails.
    Only called for prompts with ambiguous complexity scores.
    """
    from openai import AzureOpenAI
    import os
    try:
        client = AzureOpenAI(
            azure_endpoint=os.environ["AZURE_OAI_WESTEUROPE_ENDPOINT"],
            api_key=os.environ["AZURE_OAI_WESTEUROPE_KEY"],
            api_version="2024-02-01",
        )
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a routing classifier. Reply with exactly one word: "
                        "'simple' or 'complex'. "
                        "'complex' means the prompt requires multi-step reasoning, "
                        "code generation, mathematical derivation, or deep analysis. "
                        "'simple' means it can be answered with a short factual response."
                    ),
                },
                {"role": "user", "content": prompt[:500]},  # cap to 500 chars
            ],
            max_tokens=1,
            temperature=0,
        )
        answer = response.choices[0].message.content.strip().lower()
        return answer == "complex"
    except Exception:
        return False  # fail safe: stay on mini


MODEL_FOR_TIER = {
    1: "gpt-4o-mini",
    2: "gpt-4o",
}
```

### Tuning guide
| Knob | Effect |
|------|--------|
| `TIER_THRESHOLD` | Lower → more tier-2 routing (more accurate, more expensive) |
| `BORDERLINE_LOW` | Lower → more model-based escalation calls |
| Keyword weights | Increase a weight to make that signal more decisive |

During the demo, log `score` alongside `tier` so you can show the jury exactly why each prompt was routed where it was.

---

## Stage 4: Carbon-Aware Scheduler

### Carbon data source: Electricity Maps API

Sign up for a free API key at electricitymaps.com (free tier: 10k calls/month, sufficient for demo).

```python
# carbon_client.py
import os
import httpx
from datetime import datetime, timezone

ELECTRICITY_MAPS_KEY = os.environ["ELECTRICITY_MAPS_KEY"]

# Azure region → Electricity Maps zone code
REGION_TO_ZONE = {
    "westeurope": "NL",    # Netherlands
    "eastus": "US-MIDA-PJM",  # US East grid
}

# Fallback values if API is unavailable (use real historical averages)
FALLBACK_CARBON_INTENSITY = {
    "westeurope": 150.0,
    "eastus": 386.0,
}

def get_carbon_intensity(region: str) -> float:
    """Returns gCO₂/kWh for the given Azure region. Falls back to historical average."""
    zone = REGION_TO_ZONE.get(region)
    if not zone:
        return FALLBACK_CARBON_INTENSITY.get(region, 300.0)
    
    try:
        response = httpx.get(
            f"https://api.electricitymap.org/v3/carbon-intensity/latest",
            params={"zone": zone},
            headers={"auth-token": ELECTRICITY_MAPS_KEY},
            timeout=3.0  # never block the user more than 3 seconds for carbon data
        )
        if response.status_code == 200:
            data = response.json()
            return float(data["carbonIntensity"])
    except Exception:
        pass  # network failure → use fallback
    
    return FALLBACK_CARBON_INTENSITY.get(region, 300.0)
```

**Important:** Always catch exceptions from the carbon API. If it's down, use the fallback and note `"carbon_data_source": "fallback"` in the routing decision. Never fail a user request because of a carbon API outage.

### Deferral logic

```python
# Threshold: if carbon intensity > this, defer batch requests
DEFER_THRESHOLD_GCO2_KWH = 250.0

# Defer until: check forecast if available, otherwise defer 2 hours
DEFAULT_DEFER_HOURS = 2
```

```python
def should_defer(urgency: str, carbon_intensity: float) -> tuple[bool, str | None]:
    """
    Returns (defer, defer_until_iso).
    Only defers if urgency == "batch" AND carbon is above threshold.
    """
    if urgency != "batch":
        return False, None
    
    if carbon_intensity <= DEFER_THRESHOLD_GCO2_KWH:
        return False, None  # carbon is already low, run now
    
    # Simple defer: 2 hours from now
    # In production you'd use the Electricity Maps forecast endpoint
    from datetime import timedelta
    defer_until = datetime.now(timezone.utc) + timedelta(hours=DEFAULT_DEFER_HOURS)
    return True, defer_until.isoformat()
```

### Main routing function (carbon_scheduler.py)

```python
import os
from scheduler.complexity_router import classify_complexity, MODEL_FOR_TIER
from scheduler.carbon_client import get_carbon_intensity, FALLBACK_CARBON_INTENSITY
from shared.models import RoutingDecision

AVAILABLE_REGIONS = ["westeurope", "eastus"]

REGION_CONFIG = {
    "westeurope": {
        "endpoint_env": "AZURE_OAI_WESTEUROPE_ENDPOINT",
        "key_env": "AZURE_OAI_WESTEUROPE_KEY",
    },
    "eastus": {
        "endpoint_env": "AZURE_OAI_EASTUS_ENDPOINT",
        "key_env": "AZURE_OAI_EASTUS_KEY",
    },
}

def get_routing_decision(prompt: str, urgency: str) -> RoutingDecision:
    # Stage 3: classify complexity
    tier = classify_complexity(prompt)
    model = MODEL_FOR_TIER[tier]
    
    # Stage 4: get live carbon intensity for each region
    intensities = {region: get_carbon_intensity(region) for region in AVAILABLE_REGIONS}
    
    # Pick the region with lowest carbon intensity
    best_region = min(intensities, key=intensities.get)
    best_intensity = intensities[best_region]
    baseline_intensity = intensities.get("eastus", FALLBACK_CARBON_INTENSITY["eastus"])
    
    config = REGION_CONFIG[best_region]
    endpoint = os.environ[config["endpoint_env"]]
    
    # Deferral check
    defer, defer_until = should_defer(urgency, best_intensity)
    
    # Build human-readable reason
    reason = _build_reason(tier, model, best_region, best_intensity, defer, urgency)
    
    return RoutingDecision(
        model=model,
        region=best_region,
        endpoint=endpoint,
        api_key_env=config["key_env"],
        complexity_tier=tier,
        defer=defer,
        defer_until=defer_until,
        carbon_intensity=best_intensity,
        carbon_intensity_baseline=baseline_intensity,
        routing_reason=reason,
    )

def _build_reason(tier, model, region, intensity, defer, urgency) -> str:
    if defer:
        return f"Deferred: {region} grid at {intensity:.0f} gCO₂/kWh exceeds threshold; batch job queued."
    if tier == 1:
        return f"Routed to {model} in {region} ({intensity:.0f} gCO₂/kWh): simple prompt, efficient model."
    return f"Routed to {model} in {region} ({intensity:.0f} gCO₂/kWh): complex prompt requires full model."
```

---

## Deferred Queue (deferred_queue.py)

For the hackathon demo, implement a simple in-memory queue. Deferred requests are stored and can be retrieved by the frontend to show "pending green jobs."

```python
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

@dataclass
class DeferredJob:
    job_id: str
    prompt: str
    system_prompt: str | None
    queued_at: str
    defer_until: str
    carbon_intensity_at_queue: float
    status: str  # "queued" | "processing" | "done"
    result: str | None

_queue: deque[DeferredJob] = deque(maxlen=100)

def enqueue(prompt, system_prompt, defer_until, carbon_intensity) -> str:
    job_id = str(uuid.uuid4())
    _queue.append(DeferredJob(
        job_id=job_id,
        prompt=prompt,
        system_prompt=system_prompt,
        queued_at=datetime.now(timezone.utc).isoformat(),
        defer_until=defer_until,
        carbon_intensity_at_queue=carbon_intensity,
        status="queued",
        result=None,
    ))
    return job_id

def get_all_jobs() -> list[DeferredJob]:
    return list(_queue)

def get_ready_jobs() -> list[DeferredJob]:
    """Jobs whose defer_until has passed."""
    now = datetime.now(timezone.utc)
    return [j for j in _queue if j.status == "queued" 
            and datetime.fromisoformat(j.defer_until) <= now]
```

---

## Implementation Order

### Step 1 — complexity_router.py
Implement and test `classify_complexity`. Test cases:
- `"What is 2+2?"` → tier 1
- `"Step by step, design a microservices architecture for a payment system."` → tier 2
- A 400-token prompt → tier 2

### Step 2 — carbon_client.py
Implement `get_carbon_intensity`. Test it with a real API key. Print the live intensity for `"NL"` and `"US-MIDA-PJM"`. Verify the fallback works when you pass an invalid key.

### Step 3 — carbon_scheduler.py
Wire Steps 1 and 2. Test the full `get_routing_decision` call with a simple and a complex prompt, both `"realtime"` and `"batch"` urgency.

### Step 4 — deferred_queue.py
Implement queue. Verify `get_ready_jobs` returns nothing for jobs deferred 2 hours in the future.

---

## What NOT to do
- Do not block a request for more than 3 seconds waiting for carbon data
- Do not defer `"realtime"` requests — ever, regardless of carbon intensity
- Do not hardcode API keys
- Do not make the complexity classification deterministic on token count alone — use all scoring layers
- Do not call `_escalate_via_model` for every request — only for borderline scores in [BORDERLINE_LOW, TIER_THRESHOLD)
- Do not route per-session — every request is classified independently

---

## Fallback Behavior (critical for demo reliability)
If `get_carbon_intensity` fails for all regions:
- Use `FALLBACK_CARBON_INTENSITY` values
- Set `routing_reason` to include `"(fallback carbon data)"`
- Never throw an exception — always return a valid `RoutingDecision`

---

## Dependencies to add to requirements.txt
```
httpx
tiktoken
```

---

## Definition of Done
- [ ] `classify_complexity("What is 2+2?")` returns `1`
- [ ] `classify_complexity("Step by step, design a distributed system...")` returns `2`
- [ ] `get_carbon_intensity("westeurope")` returns a float (from API or fallback)
- [ ] `get_routing_decision("Hello", "realtime")` returns a `RoutingDecision` with `defer=False`
- [ ] `get_routing_decision("Hello", "batch")` returns `defer=True` when westeurope carbon > 250
- [ ] Carbon API timeout (3s) is enforced
- [ ] No API keys in source code
- [ ] Fallback values used silently when API is unavailable
