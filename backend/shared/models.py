from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class GatewayRequest:
    prompt: str
    urgency: str = "realtime"          # "realtime" | "batch"
    system_prompt: Optional[str] = None
    max_tokens: int = 2000


@dataclass
class CacheResult:
    hit: bool
    response: Optional[str]
    similarity: float


@dataclass
class CompressionResult:
    compressed_prompt: str
    original_tokens: int
    compressed_tokens: int
    ratio: float
    rules_applied: list = field(default_factory=list)


@dataclass
class RoutingDecision:
    model: str
    region: str
    endpoint: str
    api_key_env: str
    complexity_tier: int
    defer: bool
    defer_until: Optional[str]
    carbon_intensity: float
    carbon_intensity_baseline: float
    routing_reason: str


@dataclass
class GreenReceipt:
    request_id: str
    timestamp: str

    # Stage 1 — cache
    cache_hit: bool
    cache_similarity: float

    # Stage 2 — compression
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    tokens_saved_by_compression: int

    # Stage 3+4 — routing
    complexity_tier: int
    model_used: str
    region_used: str
    carbon_intensity: float
    deferred: bool
    defer_until: Optional[str]

    # SCI — Green Software Foundation formula: SCI = (E * I + M) / R
    energy_kwh: float
    gco2_this_request: float    # gCO₂
    gco2_baseline: float        # gCO₂ — what gpt-4o in eastus would have cost
    gco2_saved: float           # gCO₂ — can be negative, never hide it
    sci_score: float            # gCO₂ per request

    savings_pct: float
    route_explanation: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class GatewayResponse:
    response: Optional[str]
    green_receipt: GreenReceipt
    job_id: Optional[str] = None
    status: str = "ok"          # "ok" | "queued"

    def to_dict(self) -> dict:
        d = asdict(self)
        return d
