from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional

from shared.models import (
    GreenReceipt,
    CacheResult,
    CompressionResult,
    RoutingDecision,
)

# Energy per 1 000 tokens (kWh)
# Source: Patterson et al. 2021 "Carbon emissions and large neural network training"
# and ElectricityMaps / ML CO₂ Impact calculator cross-references.
MODEL_ENERGY_FACTORS: dict[str, float] = {
    "gpt-4o":    0.00090,
    "o4-mini":   0.00009,
}
_DEFAULT_ENERGY_FACTOR = 0.00090

EMBODIED_CARBON_G = 0.001

BASELINE_MODEL = "gpt-4o"
# Weighted average of OpenAI/Anthropic primary API regions (US-East ~320, EU-West ~250, US-West ~100)
# Represents a typical direct API call with no green routing — not a worst-case scenario.
BASELINE_REGION_INTENSITY = 300.0   # gCO₂/kWh


def _energy_kwh(model: str, total_tokens: int) -> float:
    factor = MODEL_ENERGY_FACTORS.get(model, _DEFAULT_ENERGY_FACTOR)
    return (total_tokens / 1000) * factor


def calculate_sci(
    model: str,
    actual_tokens: int,
    carbon_intensity: float,
    baseline_tokens: int | None = None,
) -> tuple[float, float, float]:
    """
    Returns (energy_kwh, gco2_this_request, gco2_baseline).
    SCI formula: (E * I + M) / R  where R = 1 request.
    baseline_tokens should be original_prompt_tokens + output_tokens so that
    compression savings are reflected in the baseline comparison.
    """
    if baseline_tokens is None:
        baseline_tokens = actual_tokens

    e = _energy_kwh(model, actual_tokens)
    gco2 = e * carbon_intensity + EMBODIED_CARBON_G

    e_base = _energy_kwh(BASELINE_MODEL, baseline_tokens)
    gco2_base = e_base * BASELINE_REGION_INTENSITY + EMBODIED_CARBON_G

    return e, gco2, gco2_base


def build_receipt(
    *,
    cache_result: CacheResult,
    compression: Optional[CompressionResult],
    routing: Optional[RoutingDecision],
    total_tokens: int,
    original_prompt_tokens: int,
    reasoning_tokens: int = 0,
) -> GreenReceipt:
    """
    Assembles a GreenReceipt from all pipeline stage outputs.
    Call with compression=None and routing=None on a cache hit.
    """
    now = datetime.now(timezone.utc).isoformat()

    if cache_result.hit:
        # Cache hit: no model call, no compression ran.
        # Baseline assumes a typical full call: prompt + estimated output tokens.
        estimated_total_tokens = original_prompt_tokens + 200
        e, gco2, gco2_base = calculate_sci(
            BASELINE_MODEL, estimated_total_tokens, BASELINE_REGION_INTENSITY
        )
        # We saved everything — embodied carbon is all we "spent"
        gco2_spent = EMBODIED_CARBON_G
        gco2_saved = gco2_base - gco2_spent
        savings_pct = (gco2_saved / gco2_base * 100) if gco2_base > 0 else 0.0

        return GreenReceipt(
            request_id=str(uuid.uuid4()),
            timestamp=now,
            cache_hit=True,
            cache_similarity=cache_result.similarity,
            original_tokens=original_prompt_tokens,
            compressed_tokens=original_prompt_tokens,
            compression_ratio=1.0,
            tokens_saved_by_compression=0,
            complexity_tier=0,
            model_used="cache",
            region_used="cache",
            carbon_intensity=0.0,
            deferred=False,
            defer_until=None,
            energy_kwh=0.0,
            gco2_this_request=gco2_spent,
            gco2_baseline=gco2_base,
            gco2_saved=gco2_saved,
            sci_score=gco2_spent,
            savings_pct=round(savings_pct, 2),
            route_explanation=(
                f"Cache hit (similarity {cache_result.similarity:.2f}) — "
                "no model call needed, zero inference energy."
            ),
        )

    # Full pipeline path
    assert compression is not None
    assert routing is not None

    # Baseline = what the user would have spent calling gpt-4o directly:
    #   original (uncompressed) prompt + visible output only.
    #   reasoning_tokens are o4-mini's hidden chain-of-thought — gpt-4o has no
    #   equivalent overhead, so they must be excluded from the baseline.
    visible_output_tokens = max(0, total_tokens - compression.compressed_tokens - reasoning_tokens)
    baseline_total_tokens = compression.original_tokens + visible_output_tokens

    e, gco2, gco2_base = calculate_sci(
        routing.model, total_tokens, routing.carbon_intensity,
        baseline_tokens=baseline_total_tokens,
    )
    gco2_saved = max(0.0, gco2_base - gco2)
    savings_pct = (gco2_saved / gco2_base * 100) if gco2_base > 0 else 0.0

    return GreenReceipt(
        request_id=str(uuid.uuid4()),
        timestamp=now,
        cache_hit=False,
        cache_similarity=cache_result.similarity,
        original_tokens=compression.original_tokens,
        compressed_tokens=compression.compressed_tokens,
        compression_ratio=compression.ratio,
        tokens_saved_by_compression=compression.original_tokens - compression.compressed_tokens,
        complexity_tier=routing.complexity_tier,
        model_used=routing.model,
        region_used=routing.region,
        carbon_intensity=routing.carbon_intensity,
        deferred=routing.defer,
        defer_until=routing.defer_until,
        energy_kwh=round(e, 8),
        gco2_this_request=round(gco2, 6),
        gco2_baseline=round(gco2_base, 6),
        gco2_saved=round(gco2_saved, 6),
        sci_score=round(gco2, 6),
        savings_pct=round(savings_pct, 2),
        route_explanation=routing.routing_reason,
    )
